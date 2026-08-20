"""Materiality-gated repo sync: copy live voice files into the dedicated sync clone and
push to the target branch. Deterministic replacement for the prose materiality check."""

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .profile import get_marker, parse, set_marker


@dataclass
class Materiality:
    material: bool
    reasons: list[str] = field(default_factory=list)
    changed_bullets: int = 0
    new_sections: list[str] = field(default_factory=list)
    changed_overlays: list[str] = field(default_factory=list)


MIN_CHANGED_BULLETS = 3


def _bullets(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if l.strip().startswith("- ")]


def assess(live_dir: Path, committed_dir: Path) -> Materiality:
    """Material when: new core section, >=3 changed/added core trait bullets, or any
    overlay file differs from its committed copy."""
    m = Materiality(material=False)
    live_core = live_dir / "core.md"
    committed_core = committed_dir / "core.md"
    if not live_core.exists():
        return m
    live_text = live_core.read_text(encoding="utf-8")
    committed_text = (
        committed_core.read_text(encoding="utf-8") if committed_core.exists() else ""
    )

    live_headings = [h for h, _ in parse(live_text).sections]
    committed_headings = {h for h, _ in parse(committed_text).sections}
    m.new_sections = [h for h in live_headings if h not in committed_headings]

    committed_bullets = set(_bullets(committed_text))
    m.changed_bullets = sum(1 for b in _bullets(live_text) if b not in committed_bullets)

    for overlay in sorted(live_dir.glob("*.md")):
        if overlay.name in paths.NON_OVERLAY:
            continue
        committed = committed_dir / overlay.name
        if (
            not committed.exists()
            or committed.read_text(encoding="utf-8") != overlay.read_text(encoding="utf-8")
        ):
            m.changed_overlays.append(overlay.name)

    if not committed_text:
        m.reasons.append("no committed core yet (first sync)")
    if m.new_sections:
        m.reasons.append(f"new core section(s): {', '.join(m.new_sections)}")
    if m.changed_bullets >= MIN_CHANGED_BULLETS:
        m.reasons.append(f"{m.changed_bullets} changed/added core trait bullets")
    if m.changed_overlays:
        m.reasons.append(f"overlay(s) changed: {', '.join(m.changed_overlays)}")
    m.material = bool(m.reasons)
    return m


class SyncError(Exception):
    pass


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if r.returncode != 0:
        raise SyncError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def run(dry_run: bool = False, push: bool = True) -> str:
    live_dir = paths.voice_dir()
    repo = paths.sync_repo()
    branch = paths.sync_branch()
    committed_dir = repo / paths.VOICES_SUBPATH

    verdict = assess(live_dir, committed_dir)
    if not verdict.material:
        return "sync: no material delta - nothing to do"
    summary = "; ".join(verdict.reasons)
    if dry_run:
        return f"sync (dry-run): material - {summary}"

    if not (repo / ".git").exists():
        raise SyncError(f"sync repo missing: {repo}")
    current = _git(repo, "branch", "--show-current")
    if current != branch:
        raise SyncError(f"sync repo on '{current}', not target '{branch}' - refusing")

    # Stamp Repo-synced through = Processed through in the LIVE core first, then copy
    # everything, so both copies carry the same markers.
    live_core = live_dir / "core.md"
    text = live_core.read_text(encoding="utf-8")
    processed = get_marker(text, "processed")
    if processed:
        live_core.write_text(
            set_marker(text, "repo", processed), encoding="utf-8"
        )

    committed_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for f in sorted(live_dir.glob("*.md")):
        if f.name == "voice.md":  # compat render, never committed
            continue
        shutil.copyfile(f, committed_dir / f.name)
        copied.append(f.name)

    _git(repo, "add", paths.VOICES_SUBPATH)
    if not _git(repo, "status", "--porcelain", "--", paths.VOICES_SUBPATH):
        return "sync: material by assessment but no file delta after copy - nothing committed"
    _git(repo, "commit", "-m", "voice: sync voice profiles (auto)")
    if push:
        _git(repo, "push", "origin", branch)
    return f"sync: pushed {', '.join(copied)} ({summary})"
