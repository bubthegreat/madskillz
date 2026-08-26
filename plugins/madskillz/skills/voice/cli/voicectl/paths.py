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


def store_branch() -> str:
    return os.environ.get("VOICE_SYNC_BRANCH", "main")


def templates_dir() -> Path:
    """Skill-shipped profile templates. Env override > skill checkout > installed copy.

    The installed copy sits BESIDE the store dir, never inside it: files inside the store
    dir are the user's own, and `init` renames those aside when it adopts a remote store.
    """
    env = os.environ.get("VOICE_TEMPLATES_DIR")
    if env:
        return Path(env)
    checkout = Path(__file__).resolve().parents[2] / "references" / "voices"
    if checkout.is_dir():
        return checkout
    return voice_dir().parent / "voice-templates"


# Files in the live voice dir that are markdown but not context overlays.
NON_OVERLAY = {"core.md", "README.md", "voice.md"}

# Suffix for the backup dir `init --remote` makes when adopting a non-empty remote.
BACKUP_SUFFIX = ".bak-"


def live_contexts() -> list[str]:
    """Context names with a live overlay present."""
    d = voice_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md") if p.name not in NON_OVERLAY)
