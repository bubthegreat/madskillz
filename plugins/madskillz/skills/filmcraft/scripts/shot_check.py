# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Deterministic shot-list validator for filmcraft.

Catches the film-grammar and continuity errors that are checkable by machine, so the
production crew personas spend their judgment on the ones that are not — and so no
money is spent generating a shot list that was broken on paper.

Pure stdlib + pyyaml; run with `uv run shot_check.py <film_dir>`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

SHOT_ID = re.compile(r"^s(\d{2})-(\d{3})$")

# Shot sizes ordered wide → tight. The index distance between two sizes is what
# makes a cut read as a cut rather than a jump.
SIZE_ORDER = ["EWS", "WS", "MWS", "MS", "MCU", "CU", "ECU"]
WIDE_SIZES = frozenset({"EWS", "WS", "MWS"})

VALID_ANGLES = frozenset({"eye", "low", "high", "dutch", "overhead", "worm"})
VALID_MODES = frozenset({"text", "image", "reference", "extend"})
VALID_SCREEN_DIR = frozenset({"L→R", "R→L", "neutral", "to-cam", "from-cam"})

# Conversational delivery. Deliberately conservative: generated actors rush, and a
# line that only just fits at 3.0 wps will be clipped at the tail.
DEFAULT_WORDS_PER_SECOND = 2.5

# Seconds of the clip that dialogue may not claim, reserved for the actor to arrive,
# settle, and land the beat. Without this, every line starts on frame 1.
DIALOGUE_HEADROOM_SECONDS = 1.2

DEFAULTS = {
    "min_clip_seconds": 1,
    "max_clip_seconds": 15,
    "max_extend_chain": 3,
    "words_per_second": DEFAULT_WORDS_PER_SECOND,
}


def _note(severity: str, shot: str, problem: str, fix: str, check: str) -> dict:
    return {
        "severity": severity,
        "shot": shot,
        "check": check,
        "problem": problem,
        "suggested_fix": fix,
    }


def word_count(line: str) -> int:
    return len(re.findall(r"[\w']+", line or ""))


def dialogue_seconds(line: str, words_per_second: float = DEFAULT_WORDS_PER_SECOND) -> float:
    """Wall-clock seconds to deliver `line`, excluding headroom."""
    if words_per_second <= 0:
        raise ValueError("words_per_second must be positive")
    return word_count(line) / words_per_second


def size_distance(a: str, b: str) -> int | None:
    """Steps apart on the wide→tight ladder, or None if either size is unknown."""
    if a not in SIZE_ORDER or b not in SIZE_ORDER:
        return None
    return abs(SIZE_ORDER.index(a) - SIZE_ORDER.index(b))


