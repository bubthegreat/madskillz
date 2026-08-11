# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Clips mode: generate a chained per-scene video from approved briefs.

The lightweight lane of filmcraft — no shot list, no casting plates. Reads
`video/**/NN-brief.md` files with `status: approved` from a storycraft book
and builds the video intentionally: the first scene is a fresh generation,
and every following scene EXTENDS the previous scene's clip from its final
frame (`/v1/videos/extensions`), so motion and look flow scene to scene.
Segments are downloaded next to their briefs; concatenating them yields one
continuous film. `--independent` disables chaining (isolated per-scene clips).

Idempotent: generated briefs are skipped; a saved request_id is resumed by
polling, never resubmitted. Chain URLs are temporary, so a scene generated in
an earlier run cannot be extended — the chain restarts fresh at the next
scene and says so. See references/clips-brief-format.md.
Run:
`uv run clips_generate.py <book_dir> [--chapter NN-slug] [--dry-run]
                          [--max-clips N] [--independent]`.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grok_client  # noqa: E402
from grok_client import GenerationFailed, GrokVideoClient  # noqa: E402

SECTION_ORDER = [
    "Scene",
    "Motion & camera",
    "Mood / palette",
    "Characters present",
    "Audio",
]
DOWNLOAD_RETRIES = 3


