import json
import textwrap

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
    monkeypatch.setenv("VOICE_SYNC_REPO", str(tmp_path / "sync-repo"))
    return vdir


def add_corpus(vdir, ts, text):
    with (vdir / "corpus.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "text": text}) + "\n")
