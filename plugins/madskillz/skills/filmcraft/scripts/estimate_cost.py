# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Pre-flight cost estimator and spend ledger for filmcraft.

Generation is billed per second of output, so a shot list is also an invoice. This
runs before any generation call and gates it against the film's budget cap.

Rates are configurable because published pricing moves; see `references/grok-api.md`
for provenance and how to re-verify them.

Run with `uv run estimate_cost.py <film_dir> [--ledger]`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

# USD per second of generated video, audio included. Verify against live pricing
# before relying on these — see references/grok-api.md.
DEFAULT_VIDEO_RATES = {"480p": 0.03, "720p": 0.07, "1080p": 0.14}
DEFAULT_IMAGE_RATE = 0.02  # USD per generated reference still
DEFAULT_RESOLUTION = "720p"
DEFAULT_TAKES = 1


def video_rate(resolution: str, rates: dict[str, float]) -> float:
    if resolution not in rates:
        raise KeyError(f"No rate configured for resolution {resolution!r}; known: {sorted(rates)}")
    return rates[resolution]


def estimate(film: dict, shots: list[dict], casting: dict | None = None) -> dict:
    """Project total spend for generating every shot at its configured take count."""
    rates = {**DEFAULT_VIDEO_RATES, **(film.get("video_rates") or {})}
    resolution = film.get("resolution", DEFAULT_RESOLUTION)
    rate = video_rate(resolution, rates)
    default_takes = film.get("takes", DEFAULT_TAKES)

    per_shot, total_seconds, total_cost = [], 0.0, 0.0
    for shot in shots:
        dur = shot.get("duration")
        if not isinstance(dur, (int, float)):
            continue
        takes = shot.get("takes", default_takes)
        seconds = dur * takes
        cost = seconds * rate
        total_seconds += seconds
        total_cost += cost
        per_shot.append({
            "id": shot.get("id"),
            "duration": dur,
            "takes": takes,
            "seconds": round(seconds, 2),
            "cost_usd": round(cost, 2),
        })

    # Reference plates are generated once per character and per location, then reused.
    casting = casting or {}
    image_rate = film.get("image_rate", DEFAULT_IMAGE_RATE)
    plate_count = len(casting.get("characters", {})) + len(casting.get("locations", {}))
    plate_variants = film.get("plate_variants", 3)
    plates_cost = plate_count * plate_variants * image_rate

    grand_total = total_cost + plates_cost
    budget = film.get("budget_usd")
    report = {
        "resolution": resolution,
        "rate_per_second_usd": rate,
        "shot_count": len(per_shot),
        "total_generated_seconds": round(total_seconds, 1),
        "video_cost_usd": round(total_cost, 2),
        "reference_plates": {
            "count": plate_count,
            "variants_each": plate_variants,
            "cost_usd": round(plates_cost, 2),
        },
        "total_cost_usd": round(grand_total, 2),
        "budget_usd": budget,
        "per_shot": per_shot,
    }
    if budget is not None:
        report["over_budget"] = grand_total > budget
        report["headroom_usd"] = round(budget - grand_total, 2)
    return report


def ledger(film_dir: Path) -> dict:
    """Actual spend so far, reconstructed from the generation log."""
    log_path = film_dir / "generated" / "generation-log.jsonl"
    if not log_path.exists():
        return {"entries": 0, "spent_usd": 0.0, "note": "No generation log yet."}

    entries, spent, failed = 0, 0.0, 0
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        entries += 1
        spent += rec.get("cost_usd", 0.0)
        if rec.get("status") != "done":
            failed += 1
    return {"entries": entries, "spent_usd": round(spent, 2), "failed": failed}


def load(film_dir: Path) -> tuple[dict, list[dict], dict]:
    film = yaml.safe_load((film_dir / "film.yaml").read_text()) or {}
    raw = yaml.safe_load((film_dir / "shots.yaml").read_text()) or []
    shots = raw.get("shots", []) if isinstance(raw, dict) else raw
    casting_path = film_dir / "bible" / "casting.yaml"
    casting = yaml.safe_load(casting_path.read_text()) or {} if casting_path.exists() else {}
    return film, shots, casting


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) != 1:
        print("usage: estimate_cost.py <film_dir> [--ledger]", file=sys.stderr)
        return 2

    film_dir = Path(args[0])
    try:
        film, shots, casting = load(film_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = estimate(film, shots, casting)
    if "--ledger" in flags:
        report["actual_spend"] = ledger(film_dir)

    print(json.dumps(report, indent=2))
    return 1 if report.get("over_budget") else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
