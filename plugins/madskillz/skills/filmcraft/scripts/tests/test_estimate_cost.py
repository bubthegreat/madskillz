import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import estimate_cost as ec  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "tinyfilm"


def test_cost_is_seconds_times_takes_times_rate():
    film = {"resolution": "720p", "takes": 1}
    shots = [{"id": "s01-001", "duration": 10, "takes": 3}]
    report = ec.estimate(film, shots)
    # 10s x 3 takes x $0.07
    assert report["total_generated_seconds"] == 30.0
    assert report["video_cost_usd"] == pytest.approx(2.10)


def test_film_level_takes_apply_when_a_shot_omits_them():
    report = ec.estimate({"takes": 2}, [{"id": "s01-001", "duration": 5}])
    assert report["per_shot"][0]["takes"] == 2
    assert report["total_generated_seconds"] == 10.0


def test_resolution_changes_the_rate():
    shots = [{"id": "s01-001", "duration": 10, "takes": 1}]
    cheap = ec.estimate({"resolution": "480p"}, shots)["video_cost_usd"]
    dear = ec.estimate({"resolution": "1080p"}, shots)["video_cost_usd"]
    assert cheap < dear


def test_rates_are_overridable_from_film_config():
    report = ec.estimate({"resolution": "720p", "video_rates": {"720p": 1.00}},
                         [{"id": "s01-001", "duration": 2, "takes": 1}])
    assert report["video_cost_usd"] == pytest.approx(2.00)


def test_unknown_resolution_raises_rather_than_guessing():
    with pytest.raises(KeyError, match="4k"):
        ec.estimate({"resolution": "4k"}, [{"id": "s", "duration": 1}])


def test_reference_plates_are_costed_per_character_and_location():
    casting = {"characters": {"a": {}, "b": {}}, "locations": {"study": {}}}
    report = ec.estimate({"plate_variants": 2, "image_rate": 0.10}, [], casting)
    assert report["reference_plates"]["count"] == 3
    assert report["reference_plates"]["cost_usd"] == pytest.approx(0.60)


def test_budget_headroom_and_over_budget_flag():
    shots = [{"id": "s01-001", "duration": 10, "takes": 10}]  # $7.00
    assert ec.estimate({"budget_usd": 100}, shots)["over_budget"] is False
    tight = ec.estimate({"budget_usd": 1}, shots)
    assert tight["over_budget"] is True
    assert tight["headroom_usd"] < 0


def test_shots_without_a_duration_are_skipped():
    report = ec.estimate({}, [{"id": "s01-001"}, {"id": "s01-002", "duration": 4}])
    assert report["shot_count"] == 1


def test_fixture_film_is_within_its_budget():
    film, shots, casting = ec.load(FIXTURE)
    report = ec.estimate(film, shots, casting)
    assert report["over_budget"] is False
    assert report["total_cost_usd"] > 0


# --- ledger ----------------------------------------------------------------

def test_ledger_is_empty_when_nothing_generated(tmp_path):
    assert ec.ledger(tmp_path)["spent_usd"] == 0.0


def test_ledger_sums_spend_and_counts_failures(tmp_path):
    log = tmp_path / "generated" / "generation-log.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(
        json.dumps({"shot": "a", "status": "done", "cost_usd": 1.5}) + "\n"
        + json.dumps({"shot": "b", "status": "failed", "cost_usd": 0.0}) + "\n"
    )
    result = ec.ledger(tmp_path)
    assert result["entries"] == 2
    assert result["spent_usd"] == 1.5
    assert result["failed"] == 1


def test_ledger_tolerates_a_corrupt_line(tmp_path):
    log = tmp_path / "generated" / "generation-log.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text("{not json}\n" + json.dumps({"status": "done", "cost_usd": 2.0}) + "\n")
    assert ec.ledger(tmp_path)["spent_usd"] == 2.0
