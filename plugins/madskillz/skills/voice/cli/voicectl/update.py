"""LLM update boundary: prep hands the model exactly its input; apply validates and
atomically installs the model's output. The model's only job is trait judgment."""

import json
import os
import tempfile
from pathlib import Path

from . import paths
from .corpus import entries_since
from .profile import get_marker, set_marker, validate_core


class UpdateError(Exception):
    pass


def prep() -> dict:
    core = paths.core_path()
    if not core.is_file():
        raise UpdateError(f"live core profile missing: {core} (run 'voicectl init')")
    text = core.read_text(encoding="utf-8")
    marker = get_marker(text, "processed")
    new = entries_since(paths.corpus_path(), marker)
    return {
        "core_path": str(core),
        "processed_through": marker or "none",
        "new_entry_count": len(new),
        "newest_ts": new[-1]["ts"] if new else marker,
        "new_entries": new,
    }


def apply(candidate_file: Path, processed_through: str | None = None) -> str:
    """Validate a revised core profile and install it atomically, bumping the
    Processed through marker. On any validation failure the live core is untouched."""
    core = paths.core_path()
    text = candidate_file.read_text(encoding="utf-8")
    problems = validate_core(text)
    if problems:
        raise UpdateError("invalid core profile: " + "; ".join(problems))

    if processed_through is None:
        new = entries_since(
            paths.corpus_path(),
            get_marker(core.read_text(encoding="utf-8"), "processed") if core.is_file() else "",
        )
        processed_through = new[-1]["ts"] if new else None
    if processed_through:
        text = set_marker(text, "processed", processed_through)

    fd, tmp = tempfile.mkstemp(dir=str(core.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, core)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return f"update-apply: installed {core} (Processed through: {processed_through or 'unchanged'})"


def prep_json() -> str:
    return json.dumps(prep(), ensure_ascii=False, indent=2)
