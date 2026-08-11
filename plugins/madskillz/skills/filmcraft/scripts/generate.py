# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Compile shots into prompts and (optionally) drive generation.

Two modes, chosen by whether credentials exist:

  packet mode  (no API key) — writes paste-ready prompt files. Zero cost, zero
                                  network. This is also the manual fallback.
  live mode    (XAI_API_KEY or GROK_API_KEY set) — submits, polls, downloads clips, appends to the
                                  spend ledger.

Prompt compilation is deterministic: the same shot plus the same bible always yields
byte-identical prompt text, so any drift between takes came from the model, not from us.

Run with `uv run generate.py <film_dir> [--shots s01-001,s01-002] [--packet] [--yes]`.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grok_client import GrokVideoClient, MissingAPIKey  # noqa: E402
import estimate_cost  # noqa: E402

SIZE_PHRASE = {
    "EWS": "extreme wide shot",
    "WS": "wide shot",
    "MWS": "medium wide shot",
    "MS": "medium shot",
    "MCU": "medium close-up",
    "CU": "close-up",
    "ECU": "extreme close-up",
}
ANGLE_PHRASE = {
    "eye": "eye-level",
    "low": "low angle looking up",
    "high": "high angle looking down",
    "dutch": "canted dutch angle",
    "overhead": "overhead top-down",
    "worm": "ground-level worm's-eye",
}


def compile_prompt(shot: dict, bible: dict) -> str:
    """Assemble one shot's generation prompt from the shot row and locked canon.

    Order matters: camera first (the model treats leading tokens as the frame), then
    subject and action, then the verbatim lockups, then the global look. Lockups are
    pasted exactly as written — paraphrasing a lockup recasts the character.
    """
    characters = bible.get("characters", {})
    locations = bible.get("locations", {})
    look = bible.get("look", {})

    parts: list[str] = []

    camera = [SIZE_PHRASE.get(shot.get("size"), ""), ANGLE_PHRASE.get(shot.get("angle"), "")]
    move = shot.get("move")
    if move:
        camera.append(f"camera {move}")
    camera_str = ", ".join(p for p in camera if p)
    if camera_str:
        parts.append(camera_str.capitalize() + ".")

    if shot.get("beat"):
        parts.append(shot["beat"].rstrip(".") + ".")

    for name in (shot.get("refs") or {}).get("characters", []) or []:
        lockup = characters.get(name, {}).get("lockup")
        if lockup:
            parts.append(lockup.rstrip(".") + ".")

    loc = shot.get("location")
    if loc and loc in locations:
        plate = locations[loc].get("lockup")
        if plate:
            parts.append(plate.rstrip(".") + ".")

    if shot.get("prompt_extra"):
        parts.append(shot["prompt_extra"].rstrip(".") + ".")

    look_bits = [look.get(k) for k in ("stock", "lens", "lighting", "palette", "grade")]
    look_str = ", ".join(b for b in look_bits if b)
    if look_str:
        parts.append(look_str.rstrip(".") + ".")

    if shot.get("dialogue"):
        speaker = shot.get("speaker")
        who = f"{speaker} says" if speaker else "Dialogue"
        parts.append(f'{who}: "{shot["dialogue"]}"')

    if look.get("negative"):
        parts.append(f"Avoid: {look['negative']}.")

    return " ".join(parts)


def shot_request(shot: dict, film: dict, bible: dict) -> dict:
    """Build the client kwargs for one shot, honouring its generation mode."""
    refs = shot.get("refs") or {}
    kwargs: dict = {
        "duration": shot.get("duration"),
        "resolution": film.get("resolution", "720p"),
        "aspect_ratio": film.get("aspect_ratio"),
        "n": shot.get("takes", film.get("takes", 1)),
    }
    mode = shot.get("mode")
    characters = bible.get("characters", {})

    if mode == "reference":
        plates = [
            characters[c]["plate"]
            for c in refs.get("characters", []) or []
            if c in characters and characters[c].get("plate")
        ]
        if plates:
            kwargs["reference_images"] = plates
        if refs.get("voice"):
            kwargs["voice"] = bible.get("voices", {}).get(refs["voice"], {}).get("ref", refs["voice"])
    elif mode == "image":
        if shot.get("image"):
            kwargs["image_url"] = shot["image"]
    # mode "extend" goes through client.extend() with the source shot's
    # delivered URL — the extensions endpoint takes no duration/resolution/n.

    return {k: v for k, v in kwargs.items() if v is not None}


def write_packet(film_dir: Path, shots: list[dict], bible: dict, film: dict) -> Path:
    """Emit paste-ready prompts for manual generation in the Grok app."""
    out = film_dir / "packet"
    out.mkdir(parents=True, exist_ok=True)

    index: list[str] = [
        f"# Prompt packet — {film.get('title', film_dir.name)}",
        "",
        f"{len(shots)} shots. Paste each prompt into Grok Imagine, then save the result as",
        "`generated/<shot-id>_t<NN>.mp4` so `assemble.py` can find it.",
        "",
    ]
    for shot in shots:
        sid = shot.get("id", "unknown")
        prompt = compile_prompt(shot, bible)
        meta = [
            f"shot: {sid}",
            f"mode: {shot.get('mode')}",
            f"duration: {shot.get('duration')}s",
            f"takes: {shot.get('takes', film.get('takes', 1))}",
        ]
        if shot.get("extend_from"):
            meta.append(f"extend_from: {shot['extend_from']}")
        (out / f"{sid}.txt").write_text("\n".join(f"# {m}" for m in meta) + "\n\n" + prompt + "\n")
        index.append(f"- `{sid}` — {shot.get('beat', '')}")

    index_path = out / "README.md"
    index_path.write_text("\n".join(index) + "\n")
    return out


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as resp, dest.open("wb") as fh:
        fh.write(resp.read())
    return dest