def check_fields(shots: list[dict], cfg: dict) -> list[dict]:
    """Required fields, id format/uniqueness, enum membership, duration bounds."""
    notes: list[dict] = []
    seen: set[str] = set()
    lo, hi = cfg["min_clip_seconds"], cfg["max_clip_seconds"]

    for idx, shot in enumerate(shots):
        sid = shot.get("id") or f"<index {idx}>"

        for field in ("id", "scene", "mode", "duration"):
            if shot.get(field) is None:
                notes.append(_note("blocker", sid, f"Missing required field `{field}`.",
                                   f"Add `{field}` to the shot.", "fields"))

        if shot.get("id"):
            m = SHOT_ID.match(shot["id"])
            if not m:
                notes.append(_note("blocker", sid, f"Shot id `{shot['id']}` is malformed.",
                                   "Use `sNN-NNN`, e.g. `s02-004`.", "fields"))
            elif shot.get("scene") is not None and int(m.group(1)) != int(shot["scene"]):
                notes.append(_note("blocker", sid,
                                   f"Shot id scene `{m.group(1)}` disagrees with `scene: {shot['scene']}`.",
                                   "Renumber the shot id or correct `scene`.", "fields"))
            if shot["id"] in seen:
                notes.append(_note("blocker", sid, f"Duplicate shot id `{shot['id']}`.",
                                   "Shot ids must be unique across the film.", "fields"))
            seen.add(shot["id"])

        mode = shot.get("mode")
        if mode is not None and mode not in VALID_MODES:
            notes.append(_note("blocker", sid, f"Unknown mode `{mode}`.",
                               f"Use one of: {', '.join(sorted(VALID_MODES))}.", "fields"))

        angle = shot.get("angle")
        if angle is not None and angle not in VALID_ANGLES:
            notes.append(_note("minor", sid, f"Unknown camera angle `{angle}`.",
                               f"Use one of: {', '.join(sorted(VALID_ANGLES))}.", "fields"))

        size = shot.get("size")
        if size is not None and size not in SIZE_ORDER:
            notes.append(_note("minor", sid, f"Unknown shot size `{size}`.",
                               f"Use one of: {', '.join(SIZE_ORDER)}.", "fields"))

        sdir = shot.get("screen_dir")
        if sdir is not None and sdir not in VALID_SCREEN_DIR:
            notes.append(_note("minor", sid, f"Unknown screen direction `{sdir}`.",
                               f"Use one of: {', '.join(sorted(VALID_SCREEN_DIR))}.", "fields"))

        dur = shot.get("duration")
        if isinstance(dur, (int, float)) and not (lo <= dur <= hi):
            notes.append(_note("blocker", sid, f"Duration {dur}s is outside the model's {lo}–{hi}s range.",
                               f"Set a duration between {lo} and {hi}, or split the shot.", "duration"))
    return notes


def check_dialogue_budget(shots: list[dict], cfg: dict) -> list[dict]:
    """Dialogue that cannot physically be delivered inside the generated clip."""
    notes: list[dict] = []
    wps = cfg["words_per_second"]

    for shot in shots:
        line = shot.get("dialogue")
        dur = shot.get("duration")
        if not line or not isinstance(dur, (int, float)):
            continue
        needed = dialogue_seconds(line, wps)
        available = dur - DIALOGUE_HEADROOM_SECONDS
        if needed > available:
            fits = max(0, int(available * wps))
            notes.append(_note(
                "blocker", shot.get("id", "?"),
                f"Dialogue needs ~{needed:.1f}s (+{DIALOGUE_HEADROOM_SECONDS}s headroom) "
                f"but the clip is {dur}s — {word_count(line)} words will be clipped.",
                f"Cut the line to ~{fits} words, raise duration to "
                f"{needed + DIALOGUE_HEADROOM_SECONDS:.0f}s, or split across two shots.",
                "dialogue"))
    return notes


def check_edit_points(shots: list[dict]) -> list[dict]:
    """`edit_in`/`edit_out` must describe a real span inside the generated clip."""
    notes: list[dict] = []
    for shot in shots:
        sid = shot.get("id", "?")
        dur, ein, eout = shot.get("duration"), shot.get("edit_in"), shot.get("edit_out")
        if ein is None and eout is None:
            continue
        ein = 0.0 if ein is None else ein
        eout = dur if eout is None else eout
        if not isinstance(dur, (int, float)):
            continue
        if ein < 0 or eout > dur:
            notes.append(_note("major", sid,
                               f"Edit points [{ein}, {eout}] fall outside the {dur}s clip.",
                               f"Keep both within 0–{dur}.", "edit_points"))
        if eout <= ein:
            notes.append(_note("major", sid, f"`edit_out` ({eout}) is not after `edit_in` ({ein}).",
                               "Give the shot a positive on-screen duration.", "edit_points"))
    return notes


def _by_scene(shots: list[dict]) -> dict[int, list[dict]]:
    scenes: dict[int, list[dict]] = {}
    for shot in shots:
        scene = shot.get("scene")
        if scene is not None:
            scenes.setdefault(int(scene), []).append(shot)
    return scenes


