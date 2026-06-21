import sys, pathlib, zipfile
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import render

FIX = pathlib.Path(__file__).parent / "fixtures" / "tinybook"


def test_read_meta_reads_title_and_author():
    meta = render.read_meta(FIX)
    assert meta["title"] == "The Tiny Goblin"
    assert meta["author"] == "Test Author"


def test_combine_includes_title_and_both_chapters_in_order():
    md = render.combine(FIX)
    assert "# The Tiny Goblin" in md
    assert md.index("The Sneeze") < md.index("The Fix")


def test_render_produces_valid_epub_and_pdf(tmp_path):
    tools = render.tools_available()
    if not (tools["pandoc"] and tools["typst"]):
        pytest.skip(f"pandoc/typst not installed: {tools}")
    out = render.render(FIX, out_dir=tmp_path)
    assert out["epub"].exists() and out["pdf"].exists()
    assert zipfile.is_zipfile(out["epub"])
    with zipfile.ZipFile(out["epub"]) as z:
        assert z.read("mimetype").decode() == "application/epub+zip"
    assert out["pdf"].read_bytes()[:5] == b"%PDF-"
