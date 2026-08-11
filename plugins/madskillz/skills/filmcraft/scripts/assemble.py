# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Cut the selected takes into a film.

Trims each selected take to its edit points, conforms everything to one format, and
concatenates in shot order. Also builds a contact sheet and an animatic so the edit
can be judged before — and after — generation spend.

Command construction is pure and testable; `--dry-run` prints the ffmpeg calls
without running them, which is how this is exercised on machines without ffmpeg.

Run with `uv run assemble.py <film_dir> [--dry-run] [--animatic]`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def selected_take(film_dir: Path, shot: dict) -> Path | None:
    """Resolve the take chosen for a shot: explicit `select`, else the first on disk."""
    sid = shot.get("id")
    gen = film_dir / "generated"
    if shot.get("select"):
        cand = gen / shot["select"]
        return cand if cand.exists() else None
    matches = sorted(gen.glob(f"{sid}_t*.mp4"))
    return matches[0] if matches else None


def trim_command(src: Path, dest: Path, shot: dict, film: dict) -> list[str]:
    """ffmpeg call trimming one take to its edit points and conforming it."""
    ein = shot.get("edit_in") or 0.0
    eout = shot.get("edit_out")
    dur = shot.get("duration")
    span = (eout if eout is not None else dur) - ein

    fps = str(film.get("fps", 24))
    width, height = str(film.get("width", 1280)), str(film.get("height", 720))

    return [
        "ffmpeg", "-y",
        "-ss", f"{ein:.3f}",
        "-i", str(src),
        "-t", f"{span:.3f}",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        str(dest),
    ]


def concat_command(list_file: Path, dest: Path) -> list[str]:
    return ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy", str(dest)]


def mix_command(video: Path, audio: Path, dest: Path) -> list[str]:
    """Lay a music/VO bed under the cut, keeping existing clip audio underneath it."""
    return [
        "ffmpeg", "-y", "-i", str(video), "-i", str(audio),
        "-filter_complex", "[0:a]volume=1.0[a0];[1:a]volume=0.35[a1];"
                           "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(dest),
    ]


def contact_sheet_command(clips: list[Path], dest: Path) -> list[str]:
    """One frame per shot, tiled — the storyboard as it actually came out."""
    cmd: list[str] = ["ffmpeg", "-y"]
    for clip in clips:
        cmd += ["-i", str(clip)]
    n = len(clips)
    cols = min(5, n) or 1
    rows = (n + cols - 1) // cols
    streams = "".join(f"[{i}:v]scale=320:180,setsar=1[v{i}];" for i in range(n))
    inputs = "".join(f"[v{i}]" for i in range(n))
    cmd += ["-filter_complex", f"{streams}{inputs}xstack=inputs={n}:"
                               f"layout={_xstack_layout(cols, rows, n)}[out]",
            "-map", "[out]", "-frames:v", "1", str(dest)]
    return cmd


def _xstack_layout(cols: int, rows: int, n: int) -> str:
    cells = []
    for i in range(n):
        col, row = i % cols, i // cols
        cells.append(f"{'0' if col == 0 else '+'.join(['w0'] * col)}_"
                     f"{'0' if row == 0 else '+'.join(['h0'] * row)}")
    return "|".join(cells)


def plan(film_dir: Path, film: dict, shots: list[dict]) -> dict:
    """Work out what can be cut and what is missing, without touching the disk."""
    work = film_dir / "build" / "conformed"
    steps, missing, clips = [], [], []

    for shot in shots:
        sid = shot.get("id")
        src = selected_take(film_dir, shot)
        if src is None:
            missing.append(sid)
            continue
        dest = work / f"{sid}.mp4"
        steps.append(trim_command(src, dest, shot, film))
        clips.append(dest)

    return {"steps": steps, "clips": clips, "missing": missing, "work_dir": work}


def run(cmds: list[list[str]], dry_run: bool) -> int:
    for cmd in cmds:
        if dry_run:
            print(" ".join(cmd))
            continue
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            # Report the real ffmpeg error; never claim a build that did not happen.
            print(f"error: ffmpeg failed ({proc.returncode}):\n{proc.stderr[-1500:]}",
                  file=sys.stderr)
            return proc.returncode
    return 0


def load(film_dir: Path) -> tuple[dict, list[dict]]:
    film = yaml.safe_load((film_dir / "film.yaml").read_text()) or {}
    raw = yaml.safe_load((film_dir / "shots.yaml").read_text()) or []
    shots = raw.get("shots", []) if isinstance(raw, dict) else raw
    return film, shots


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) != 1:
        print("usage: assemble.py <film_dir> [--dry-run] [--animatic]", file=sys.stderr)
        return 2

    dry_run = "--dry-run" in flags
    film_dir = Path(args[0])
    film, shots = load(film_dir)

    if not dry_run and not shutil.which("ffmpeg"):
        print("error: ffmpeg not found on PATH. Install it, or re-run with --dry-run "
              "to inspect the commands.", file=sys.stderr)
        return 2

    p = plan(film_dir, film, shots)
    if p["missing"]:
        print(f"warn: {len(p['missing'])} shot(s) have no generated take and will be "
              f"omitted: {', '.join(str(m) for m in p['missing'])}", file=sys.stderr)
    if not p["clips"]:
        print("error: nothing to assemble — no generated takes found.", file=sys.stderr)
        return 1

    build = film_dir / "build"
    if not dry_run:
        p["work_dir"].mkdir(parents=True, exist_ok=True)
        build.mkdir(parents=True, exist_ok=True)

    rc = run(p["steps"], dry_run)
    if rc:
        return rc

    slug = film.get("slug", film_dir.name)
    list_file = build / "concat.txt"
    if not dry_run:
        list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in p["clips"]))

    cut = build / f"{slug}.mp4"
    rc = run([concat_command(list_file, cut)], dry_run)
    if rc:
        return rc

    bed = film_dir / "audio" / "bed.wav"
    if bed.exists():
        mixed = build / f"{slug}-mixed.mp4"
        rc = run([mix_command(cut, bed, mixed)], dry_run)
        if rc:
            return rc

    rc = run([contact_sheet_command(p["clips"], build / f"{slug}-contact-sheet.png")], dry_run)
    if rc:
        print("warn: contact sheet failed; the cut itself is fine.", file=sys.stderr)

    print(json.dumps({
        "cut": str(cut),
        "shots_cut": len(p["clips"]),
        "shots_missing": p["missing"],
        "dry_run": dry_run,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