def check_axis(shots: list[dict]) -> list[dict]:
    """The 180-degree rule: screen direction must not flip without an acknowledged break.

    Two consecutive shots in a scene whose subjects face opposite directions read as
    the geography inverting. Real productions cross the axis deliberately, via a
    neutral shot or a visible camera move — so an explicit `axis_break: true` clears it.
    """
    notes: list[dict] = []
    opposed = {("L→R", "R→L"), ("R→L", "L→R")}

    for scene, group in sorted(_by_scene(shots).items()):
        for prev, cur in zip(group, group[1:]):
            pair = (prev.get("screen_dir"), cur.get("screen_dir"))
            if pair not in opposed:
                continue
            if cur.get("axis_break"):
                continue
            notes.append(_note(
                "major", cur.get("id", "?"),
                f"Screen direction flips {pair[0]} → {pair[1]} straight after "
                f"{prev.get('id')} — crosses the 180° line, so the geography inverts on the cut.",
                "Insert a neutral (`to-cam`/`from-cam`) shot between them, match the direction, "
                "or set `axis_break: true` if the cross is intentional.",
                "axis"))
    return notes


def check_jump_cuts(shots: list[dict]) -> list[dict]:
    """Adjacent shots too similar to read as a cut rather than a glitch.

    The editing convention is to change size by at least two steps or change the
    angle. Same size + same angle back-to-back on the same subject is a jump cut.
    """
    notes: list[dict] = []
    for scene, group in sorted(_by_scene(shots).items()):
        for prev, cur in zip(group, group[1:]):
            if cur.get("mode") == "extend" and cur.get("extend_from") == prev.get("id"):
                continue  # a continuous extension, not a cut
            dist = size_distance(prev.get("size"), cur.get("size"))
            if dist is None:
                continue
            same_angle = prev.get("angle") == cur.get("angle")
            if dist == 0 and same_angle:
                notes.append(_note(
                    "major", cur.get("id", "?"),
                    f"Identical framing to {prev.get('id')} ({cur.get('size')}, {cur.get('angle')}) — "
                    "this cut will read as a jump cut.",
                    "Change size by at least two steps (e.g. MS → CU) or change the angle.",
                    "jump_cut"))
            elif dist == 1 and same_angle:
                notes.append(_note(
                    "minor", cur.get("id", "?"),
                    f"Only one size step from {prev.get('id')} at the same angle — a weak cut.",
                    "Widen the size delta to two steps, or vary the angle.",
                    "jump_cut"))
    return notes


def check_coverage(shots: list[dict]) -> list[dict]:
    """Every scene needs a wide shot to establish where the audience is standing."""
    notes: list[dict] = []
    for scene, group in sorted(_by_scene(shots).items()):
        if not any(s.get("size") in WIDE_SIZES for s in group):
            notes.append(_note(
                "major", group[0].get("id", "?"),
                f"Scene {scene:02d} has no wide shot — the audience never learns the geography.",
                "Add an establishing EWS/WS/MWS, usually at the head of the scene.",
                "coverage"))
    return notes


