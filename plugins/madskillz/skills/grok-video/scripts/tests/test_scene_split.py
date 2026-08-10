import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import scene_split

FIX = pathlib.Path(__file__).parent / "fixtures" / "tinybook"


def test_splits_chapter_at_scene_breaks():
    inv = scene_split.inventory(FIX)
    ch1 = inv["chapters"][0]
    assert ch1["chapter"] == "01-the-sneeze"
    assert len(ch1["scenes"]) == 2


def test_ignores_dashes_inside_code_fences():
    inv = scene_split.inventory(FIX)
    ch1 = inv["chapters"][0]
    # The fenced "sock log" block contains a --- line; it must not split.
    assert "Morg folded her arms" in ch1["scenes"][1]["text"]
    assert "sock log" in ch1["scenes"][1]["text"]


def test_skips_yaml_frontmatter():
    inv = scene_split.inventory(FIX)
    ch2 = inv["chapters"][1]
    assert ch2["chapter"] == "02-the-fix"
    assert len(ch2["scenes"]) == 1
    assert "draft: 2" not in ch2["scenes"][0]["text"]
    assert "Pip returned the sock" in ch2["scenes"][0]["text"]


def test_scene_metadata():
    inv = scene_split.inventory(FIX)
    s1 = inv["chapters"][0]["scenes"][0]
    assert s1["scene"] == 1
    assert s1["first_line"].startswith("# Chapter 1")
    assert s1["words"] > 0
    assert s1["start_line"] == 1


def test_chapter_prefix_filter():
    inv = scene_split.inventory(FIX, chapter_prefix="02")
    assert [c["chapter"] for c in inv["chapters"]] == ["02-the-fix"]


def test_missing_chapters_dir_fails_loudly(tmp_path):
    with pytest.raises(RuntimeError, match="no chapters"):
        scene_split.inventory(tmp_path)


def test_cli_prints_json(capsys):
    rc = scene_split.main(["scene_split.py", str(FIX)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["book"] == "tinybook"
    assert len(out["chapters"]) == 2
