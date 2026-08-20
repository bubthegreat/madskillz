import pytest

from voicectl import profile as prof
from voicectl.merge import RenderError, render
from tests.conftest import CORE, OVERLAY


def test_frontmatter_and_sections():
    p = prof.parse(CORE)
    assert p.frontmatter["voice"] == "core"
    assert "Identity preamble." in p.preamble
    headings = [h for h, _ in p.sections]
    assert "## Mechanics" in headings and "## Provenance & sync" in headings
    assert "trait one" in p.section("## Mechanics")


def test_markers_roundtrip():
    assert prof.get_marker(CORE, "processed") == "2026-01-01T00:00:00Z"
    bumped = prof.set_marker(CORE, "processed", "2026-02-02T00:00:00Z")
    assert prof.get_marker(bumped, "processed") == "2026-02-02T00:00:00Z"
    assert prof.get_marker(bumped, "repo") == "2026-01-01T00:00:00Z"
    assert prof.get_marker("Processed through: none", "processed") == ""


def test_set_marker_missing_raises():
    with pytest.raises(ValueError):
        prof.set_marker("no markers here", "repo", "2026-01-01T00:00:00Z")


def test_validate_core():
    assert prof.validate_core(CORE) == []
    bad = CORE.replace("voice: core", "voice: blog").replace("## Mechanics", "## Stuff")
    problems = prof.validate_core(bad)
    assert any("voice" in p for p in problems)
    assert any("Mechanics" in p for p in problems)


def test_render_merges_and_overrides():
    out = render(CORE, OVERLAY, "blog")
    assert out.startswith("---\nvoice: blog\n")
    # overlay prescriptive section present
    assert "## Comedic influences" in out
    # override replaced the core body, no duplicate heading
    assert out.count("## Inquiry style") == 1
    assert "overridden inquiry for blog" in out
    assert "question stacking" not in out
    # core descriptive + provenance carried through
    assert "## Mechanics" in out and "## Provenance & sync" in out
    # blog prescriptive comes before core descriptive
    assert out.index("## Comedic influences") < out.index("## Mechanics")


def test_render_orphan_override_raises():
    bad_overlay = OVERLAY.replace("## Inquiry style", "## Nonexistent")
    with pytest.raises(RenderError):
        render(CORE, bad_overlay, "blog")