def log_generation(film_dir: Path, record: dict) -> None:
    log_path = film_dir / "generated" / "generation-log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def run_live(film_dir: Path, shots: list[dict], bible: dict, film: dict,
             client: GrokVideoClient) -> list[dict]:
    """Generate every selected shot, downloading takes and logging spend."""
    rates = {**estimate_cost.DEFAULT_VIDEO_RATES, **(film.get("video_rates") or {})}
    rate = estimate_cost.video_rate(film.get("resolution", "720p"), rates)
    produced: list[dict] = []
    by_id = {s.get("id"): s for s in shots}

    for shot in shots:
        sid = shot.get("id")
        source_url = None
        if shot.get("mode") == "extend":
            src = by_id.get(shot.get("extend_from"), {})
            # Extension needs the source's delivered URL, this run — the URLs
            # are temporary, so a cross-run extend must regenerate the source.
            source_url = src.get("_selected_url")
            if not source_url:
                print(f"warn: {sid} extends {shot.get('extend_from')} which has no delivered "
                      f"clip this run — skipping.", file=sys.stderr)
                continue

        prompt = compile_prompt(shot, bible)
        try:
            if source_url:
                result = client.extend(source_url, prompt,
                                       duration=shot.get("duration"))
            else:
                result = client.generate(prompt, **shot_request(shot, film, bible))
        except Exception as exc:  # surface the real failure; never fake a clip
            print(f"error: {sid} failed to generate: {exc}", file=sys.stderr)
            log_generation(film_dir, {"shot": sid, "status": "failed", "error": str(exc),
                                      "cost_usd": 0.0})
            continue

        paths = []
        for take_no, url in enumerate(result["urls"], start=1):
            dest = film_dir / "generated" / f"{sid}_t{take_no:02d}.mp4"
            paths.append(str(download(url, dest)))

        seconds = (shot.get("duration") or 0) * max(1, len(paths))
        record = {
            "shot": sid,
            "status": "done",
            "request_id": result["request_id"],
            "takes": len(paths),
            "paths": paths,
            "cost_usd": round(seconds * rate, 4),
            "prompt": prompt,
        }
        log_generation(film_dir, record)
        if paths:
            shot["_selected_path"] = paths[0]
        if result["urls"]:
            shot["_selected_url"] = result["urls"][0]
        produced.append(record)
        print(f"ok: {sid} — {len(paths)} take(s), ${record['cost_usd']:.2f}")

    return produced


def load(film_dir: Path) -> tuple[dict, list[dict], dict]:
    film = yaml.safe_load((film_dir / "film.yaml").read_text()) or {}
    raw = yaml.safe_load((film_dir / "shots.yaml").read_text()) or []
    shots = raw.get("shots", []) if isinstance(raw, dict) else raw

    bible: dict = {}
    casting_path = film_dir / "bible" / "casting.yaml"
    if casting_path.exists():
        bible.update(yaml.safe_load(casting_path.read_text()) or {})
    look_path = film_dir / "bible" / "look.yaml"
    if look_path.exists():
        bible["look"] = yaml.safe_load(look_path.read_text()) or {}
    return film, shots, bible


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a.split("=")[0]: a.partition("=")[2] for a in argv[1:] if a.startswith("--")}
    if len(args) != 1:
        print("usage: generate.py <film_dir> [--shots ids] [--packet] [--yes]", file=sys.stderr)
        return 2

    film_dir = Path(args[0])
    film, shots, bible = load(film_dir)

    if flags.get("--shots"):
        wanted = {s.strip() for s in flags["--shots"].split(",")}
        shots = [s for s in shots if s.get("id") in wanted]
        if not shots:
            print("error: --shots matched no shots.", file=sys.stderr)
            return 2

    client = GrokVideoClient(model=film.get("model", "grok-imagine-video-1.5"))

    if "--packet" in flags or not client.available:
        out = write_packet(film_dir, shots, bible, film)
        why = "requested" if "--packet" in flags else "no API key set"
        print(f"packet mode ({why}): wrote {len(shots)} prompts to {out}")
        return 0

    report = estimate_cost.estimate(film, shots, bible)
    print(f"About to generate {report['shot_count']} shots "
          f"({report['total_generated_seconds']}s) for ~${report['video_cost_usd']:.2f}.")
    if report.get("over_budget"):
        print(f"error: estimate exceeds budget_usd={film.get('budget_usd')}. "
              f"Raise the cap or trim the shot list.", file=sys.stderr)
        return 1
    if "--yes" not in flags:
        print("Re-run with --yes to confirm and spend.", file=sys.stderr)
        return 1

    try:
        produced = run_live(film_dir, shots, bible, film, client)
    except MissingAPIKey as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    spent = sum(r["cost_usd"] for r in produced)
    print(f"\nGenerated {len(produced)}/{len(shots)} shots. Spend this run: ${spent:.2f}")
    return 0 if len(produced) == len(shots) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
