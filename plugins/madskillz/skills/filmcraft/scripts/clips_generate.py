# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Clips mode: generate per-scene video clips from approved briefs.

The lightweight lane of filmcraft — no shot list, no casting plates. Reads
`video/**/NN-brief.md` files with `status: approved` from a storycraft book,
submits each to Grok Imagine via `grok_client` (the only file that knows the
wire format), polls, downloads the mp4 next to the brief, and flips the
status. Idempotent: generated briefs are skipped; a saved request_id is
resumed by polling, never resubmitted. See references/clips-brief-format.md.
Run:
`uv run clips_generate.py <book_dir> [--chapter NN-slug] [--dry-run] [--max-clips N]`.
"""
from __future__ import annotations

import argparse
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
    """Return (approved briefs, [(malformed brief, reason), ...])."""
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
        if front.get("status") == "approved":
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
    if len(briefs) > max_clips:
        print(f"capping at --max-clips {max_clips}: {len(briefs)} approved, "
              f"{len(briefs) - max_clips} deferred to a later run")
        briefs = briefs[:max_clips]

    results: list[tuple[Path, str]] = []
    for brief in briefs:
        front, body = parse_brief(brief)
        prompt = assemble_prompt(style_block, parse_sections(body))
        dest = mp4_path(brief)

        if dest.exists() or front.get("status") == "generated":
            results.append((brief, "skipped (already generated)"))
            continue
        if dry_run:
            print(f"--- {brief.relative_to(book_dir)} (dry run) ---")
            print(prompt)
            results.append((brief, "dry-run"))
            continue

        try:
            request_id = front.get("request_id") or ""
            if not request_id:
                payload = grok_client.build_payload(
                    prompt,
                    model=client.model,
                    duration=int(front.get("duration", 4)),
                    aspect_ratio=str(front.get("aspect_ratio", "16:9")),
                    resolution=str(front.get("resolution", "480p")),
                )
                request_id = client.submit(payload)
                front["request_id"] = request_id
                write_brief(brief, front, body)  # saved before polling: crash-safe resume
            data = poll_until_settled(client, request_id, poll_timeout, sleep)
        except GenerationFailed as e:
            front["status"] = "failed"
            front["error"] = str(e)
            write_brief(brief, front, body)
            results.append((brief, f"failed: {e}"))
            continue

        status = str(data.get("status", "")).lower()
        if status in grok_client.TERMINAL_FAIL:
            front["status"] = "failed"
            front["error"] = str(data.get("error") or status)
            write_brief(brief, front, body)
            results.append((brief, f"failed: {front['error']}"))
            continue
        if status not in grok_client.TERMINAL_OK:
            results.append((brief, f"still pending (request_id {request_id}); re-run to resume"))
            continue

        urls = grok_client.extract_video_urls(data)
        if not urls:
            front["status"] = "failed"
            front["error"] = "done response had no video url"
            write_brief(brief, front, body)
            results.append((brief, f"failed: {front['error']}"))
            continue

        err = download(fetch, urls[0], dest, sleep)
        if err:
            front["status"] = "failed"
            front["error"] = err
            write_brief(brief, front, body)
            results.append((brief, f"failed: {err}"))
            continue

        front["status"] = "generated"
        front["error"] = ""
        write_brief(brief, front, body)
        results.append((brief, f"generated {dest.name}"))

    print("\nsummary:")
    for brief, outcome in results:
        print(f"  {brief.relative_to(book_dir)}: {outcome}")
    bad = [o for _, o in results if o.startswith("failed") or o.startswith("still pending")]
    return 1 if bad or malformed else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="clips_generate.py")
    ap.add_argument("book_dir", type=Path)
    ap.add_argument("--chapter")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-clips", type=int, default=5)
    args = ap.parse_args(argv[1:])

    client = GrokVideoClient()
    if args.dry_run:
        return process(args.book_dir, client, args.chapter, dry_run=True,
                       max_clips=args.max_clips)
    if not client.available:
        print("XAI_API_KEY is not set; export it before generating videos", file=sys.stderr)
        return 2
    return process(args.book_dir, client, args.chapter, max_clips=args.max_clips)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
