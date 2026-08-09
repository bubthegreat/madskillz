import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import assemble as asm  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "tinyfilm"

FILM = {"fps": 24, "width": 1280, "height": 720, "slug": "tinyfilm"}


def test_trim_uses_edit_points_not_full_clip_length():
    shot = {"id": "s01-001", "duration": 8, "edit_in": 1.0, "edit_out": 5.5}
    cmd = asm.trim_command(pathlib.Path("in.mp4"), pathlib.Path("out.mp4"), shot, FILM)
    assert cmd[cmd.index("-ss") + 1] == "1.000"
    assert cmd[cmd.index("-t") + 1] == "4.500"


def test_trim_defaults_to_the_whole_clip_when_no_edit_points():
    shot = {"id": "s01-001", "duration": 6}
    cmd = asm.trim_command(pathlib.Path("in.mp4"), pathlib.Path("out.mp4"), shot, FILM)
    assert cmd[cmd.index("-ss") + 1] == "0.000"
    assert cmd[cmd.index("-t") + 1] == "6.000"


def test_trim_conforms_resolution_and_fps():
    cmd = asm.trim_command(pathlib.Path("i.mp4"), pathlib.Path("o.mp4"),
                           {"duration": 5}, FILM)
    vf = cmd[cmd.index("-vf") + 1]
    assert "scale=1280:720" in vf and "fps=24" in vf


def test_concat_command_uses_stream_copy():
    cmd = asm.concat_command(pathlib.Path("list.txt"), pathlib.Path("out.mp4"))
    assert "concat" in cmd and cmd[-3:] == ["-c", "copy", "out.mp4"]


def test_mix_command_ducks_the_bed_under_clip_audio():
    cmd = asm.mix_command(pathlib.Path("v.mp4"), pathlib.Path("bed.wav"),
                          pathlib.Path("out.mp4"))
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "volume=0.35" in fc and "amix=inputs=2" in fc


def test_contact_sheet_tiles_every_clip():
    clips = [pathlib.Path(f"{i}.mp4") for i in range(3)]
    cmd = asm.contact_sheet_command(clips, pathlib.Path("sheet.png"))
    assert cmd.count("-i") == 3
    assert "xstack=inputs=3" in cmd[cmd.index("-filter_complex") + 1]


def test_xstack_layout_places_cells_in_a_grid():
    # 2x2: offsets accumulate one cell width/height per column/row index.
    assert asm._xstack_layout(2, 2, 4) == "0_0|w0_0|0_h0|w0_h0"


def test_xstack_layout_accumulates_across_wider_rows():
    assert asm._xstack_layout(3, 1, 3) == "0_0|w0_0|w0+w0_0"


# --- select resolution -----------------------------------------------------

def test_selected_take_prefers_explicit_select(tmp_path):
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "s01-001_t01.mp4").touch()
    (gen / "s01-001_t02.mp4").touch()
    shot = {"id": "s01-001", "select": "s01-001_t02.mp4"}
    assert asm.selected_take(tmp_path, shot).name == "s01-001_t02.mp4"


def test_selected_take_falls_back_to_first_on_disk(tmp_path):
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "s01-001_t02.mp4").touch()
    (gen / "s01-001_t01.mp4").touch()
    assert asm.selected_take(tmp_path, {"id": "s01-001"}).name == "s01-001_t01.mp4"


def test_selected_take_is_none_when_nothing_generated(tmp_path):
    (tmp_path / "generated").mkdir()
    assert asm.selected_take(tmp_path, {"id": "s01-001"}) is None


# --- planning --------------------------------------------------------------

def test_plan_reports_missing_shots_without_failing(tmp_path):
    (tmp_path / "generated").mkdir()
    shots = [{"id": "s01-001", "duration": 5}, {"id": "s01-002", "duration": 5}]
    p = asm.plan(tmp_path, FILM, shots)
    assert p["missing"] == ["s01-001", "s01-002"]
    assert p["steps"] == []


def test_plan_builds_one_step_per_available_take(tmp_path):
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "s01-001_t01.mp4").touch()
    shots = [{"id": "s01-001", "duration": 5}, {"id": "s01-002", "duration": 5}]
    p = asm.plan(tmp_path, FILM, shots)
    assert len(p["steps"]) == 1
    assert p["missing"] == ["s01-002"]


def test_dry_run_executes_nothing():
    # A non-existent binary would raise if dry_run were not honoured.
    assert asm.run([["definitely-not-a-real-binary"]], dry_run=True) == 0


def test_load_reads_the_fixture():
    film, shots = asm.load(FIXTURE)
    assert film["fps"] == 24 and len(shots) == 5
