# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx", "pyyaml"]
# ///
"""Generate per-scene video clips from approved briefs via the xAI API.

Reads `video/**/NN-brief.md` files with `status: approved`, submits each to
Grok Imagine, polls until done, downloads the mp4 next to the brief, and flips
the status. Idempotent: generated briefs are skipped; a saved request_id is
resumed by polling, never resubmitted. See references/brief-format.md and
references/grok-api.md. Run:
`uv run generate.py <book_dir> [--chapter NN-slug] [--dry-run] [--max-clips N]`.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx
import yaml

MODEL = "grok-imagine-video-1.5"
DEFAULT_BASE_URL = "https://api.x.ai"
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


def submit(client: httpx.Client, prompt: str, front: dict) -> str:
    resp = client.post(
        "/v1/videos/generations",
        json={
            "model": MODEL,
            "prompt": prompt,
            "duration": int(front.get("duration", 4)),
            "aspect_ratio": str(front.get("aspect_ratio", "16:9")),
            "resolution": str(front.get("resolution", "480p")),
        },
    )
    resp.raise_for_status()
    return resp.json()["request_id"]


def poll(client: httpx.Client, request_id: str, timeout: float, sleep) -> dict:
    deadline = time.monotonic() + timeout
    delay = 5.0
    while True:
        resp = client.get(f"/v1/videos/{request_id}")
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "pending":
            return data
        if time.monotonic() >= deadline:
            return data
        sleep(delay)
        delay = min(delay * 1.5, 30.0)


def download(client: httpx.Client, url: str, dest: Path, sleep) -> str | None:
    """Download url to dest. Return an error string, or None on success."""
    last = ""
    for _ in range(DOWNLOAD_RETRIES):
        try:
            resp = client.get(url)
            if resp.status_code == 200 and resp.content:
                dest.write_bytes(resp.content)
                return None
            last = f"download HTTP {resp.status_code}"
        except httpx.HTTPError as e:
            last = f"download error: {e}"
        except OSError as e:
            return f"could not write {dest}: {e}"
        sleep(2)
    return last


def process(
    book_dir: Path,
    client: httpx.Client,
    chapter: str | None = None,
    dry_run: bool = False,
    max_clips: int = 5,
    poll_timeout: float = 600.0,
    sleep=time.sleep,
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
                request_id = submit(client, prompt, front)
                front["request_id"] = request_id
                write_brief(brief, front, body)  # saved before polling: crash-safe resume
            data = poll(client, request_id, poll_timeout, sleep)
        except httpx.HTTPStatusError as e:
            front["status"] = "failed"
            front["error"] = f"API HTTP {e.response.status_code}: {e.response.text[:200]}"
            write_brief(brief, front, body)
            results.append((brief, f"failed: {front['error']}"))
            continue
        except (httpx.HTTPError, KeyError, ValueError) as e:
            front["status"] = "failed"
            front["error"] = f"API error: {e}"
            write_brief(brief, front, body)
            results.append((brief, f"failed: {front['error']}"))
            continue
        status = data.get("status")
        if status == "pending":
            results.append((brief, f"still pending (request_id {request_id}); re-run to resume"))
            continue
        if status != "done":
            front["status"] = "failed"
            front["error"] = str(data.get("error") or status)
            write_brief(brief, front, body)
            results.append((brief, f"failed: {front['error']}"))
            continue

        err = download(client, data["video"]["url"], dest, sleep)
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
    ap = argparse.ArgumentParser(prog="generate.py")
    ap.add_argument("book_dir", type=Path)
    ap.add_argument("--chapter")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-clips", type=int, default=5)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = ap.parse_args(argv[1:])

    if args.dry_run:
        with httpx.Client(base_url=args.base_url) as client:
            return process(args.book_dir, client, args.chapter, dry_run=True,
                           max_clips=args.max_clips)

    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        print("XAI_API_KEY is not set; export it before generating videos", file=sys.stderr)
        return 2
    with httpx.Client(
        base_url=args.base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60.0,
    ) as client:
        return process(args.book_dir, client, args.chapter, max_clips=args.max_clips)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