def parse_brief(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        raise RuntimeError(f"{path}: brief has no closed frontmatter block")
    return yaml.safe_load(parts[1]) or {}, parts[2].lstrip("\n")


def write_brief(path: Path, front: dict, body: str) -> None:
    front_text = yaml.safe_dump(front, sort_keys=False, allow_unicode=True).strip()
    path.write_text(f"---\n{front_text}\n---\n{body}", encoding="utf-8")


def parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        else:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return sections


def assemble_prompt(style_block: str, sections: dict[str, str]) -> str:
    parts = [style_block.strip()]
    for name in SECTION_ORDER:
        if sections.get(name):
            parts.append(sections[name])
    nots = sections.get("What NOT to show", "")
    if nots:
        parts.append(nots if nots.lower().startswith("do not show") else f"Do not show: {nots}")
    return "\n\n".join(p for p in parts if p)


def select_briefs(
    book_dir: Path, chapter: str | None = None
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Return (approved + generated briefs in story order, malformed).

    Generated briefs ride along as chain context: the loop skips them but can
    re-poll their request id to keep extending from their final frame.
    """
    video_dir = book_dir / "video"
    briefs: list[Path] = []
    malformed: list[tuple[Path, str]] = []
    for path in sorted(video_dir.glob("*/[0-9][0-9]-brief.md")):
        if chapter and path.parent.name != chapter:
            continue
        try:
            front, _ = parse_brief(path)
        except (RuntimeError, yaml.YAMLError) as e:
            malformed.append((path, str(e)))
            continue
        if front.get("status") in ("approved", "generated"):
            briefs.append(path)
    return briefs, malformed


def mp4_path(brief: Path) -> Path:
    return brief.with_name(brief.name.replace("-brief.md", ".mp4"))


def poll_until_settled(
    client: GrokVideoClient, request_id: str, timeout: float, sleep
) -> dict:
    """Poll until a terminal status or timeout; returns the last response."""
    deadline = time.monotonic() + timeout
    delay = 5.0
    while True:
        data = client.poll_once(request_id)
        status = str(data.get("status", "")).lower()
        if status in grok_client.TERMINAL_OK or status in grok_client.TERMINAL_FAIL:
            return data
        if time.monotonic() >= deadline:
            return data
        sleep(delay)
        delay = min(delay * 1.5, 30.0)


def download(fetch, url: str, dest: Path, sleep) -> str | None:
    """Download url to dest. Return an error string, or None on success."""
    last = ""
    for _ in range(DOWNLOAD_RETRIES):
        try:
            content = fetch(url)
            if content:
                dest.write_bytes(content)
                return None
            last = "download returned empty body"
        except OSError as e:
            last = f"download error: {e}"
        sleep(2)
    return last


def process(
    book_dir: Path,
    client: GrokVideoClient,
    chapter: str | None = None,
    dry_run: bool = False,
    max_clips: int = 5,
    poll_timeout: float = 600.0,
    sleep=time.sleep,
    fetch=grok_client.fetch_binary,
    independent: bool = False,
) -> int:
    book_dir = Path(book_dir)
    style_path = book_dir / "video" / "style-block.md"
    style_block = style_path.read_text(encoding="utf-8") if style_path.exists() else ""
    briefs, malformed = select_briefs(book_dir, chapter)
    for path, reason in malformed:
        print(f"malformed brief skipped: {path.relative_to(book_dir)}: {reason}",
              file=sys.stderr)
    if not briefs:
        print("no approved briefs to generate")
        return 1 if malformed else 0

    results: list[tuple[Path, str]] = []
    chain_url: str | None = None  # previous segment's delivered URL, this run only
    chain_broken = False
    submitted = 0
    final_dest: Path | None = None  # last chained segment = the whole film so far
    for brief in briefs:
        front, body = parse_brief(brief)
        prompt = assemble_prompt(style_block, parse_sections(body))
        dest = mp4_path(brief)

        if dest.exists() or front.get("status") == "generated":
            # Try to recover a still-valid delivered URL by re-polling the saved
            # request id — one free GET. If it works, the chain continues from
            # this scene's real final frame instead of restarting fresh.
            chain_url = None
            note = "chain restarts after it"
            if not independent and not dry_run and front.get("request_id"):
                try:
                    old = client.poll_once(front["request_id"])
                    urls = grok_client.extract_video_urls(old)
                    if str(old.get("status", "")).lower() in grok_client.TERMINAL_OK and urls:
                        chain_url = urls[0]
                        note = "chain continues from it"
                except GenerationFailed:
                    pass
            results.append((brief, f"skipped (already generated; {note})"))
            continue
        if chain_broken:
            results.append((brief, "not attempted (chain broken upstream)"))
            continue
        if submitted >= max_clips:
            # Deferred, chain not broken: the next run re-polls the last
            # generated scene and keeps extending from its final frame.
            results.append((brief, f"deferred (--max-clips {max_clips})"))
            continue
        mode = "extend" if (chain_url and not independent) else "fresh"
        if dry_run:
            print(f"--- {brief.relative_to(book_dir)} (dry run, would be {mode}) ---")
            print(prompt)
            results.append((brief, f"dry-run ({mode})"))
            chain_url = "dry"  # later briefs preview as extend
            continue

        try:
            request_id = front.get("request_id") or ""
            if not request_id:
                if mode == "extend":
                    payload = grok_client.build_extend_payload(
                        prompt, chain_url,
                        duration=int(front.get("duration", 4)),
                    )
                    request_id = client.submit_extend(payload)
                else:
                    payload = grok_client.build_payload(
                        prompt,
                        model=client.model,
                        duration=int(front.get("duration", 4)),
                        aspect_ratio=str(front.get("aspect_ratio", "16:9")),
                        resolution=str(front.get("resolution", "480p")),
                    )
                    request_id = client.submit(payload)
                submitted += 1
                front["request_id"] = request_id
                front["mode"] = mode
                write_brief(brief, front, body)  # saved before polling: crash-safe resume
            data = poll_until_settled(client, request_id, poll_timeout, sleep)
        except GenerationFailed as e:
            front["status"] = "failed"
            front["error"] = str(e)
            write_brief(brief, front, body)
            results.append((brief, f"failed: {e}"))
            chain_broken = not independent
            continue

        status = str(data.get("status", "")).lower()
        if status in grok_client.TERMINAL_FAIL:
            front["status"] = "failed"
            front["error"] = str(data.get("error") or status)
            write_brief(brief, front, body)
            results.append((brief, f"failed: {front['error']}"))
            chain_broken = not independent
            continue
        if status not in grok_client.TERMINAL_OK:
            results.append((brief, f"still pending (request_id {request_id}); re-run to resume"))
            chain_broken = not independent
            continue

        urls = grok_client.extract_video_urls(data)
        if not urls:
            front["status"] = "failed"
            front["error"] = "done response had no video url"
            write_brief(brief, front, body)
            results.append((brief, f"failed: {front['error']}"))
            chain_broken = not independent
            continue

        err = download(fetch, urls[0], dest, sleep)
        if err:
            front["status"] = "failed"
            front["error"] = err
            write_brief(brief, front, body)
            results.append((brief, f"failed: {err}"))
            chain_broken = not independent
            continue

        front["status"] = "generated"
        front["error"] = ""
        write_brief(brief, front, body)
        results.append((brief, f"generated {dest.name} ({front.get('mode', mode)})"))
        chain_url = urls[0]
        final_dest = dest

    print("\nsummary:")
    for brief, outcome in results:
        print(f"  {brief.relative_to(book_dir)}: {outcome}")
    bad = [o for _, o in results
           if o.startswith(("failed", "still pending", "not attempted"))]

    # Extension output is cumulative (live-verified): each segment contains all
    # footage so far, so the last chained segment is the film to date.
    if final_dest and not independent:
        film = book_dir / "video" / f"{book_dir.name}.mp4"
        shutil.copyfile(final_dest, film)
        state = "complete" if not (bad or malformed) else "partial — chain incomplete"
        print(f"film ({state}): {film.relative_to(book_dir)}")

    return 1 if bad or malformed else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="clips_generate.py")
    ap.add_argument("book_dir", type=Path)
    ap.add_argument("--chapter")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-clips", type=int, default=5)
    ap.add_argument("--independent", action="store_true",
                    help="isolated per-scene clips instead of the default extend chain")
    args = ap.parse_args(argv[1:])

    client = GrokVideoClient()
    if args.dry_run:
        return process(args.book_dir, client, args.chapter, dry_run=True,
                       max_clips=args.max_clips, independent=args.independent)
    if not client.available:
        print("Neither XAI_API_KEY nor GROK_API_KEY is set; export one before "
              "generating videos", file=sys.stderr)
        return 2
    return process(args.book_dir, client, args.chapter, max_clips=args.max_clips,
                   independent=args.independent)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
