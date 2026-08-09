import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import shot_check as sc  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "tinyfilm"


def shot(**kw):
    base = {"id": "s01-001", "scene": 1, "mode": "text", "duration": 8}
    base.update(kw)
    return base


def severities(notes, check=None):
    return [n for n in notes if check is None or n["check"] == check]


# --- dialogue budget -------------------------------------------------------

def test_dialogue_seconds_uses_rate():
    assert sc.dialogue_seconds("one two three four five", 2.5) == 2.0


def test_dialogue_that_fits_is_not_flagged():
    notes = sc.check_dialogue_budget([shot(dialogue="This isn't hers.", duration=8)], sc.DEFAULTS)
    assert notes == []


def test_dialogue_overrun_is_a_blocker():
    long_line = " ".join(["word"] * 40)
    notes = sc.check_dialogue_budget([shot(dialogue=long_line, duration=6)], sc.DEFAULTS)
    assert len(notes) == 1 and notes[0]["severity"] == "blocker"
    assert "clipped" in notes[0]["problem"]


def test_dialogue_headroom_is_reserved():
    # 15 words at 2.5 wps = 6.0s exactly; with 1.2s headroom it must not fit a 6s clip.
    line = " ".join(["word"] * 15)
    assert sc.check_dialogue_budget([shot(dialogue=line, duration=6)], sc.DEFAULTS)
    assert sc.check_dialogue_budget([shot(dialogue=line, duration=8)], sc.DEFAULTS) == []


# --- film grammar ----------------------------------------------------------

def test_axis_flip_without_break_is_flagged():
    shots = [shot(id="s01-001", screen_dir="L→R"), shot(id="s01-002", screen_dir="R→L")]
    notes = sc.check_axis(shots)
    assert len(notes) == 1 and notes[0]["shot"] == "s01-002"
    assert "180" in notes[0]["problem"]


def test_axis_flip_is_cleared_by_explicit_break():
    shots = [shot(id="s01-001", screen_dir="L→R"),
             shot(id="s01-002", screen_dir="R→L", axis_break=True)]
    assert sc.check_axis(shots) == []


def test_axis_not_flagged_across_different_scenes():
    shots = [shot(id="s01-001", scene=1, screen_dir="L→R"),
             shot(id="s02-001", scene=2, screen_dir="R→L")]
    assert sc.check_axis(shots) == []


def test_identical_framing_back_to_back_is_a_jump_cut():
    shots = [shot(id="s01-001", size="MS", angle="eye"),
             shot(id="s01-002", size="MS", angle="eye")]
    notes = sc.check_jump_cuts(shots)
    assert len(notes) == 1 and notes[0]["severity"] == "major"


def test_two_size_steps_is_a_clean_cut():
    shots = [shot(id="s01-001", size="WS", angle="eye"),
             shot(id="s01-002", size="MCU", angle="eye")]
    assert sc.check_jump_cuts(shots) == []


def test_extend_shot_is_exempt_from_jump_cut_check():
    shots = [shot(id="s01-001", size="MS", angle="eye"),
             shot(id="s01-002", size="MS", angle="eye", mode="extend", extend_from="s01-001")]
    assert sc.check_jump_cuts(shots) == []


def test_scene_without_a_wide_shot_is_flagged():
    shots = [shot(id="s01-001", size="CU"), shot(id="s01-002", size="MCU")]
    notes = sc.check_coverage(shots)
    assert len(notes) == 1 and "no wide shot" in notes[0]["problem"]


def test_scene_with_a_wide_shot_passes_coverage():
    assert sc.check_coverage([shot(id="s01-001", size="WS"), shot(id="s01-002", size="CU")]) == []


# --- references ------------------------------------------------------------

CASTING = {"characters": {"elena": {}}, "voices": {"elena_vo": {}}}


def test_unknown_character_reference_is_a_blocker():
    shots = [shot(refs={"characters": ["nobody"]})]
    notes = severities(sc.check_references(shots, CASTING, sc.DEFAULTS), "references")
    assert any(n["severity"] == "blocker" and "nobody" in n["problem"] for n in notes)


def test_known_character_reference_passes():
    shots = [shot(mode="reference", refs={"characters": ["elena"], "voice": "elena_vo"})]
    assert sc.check_references(shots, CASTING, sc.DEFAULTS) == []


def test_extend_from_a_later_shot_is_rejected():
    shots = [shot(id="s01-001", mode="extend", extend_from="s01-002"), shot(id="s01-002")]
    notes = sc.check_references(shots, CASTING, sc.DEFAULTS)
    assert any("later shot" in n["problem"] for n in notes)


def test_extend_chain_depth_limit_is_enforced():
    shots = [
        shot(id="s01-001"),
        shot(id="s01-002", mode="extend", extend_from="s01-001"),
        shot(id="s01-003", mode="extend", extend_from="s01-002"),
        shot(id="s01-004", mode="extend", extend_from="s01-003"),
        shot(id="s01-005", mode="extend", extend_from="s01-004"),
    ]
    notes = sc.check_references(shots, CASTING, {**sc.DEFAULTS, "max_extend_chain": 3})
    assert any("Extension chain" in n["problem"] for n in notes)


# --- fields ----------------------------------------------------------------

def test_malformed_shot_id_is_a_blocker():
    notes = severities(sc.check_fields([shot(id="shot1")], sc.DEFAULTS), "fields")
    assert any(n["severity"] == "blocker" and "malformed" in n["problem"] for n in notes)


def test_shot_id_scene_must_match_scene_field():
    notes = sc.check_fields([shot(id="s03-001", scene=1)], sc.DEFAULTS)
    assert any("disagrees" in n["problem"] for n in notes)


def test_duplicate_ids_are_rejected():
    notes = sc.check_fields([shot(id="s01-001"), shot(id="s01-001")], sc.DEFAULTS)
    assert any("Duplicate" in n["problem"] for n in notes)


def test_duration_beyond_model_ceiling_is_a_blocker():
    notes = sc.check_fields([shot(duration=22)], sc.DEFAULTS)
    assert any(n["check"] == "duration" and n["severity"] == "blocker" for n in notes)


def test_edit_points_must_lie_inside_the_clip():
    notes = sc.check_edit_points([shot(duration=8, edit_in=2, edit_out=12)])
    assert any("outside" in n["problem"] for n in notes)


def test_edit_out_must_follow_edit_in():
    notes = sc.check_edit_points([shot(duration=8, edit_in=5, edit_out=3)])
    assert any("not after" in n["problem"] for n in notes)


# --- end to end ------------------------------------------------------------

def test_fixture_film_has_no_blockers():
    film, shots, casting = sc.load_film(FIXTURE)
    report = sc.check(film, shots, casting)
    assert report["shot_count"] == 5
    assert report["counts"]["blocker"] == 0, report["notes"]


def test_report_sorts_blockers_first():
    film, shots, casting = sc.load_film(FIXTURE)
    shots[0]["duration"] = 99  # inject a blocker
    report = sc.check(film, shots, casting)
    assert report["notes"][0]["severity"] == "blocker"
