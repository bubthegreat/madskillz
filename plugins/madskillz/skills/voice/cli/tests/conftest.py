import json
import subprocess
import textwrap
from pathlib import Path

import pytest

CORE = textwrap.dedent(
    """\
    ---
    voice: core
    owner: tester
    purpose: test core
    status: personal
    ---

    # Core voice

    Identity preamble.

    ## Mechanics
    - **trait one** - keep.
    - **trait two** - tone-down.

    ## Inquiry style
    - **question stacking** - keep.

    ## Flagged overuse (tendencies to watch)
    - **"etc."** - crutch.

    ## AI-tells
    - no em-dashes.

    ## Provenance & sync
    - Processed through: 2026-01-01T00:00:00Z
    - Repo-synced through: 2026-01-01T00:00:00Z
    - Changelog:
      - 2026-01-01 - seeded.
    """
)

OVERLAY = textwrap.dedent(
    """\
    ---
    voice: blog
    owner: tester
    purpose: blog overlay
    status: personal
    extends: core
    ---

    Blog preamble: write funny.

    ## Comedic influences
    - deadpan.

    ## Inquiry style
    <!-- override -->
    - overridden inquiry for blog.
    """
)


@pytest.fixture
def voice_env(tmp_path, monkeypatch):
    """Sandboxed voice dir with a seeded core, blog overlay, and empty corpus."""
    vdir = tmp_path / "voice"
    vdir.mkdir()
    (vdir / "core.md").write_text(CORE, encoding="utf-8")
    (vdir / "blog.md").write_text(OVERLAY, encoding="utf-8")
    (vdir / "corpus.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("VOICE_DIR", str(vdir))
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "core.md").write_text(
        CORE.replace("owner: tester", "owner: <handle>").replace("status: personal", "status: template"),
        encoding="utf-8",
    )
    (templates / "blog.md").write_text(
        OVERLAY.replace("owner: tester", "owner: <handle>").replace("status: personal", "status: template"),
        encoding="utf-8",
    )
    (templates / "chat.md").write_text(
        OVERLAY.replace("voice: blog", "voice: chat").replace("owner: tester", "owner: <handle>").replace("status: personal", "status: template"),
        encoding="utf-8",
    )
    monkeypatch.setenv("VOICE_TEMPLATES_DIR", str(templates))
    return vdir


def add_corpus(vdir, ts, text):
    with (vdir / "corpus.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "text": text}) + "\n")


@pytest.fixture
def git_env(monkeypatch):
    """Deterministic git identity so commits work in a sandbox."""
    for k, v in {
        "GIT_AUTHOR_NAME": "tester",
        "GIT_AUTHOR_EMAIL": "tester@example.com",
        "GIT_COMMITTER_NAME": "tester",
        "GIT_COMMITTER_EMAIL": "tester@example.com",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def bare_remote(tmp_path, git_env):
    """Empty bare repo on branch main."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    return origin


def clone_of(origin: Path, dest: Path) -> Path:
    subprocess.run(["git", "clone", "-q", str(origin), str(dest)], check=True)
    return dest
