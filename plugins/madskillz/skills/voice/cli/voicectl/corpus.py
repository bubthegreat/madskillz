"""Corpus access: capture appends, marker-relative reads."""

import json
from datetime import datetime, timezone
from pathlib import Path


def now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_capture(corpus: Path, event_json: str) -> bool:
    """Append the prompt from a UserPromptSubmit event. Returns True when a line was written."""
    data = json.loads(event_json)
    text = data.get("prompt", "")
    if not isinstance(text, str) or not text.strip():
        return False
    corpus.parent.mkdir(parents=True, exist_ok=True)
    with corpus.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now_ts(), "text": text}, ensure_ascii=False) + "\n")
    return True


def entries(corpus: Path) -> list[dict]:
    out = []
    try:
        lines = corpus.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(d.get("ts"), str) and isinstance(d.get("text"), str):
            out.append(d)
    return out


def entries_since(corpus: Path, marker: str) -> list[dict]:
    return [e for e in entries(corpus) if e["ts"] > marker]


def count_since(corpus: Path, marker: str) -> int:
    return len(entries_since(corpus, marker))
