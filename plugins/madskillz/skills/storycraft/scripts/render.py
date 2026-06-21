# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Render a storycraft book (Markdown chapters) to EPUB + PDF.

EPUB via pandoc; PDF via pandoc's Typst engine (no LaTeX). Pure stdlib; the
external tools `pandoc` and `typst` must be on PATH. Run: `uv run render.py <book_dir>`.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path


def read_meta(book_dir: Path) -> dict:
    meta = {"title": book_dir.name, "author": ""}
    f = book_dir / "book.yaml"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            for key in ("title", "author"):
                if s.startswith(key + ":"):
                    meta[key] = s.split(":", 1)[1].strip().strip("\"'")
    return meta


def combine(book_dir: Path) -> str:
    meta = read_meta(book_dir)
    parts = [f"# {meta['title']}\n"]
    for p in sorted((book_dir / "chapters").glob("*.md")):
        parts.append(p.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts) + "\n"


def tools_available() -> dict:
    return {"pandoc": shutil.which("pandoc") is not None, "typst": shutil.which("typst") is not None}


def render(book_dir: Path, out_dir: Path | None = None) -> dict:
    tools = tools_available()
    missing = [t for t, ok in tools.items() if not ok]
    if missing:
        raise RuntimeError(f"missing required tools on PATH: {', '.join(missing)}")
    meta = read_meta(book_dir)
    slug = book_dir.name
    out_dir = out_dir or (book_dir / "build")
    out_dir.mkdir(parents=True, exist_ok=True)
    combined = out_dir / f"{slug}.md"
    combined.write_text(combine(book_dir), encoding="utf-8")
    epub = out_dir / f"{slug}.epub"
    pdf = out_dir / f"{slug}.pdf"
    common = ["--metadata", f"title={meta['title']}", "--metadata", f"author={meta['author']}"]
    subprocess.run(["pandoc", str(combined), "-o", str(epub), *common], check=True)
    subprocess.run(["pandoc", str(combined), "-o", str(pdf), "--pdf-engine=typst", *common], check=True)
    return {"epub": epub, "pdf": pdf}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: render.py <book_dir>", file=sys.stderr)
        return 2
    out = render(Path(argv[1]))
    print(f"wrote {out['epub']} and {out['pdf']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
