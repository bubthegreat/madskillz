"""Backfill the corpus from local Claude Code data (~/.claude/history.jsonl + project
transcripts). Idempotent; honors the live core profile's `Processed through:` marker.
Port of the blog skill's backfill_corpus.py."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .profile import get_marker


def _sessions_per_project() -> int:
    return int(os.environ.get("BACKFILL_SESSIONS_PER_PROJECT", "15"))


def processed_marker() -> str:
    """The live core's marker. Nothing else counts - a leftover `voice.md` from the old
    compat render would otherwise make the backfill skip real messages."""
    try:
        return get_marker(paths.core_path().read_text(encoding="utf-8"), "processed")
    except OSError:
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
        )[: _sessions_per_project()]
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


def run() -> str:
    voice_dir = paths.voice_dir()
    voice_dir.mkdir(parents=True, exist_ok=True)
    corpus = paths.corpus_path()
    claude_dir = paths.claude_dir()
    marker = processed_marker()

    existing = []
    seen = set()
    if corpus.exists():
        for line in corpus.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
                existing.append((d["ts"], d["text"]))
                seen.add(dedupe_key(d["ts"], d["text"]))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    mined = 0
    deduped = 0
    fresh = []
    sources = list(iter_history(claude_dir / "history.jsonl")) + list(
        iter_transcripts(claude_dir / "projects")
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
        with corpus.open("w", encoding="utf-8") as f:
            for ts, text in merged:
                f.write(json.dumps({"ts": ts, "text": text}, ensure_ascii=False) + "\n")

    return (
        f"backfill: {mined} candidate message(s) after marker "
        f"({marker or 'none'}), {deduped} duplicate(s) skipped, "
        f"{len(fresh)} appended -> {corpus} ({len(existing) + len(fresh)} total)"
    )
