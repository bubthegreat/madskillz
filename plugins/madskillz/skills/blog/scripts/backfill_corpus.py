#!/usr/bin/env python3
"""backfill_corpus.py — rebuild/extend the voice corpus from local Claude Code data.

The capture hook only records prompts from the moment it is installed. This script folds in
what the machine already knows: every prompt in ~/.claude/history.jsonl plus user-authored
turns mined from ~/.claude/projects/*/ session transcripts. Idempotent — re-runs append
nothing new.

Only entries newer than the live profile's `Processed through:` marker are considered
(anything older was already folded into the profile). Corpus schema matches the capture
hook: one JSON line {"ts": "<ISO8601 UTC>", "text": "<message>"}.

Env overrides: VOICE_DIR (~/.madskillz/voice), CLAUDE_DIR (~/.claude),
BACKFILL_SESSIONS_PER_PROJECT (15).
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VOICE_DIR = Path(os.environ.get("VOICE_DIR", Path.home() / ".madskillz" / "voice"))
CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", Path.home() / ".claude"))
SESSIONS_PER_PROJECT = int(os.environ.get("BACKFILL_SESSIONS_PER_PROJECT", "15"))

CORPUS = VOICE_DIR / "corpus.jsonl"
PROFILE = VOICE_DIR / "voice.md"


def processed_marker() -> str:
    """The live profile's `Processed through:` ts; '' means process everything."""
    try:
        m = re.search(r"Processed through:\s*(\S+)", PROFILE.read_text(encoding="utf-8"))
        if m and m.group(1).lower() != "none":
            return m.group(1)
    except OSError:
        pass
    return ""


def is_owner_prose(text: str) -> bool:
    """Keep real writing; drop slash commands, shell passthroughs, and pasted XML-ish wrappers."""
    t = text.strip()
    return bool(t) and not t.startswith(("/", "!", "<"))


def iter_history(path: Path):
    """~/.claude/history.jsonl: {"display", "timestamp"(ms), ...} across all projects."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            d = json.loads(line)
            text = d["display"]
            ts_ms = d["timestamp"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        if not isinstance(text, str) or not is_owner_prose(text):
            continue
        ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        yield ts, text.strip()


def iter_transcripts(projects_dir: Path):
    """User-authored turns from the most recent session files of each project.

    A transcript "user" line is owner-written only when message.content is a plain string
    (tool results and command wrappers arrive as lists / XML-ish text).
    """
    if not projects_dir.is_dir():
        return
    for project in sorted(projects_dir.iterdir()):
        sessions = sorted(
            project.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )[:SESSIONS_PER_PROJECT]
        for session in sessions:
            try:
                lines = session.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("type") != "user" or d.get("isMeta"):
                    continue
                content = (d.get("message") or {}).get("content")
                if not isinstance(content, str) or not is_owner_prose(content):
                    continue
                ts_raw = d.get("timestamp") or ""
                try:
                    ts = (
                        datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                        .astimezone(timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ")
                    )
                except ValueError:
                    continue
                yield ts, content.strip()


def dedupe_key(ts: str, text: str):
    """Same text on the same UTC day is one message (history + transcript record the same
    submit with slightly different timestamps); the same short prompt weeks apart is not."""
    return ts[:10], text


def main() -> int:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    marker = processed_marker()

    existing = []
    seen = set()
    if CORPUS.exists():
        for line in CORPUS.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
                existing.append((d["ts"], d["text"]))
                seen.add(dedupe_key(d["ts"], d["text"]))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    mined = 0
    deduped = 0
    fresh = []
    sources = list(iter_history(CLAUDE_DIR / "history.jsonl")) + list(
        iter_transcripts(CLAUDE_DIR / "projects")
    )
    for ts, text in sources:
        if marker and ts <= marker:
            continue
        mined += 1
        key = dedupe_key(ts, text)
        if key in seen:
            deduped += 1
            continue
        seen.add(key)
        fresh.append((ts, text))

    if fresh:
        merged = sorted(existing + fresh)
        with CORPUS.open("w", encoding="utf-8") as f:
            for ts, text in merged:
                f.write(json.dumps({"ts": ts, "text": text}, ensure_ascii=False) + "\n")

    print(
        f"backfill: {mined} candidate message(s) after marker "
        f"({marker or 'none'}), {deduped} duplicate(s) skipped, "
        f"{len(fresh)} appended -> {CORPUS} ({len(existing) + len(fresh)} total)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
