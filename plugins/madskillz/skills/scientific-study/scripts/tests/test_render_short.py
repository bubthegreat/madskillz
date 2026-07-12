import importlib.util
import shutil
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "render-paper.py"


def load():
    spec = importlib.util.spec_from_file_location("render_paper", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HAVE_TOOLS = bool(shutil.which("pandoc") and shutil.which("typst"))


def test_render_short_missing_file(tmp_path):
    mod = load()
    study = tmp_path / "empty"
    study.mkdir()
    with pytest.raises(FileNotFoundError):
        mod.render_short(study)


@pytest.mark.skipif(not HAVE_TOOLS, reason="pandoc/typst not on PATH")
def test_render_short_produces_two_column_pdf(tmp_path):
    mod = load()
    study = tmp_path / "my-study"
    study.mkdir()
    (study / "paper-short.md").write_text(
        "# My Study (short form)\n\n**A. Author** · 2026-01-01\n\n"
        "## 1. Introduction\n\nA condensed paragraph citing 0.910.\n",
        encoding="utf-8",
    )
    (study / "README.md").write_text(
        "- **Created:** 2026-01-01\n© 2026 A. Author.\n", encoding="utf-8"
    )
    out = mod.render_short(study)
    assert out["pdf"].name == "my-study-short.pdf"
    assert out["pdf"].exists() and out["pdf"].stat().st_size > 0
    # the temp source + metadata file are cleaned up
    assert not (study / "build" / "my-study-short.src.md").exists()
    assert not (study / "build" / "my-study-short.meta.yaml").exists()


@pytest.mark.skipif(not HAVE_TOOLS, reason="pandoc/typst not on PATH")
def test_render_short_title_with_colon(tmp_path):
    """A title containing ': ' must not break YAML parsing of the metadata file."""
    mod = load()
    study = tmp_path / "colon-study"
    study.mkdir()
    (study / "paper-short.md").write_text(
        "# Deep Models: A Case Study (short form)\n\n**A. Author** · 2026-01-01\n\n"
        "## 1. Introduction\n\nA condensed paragraph citing 0.910.\n",
        encoding="utf-8",
    )
    (study / "README.md").write_text(
        "- **Created:** 2026-01-01\n© 2026 A. Author.\n", encoding="utf-8"
    )
    out = mod.render_short(study)
    assert out["pdf"].name == "colon-study-short.pdf"
    assert out["pdf"].exists() and out["pdf"].stat().st_size > 0
