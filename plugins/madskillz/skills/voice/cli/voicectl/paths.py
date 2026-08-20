"""Path resolution for the voice pipeline. Everything is env-overridable so tests can sandbox."""

import os
from pathlib import Path


def voice_dir() -> Path:
    return Path(os.environ.get("VOICE_DIR", Path.home() / ".madskillz" / "voice"))


def claude_dir() -> Path:
    return Path(os.environ.get("CLAUDE_DIR", Path.home() / ".claude"))


def corpus_path() -> Path:
    return voice_dir() / "corpus.jsonl"


def core_path() -> Path:
    return voice_dir() / "core.md"


def overlay_path(context: str) -> Path:
    return voice_dir() / f"{context}.md"


def log_path() -> Path:
    return voice_dir() / "sync.log"


def sync_repo() -> Path:
    return Path(os.environ.get("VOICE_SYNC_REPO", voice_dir() / "madskillz-sync"))


def sync_branch() -> str:
    return os.environ.get("VOICE_SYNC_BRANCH", "main")


# Committed voices library, relative to a madskillz checkout.
VOICES_SUBPATH = "plugins/madskillz/skills/voice/references/voices"

# Files in the live voice dir that are voice profiles, not overlays.
NON_OVERLAY = {"core.md", "voice.md"}


def live_contexts() -> list[str]:
    """Context names with a live overlay present."""
    d = voice_dir()
    if not d.is_dir():
        return []
    return sorted(
        p.stem for p in d.glob("*.md") if p.name not in NON_OVERLAY
    )