def check_references(shots: list[dict], casting: dict, cfg: dict) -> list[dict]:
    """Reference and extend-chain integrity — the things that fail at generation time."""
    notes: list[dict] = []
    known_chars = set(casting.get("characters", {}))
    known_voices = set(casting.get("voices", {}))
    ids = {s.get("id") for s in shots}
    order = {s.get("id"): i for i, s in enumerate(shots)}

    for shot in shots:
        sid = shot.get("id", "?")
        refs = shot.get("refs") or {}

        for char in refs.get("characters", []) or []:
            if char not in known_chars:
                notes.append(_note("blocker", sid, f"Character `{char}` has no locked reference plate.",
                                   f"Add `{char}` to casting and lock a plate before generating.",
                                   "references"))
        voice = refs.get("voice")
        if voice and voice not in known_voices:
            notes.append(_note("blocker", sid, f"Voice ref `{voice}` is not defined in casting.",
                               f"Add `{voice}` to casting voices, or drop the voice ref.", "references"))

        if shot.get("mode") == "reference" and not refs:
            notes.append(_note("blocker", sid, "Mode is `reference` but no `refs` are given.",
                               "Add `refs.characters` / `refs.voice`, or change the mode.", "references"))

        src = shot.get("extend_from")
        if shot.get("mode") == "extend" and not src:
            notes.append(_note("blocker", sid, "Mode is `extend` but `extend_from` is unset.",
                               "Point `extend_from` at the shot this continues.", "references"))
        if src:
            if src not in ids:
                notes.append(_note("blocker", sid, f"`extend_from: {src}` refers to an unknown shot.",
                                   "Fix the reference to an existing shot id.", "references"))
            elif order.get(src, 0) >= order.get(sid, 0):
                notes.append(_note("blocker", sid, f"`extend_from: {src}` points at a later shot.",
                                   "A shot can only extend one that precedes it.", "references"))

    # Extension chains drift: each hop compounds the previous hop's error.
    parent = {s["id"]: s.get("extend_from") for s in shots if s.get("id")}
    for sid in parent:
        depth, cursor, guard = 0, parent.get(sid), 0
        while cursor and guard < 100:
            depth += 1
            cursor = parent.get(cursor)
            guard += 1
        if depth > cfg["max_extend_chain"]:
            notes.append(_note(
                "major", sid,
                f"Extension chain is {depth} deep (limit {cfg['max_extend_chain']}) — "
                "visual drift compounds at every hop.",
                "Re-anchor with a fresh reference-mode shot instead of extending again.",
                "references"))
    return notes


def check_runtime(shots: list[dict], film: dict) -> list[dict]:
    """Cut runtime against the film's stated target."""
    target = film.get("target_runtime_seconds")
    if not target:
        return []
    total = 0.0
    for shot in shots:
        dur = shot.get("duration")
        if not isinstance(dur, (int, float)):
            continue
        ein = shot.get("edit_in") or 0.0
        eout = shot.get("edit_out") if shot.get("edit_out") is not None else dur
        total += max(0.0, eout - ein)

    drift = (total - target) / target if target else 0
    if abs(drift) > 0.20:
        direction = "over" if drift > 0 else "under"
        return [_note("minor", "<film>",
                      f"Cut runtime is {total:.0f}s vs a {target}s target — {abs(drift) * 100:.0f}% {direction}.",
                      "Add or trim shots, or update `target_runtime_seconds`.", "runtime")]
    return []


def load_film(film_dir: Path) -> tuple[dict, list[dict], dict]:
    film_path, shots_path = film_dir / "film.yaml", film_dir / "shots.yaml"
    if not film_path.exists():
        raise FileNotFoundError(f"No film.yaml in {film_dir}")
    if not shots_path.exists():
        raise FileNotFoundError(f"No shots.yaml in {film_dir}")

    film = yaml.safe_load(film_path.read_text()) or {}
    raw = yaml.safe_load(shots_path.read_text()) or []
    shots = raw.get("shots", []) if isinstance(raw, dict) else raw

    casting_path = film_dir / "bible" / "casting.yaml"
    casting = yaml.safe_load(casting_path.read_text()) or {} if casting_path.exists() else {}
    return film, shots, casting


def check(film: dict, shots: list[dict], casting: dict) -> dict:
    cfg = {**DEFAULTS, **{k: v for k, v in film.items() if k in DEFAULTS and v is not None}}
    notes = (
        check_fields(shots, cfg)
        + check_dialogue_budget(shots, cfg)
        + check_edit_points(shots)
        + check_axis(shots)
        + check_jump_cuts(shots)
        + check_coverage(shots)
        + check_references(shots, casting, cfg)
        + check_runtime(shots, film)
    )
    rank = {"blocker": 0, "major": 1, "minor": 2}
    notes.sort(key=lambda n: (rank.get(n["severity"], 9), n["shot"]))
    counts = {sev: sum(1 for n in notes if n["severity"] == sev) for sev in rank}
    return {"shot_count": len(shots), "counts": counts, "notes": notes}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: shot_check.py <film_dir>", file=sys.stderr)
        return 2
    try:
        film, shots, casting = load_film(Path(argv[1]))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = check(film, shots, casting)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    # Blockers fail the run: they are the errors that waste generation spend.
    return 1 if report["counts"]["blocker"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
