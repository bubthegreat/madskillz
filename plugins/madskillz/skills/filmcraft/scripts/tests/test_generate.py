import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import generate as gen  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "tinyfilm"

BIBLE = {
    "characters": {
        "elena": {"lockup": "ELENA, thirties, olive field jacket, brass pendant",
                  "plate": "bible/plates/elena-03.png"},
    },
    "locations": {"study": {"lockup": "A cramped book-lined study, rain on the window"}},
    "voices": {"elena_vo": {"ref": "bible/voices/elena.wav"}},
    "look": {"stock": "shot on 35mm", "lens": "40mm", "negative": "watermarks"},
}

SHOT = {
    "id": "s01-002", "scene": 1, "mode": "reference", "duration": 8,
    "beat": "Elena turns the pendant over in the lamplight",
    "location": "study", "size": "CU", "angle": "eye", "move": "slow push in",
    "refs": {"characters": ["elena"], "voice": "elena_vo"},
    "speaker": "ELENA", "dialogue": "This isn't hers.",
}


# --- prompt compilation ----------------------------------------------------

def test_prompt_leads_with_camera():
    assert gen.compile_prompt(SHOT, BIBLE).startswith("Close-up, eye-level, camera slow push in.")


def test_prompt_includes_lockup_verbatim():
    # Paraphrasing a lockup recasts the character, so it must appear exactly.
    assert BIBLE["characters"]["elena"]["lockup"] in gen.compile_prompt(SHOT, BIBLE)


def test_prompt_includes_location_and_look():
    prompt = gen.compile_prompt(SHOT, BIBLE)
    assert "cramped book-lined study" in prompt
    assert "shot on 35mm, 40mm" in prompt


def test_prompt_attributes_dialogue_to_the_speaker():
    assert 'ELENA says: "This isn\'t hers."' in gen.compile_prompt(SHOT, BIBLE)


def test_prompt_appends_negative_terms_last():
    assert gen.compile_prompt(SHOT, BIBLE).endswith("Avoid: watermarks.")


def test_prompt_is_deterministic():
    assert gen.compile_prompt(SHOT, BIBLE) == gen.compile_prompt(SHOT, BIBLE)


def test_prompt_omits_dialogue_when_absent():
    silent = {k: v for k, v in SHOT.items() if k not in ("dialogue", "speaker")}
    assert "says" not in gen.compile_prompt(silent, BIBLE)


def test_unknown_character_contributes_no_lockup():
    shot = {**SHOT, "refs": {"characters": ["ghost"]}}
    assert BIBLE["characters"]["elena"]["lockup"] not in gen.compile_prompt(shot, BIBLE)


# --- request construction --------------------------------------------------

def test_reference_mode_sends_plates_and_voice():
    kwargs = gen.shot_request(SHOT, {"resolution": "720p"}, BIBLE)
    assert kwargs["reference_images"] == ["bible/plates/elena-03.png"]
    assert kwargs["voice"] == "bible/voices/elena.wav"


def test_extend_mode_sends_resolved_source():
    shot = {**SHOT, "mode": "extend", "_resolved_source": "generated/s01-001_t01.mp4"}
    assert gen.shot_request(shot, {}, BIBLE)["source_video"] == "generated/s01-001_t01.mp4"


def test_image_mode_sends_image_url():
    shot = {**SHOT, "mode": "image", "image": "plates/frame.png"}
    assert gen.shot_request(shot, {}, BIBLE)["image_url"] == "plates/frame.png"


def test_takes_become_the_n_parameter():
    assert gen.shot_request({**SHOT, "takes": 3}, {}, BIBLE)["n"] == 3


def test_request_omits_none_values():
    assert None not in gen.shot_request(SHOT, {}, BIBLE).values()


# --- packet mode -----------------------------------------------------------

def test_packet_mode_writes_one_file_per_shot(tmp_path):
    shots = [SHOT, {**SHOT, "id": "s01-003"}]
    out = gen.write_packet(tmp_path, shots, BIBLE, {"title": "T"})
    assert (out / "s01-002.txt").exists()
    assert (out / "s01-003.txt").exists()
    assert (out / "README.md").exists()


def test_packet_file_contains_metadata_header_and_prompt(tmp_path):
    out = gen.write_packet(tmp_path, [SHOT], BIBLE, {})
    text = (out / "s01-002.txt").read_text()
    assert "# shot: s01-002" in text
    assert "# duration: 8s" in text
    assert "ELENA, thirties" in text


def test_packet_readme_tells_you_the_ingest_filename(tmp_path):
    out = gen.write_packet(tmp_path, [SHOT], BIBLE, {})
    assert "generated/<shot-id>_t<NN>.mp4" in (out / "README.md").read_text()


# --- loading ---------------------------------------------------------------

def test_load_reads_film_shots_and_bible_from_fixture():
    film, shots, bible = gen.load(FIXTURE)
    assert film["slug"] == "tinyfilm"
    assert len(shots) == 5
    assert "elena" in bible["characters"]
    assert bible["look"]["lens"].startswith("40mm")


def test_fixture_shots_all_compile_to_nonempty_prompts():
    _, shots, bible = gen.load(FIXTURE)
    assert all(len(gen.compile_prompt(s, bible)) > 80 for s in shots)
