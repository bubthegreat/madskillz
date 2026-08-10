# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Split storycraft chapters into scenes and print a JSON inventory.

A scene is a block of text between lines that are exactly `---`. YAML
frontmatter at the top of a chapter and `---` lines inside fenced code
blocks are not scene breaks. Pure stdlib. Run:
`uv run scene_split.py <book_dir> [chapter-prefix]`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def strip_frontmatter(lines: list[str]) -> tuple[list[str], int]:
    """Return (body lines, 1-indexed line number where the body starts)."""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[i + 1 :], i + 2
    return lines, 1


def split_scenes(text: str) -> list[dict]:
    lines = text.splitlines()
    body, start = strip_frontmatter(lines)
    scenes: list[dict] = []
    current: list[str] = []
    current_start = start
    in_fence = False

    def flush(end_line: int) -> None:
        nonlocal current, current_start
        block = "\n".join(current).strip()
        if block:
            first = next(ln.strip() for ln in current if ln.strip())
            scenes.append(
                {
                    "scene": len(scenes) + 1,
                    "first_line": first,
                    "words": len(block.split()),
                    "start_line": current_start,
                    "end_line": end_line,
                    "text": block,
                }
            )
        current = []

    for offset, line in enumerate(body):
        lineno = start + offset
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if line.strip() == "---" and not in_fence:
            flush(lineno - 1)
            current_start = lineno + 1
        else:
            current.append(line)
    flush(start + len(body) - 1)
    return scenes


def inventory(book_dir: Path, chapter_prefix: str | None = None) -> dict:
    book_dir = Path(book_dir)
    chapters_dir = book_dir / "chapters"
    files = sorted(chapters_dir.glob("*.md")) if chapters_dir.is_dir() else []
    if chapter_prefix:
        files = [f for f in files if f.stem.startswith(chapter_prefix)]
    if not files:
        raise RuntimeError(f"no chapters found in {chapters_dir}")
    chapters = []
    for f in files:
        chapters.append(
            {
                "chapter": f.stem,
                "file": str(f.relative_to(book_dir)),
                "scenes": split_scenes(f.read_text(encoding="utf-8")),
            }
        )
    return {"book": book_dir.name, "chapters": chapters}


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: scene_split.py <book_dir> [chapter-prefix]", file=sys.stderr)
        return 2
    prefix = argv[2] if len(argv) == 3 else None
    print(json.dumps(inventory(Path(argv[1]), prefix), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
