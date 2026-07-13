# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Render a scientific-study manuscript (paper.md) to PDF + EPUB.

PDF via pandoc's Typst engine (no LaTeX); EPUB via pandoc. Pure stdlib; the
external tools `pandoc` and `typst` must be on PATH.

The manuscript's first `# H1` becomes the document title (and is dropped from the
body so it is not typeset twice); author/date are lifted from `README.md` when
present. pandoc runs with the study folder as its working directory so the
paper's relative `assets/…` image paths and tables resolve.

Run: `uv run render-paper.py <study_dir>`  (study_dir contains paper.md)
Writes: `<study_dir>/build/<slug>.pdf` and `<study_dir>/build/<slug>.epub`.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

H1 = re.compile(r"^#\s+(.+?)\s*$")


def split_title(paper_md: str, fallback: str) -> tuple[str, str]:
    """Return (title, body) — title from the first H1, which is removed from body."""
    lines = paper_md.splitlines()
    for i, line in enumerate(lines):
        m = H1.match(line)
        if m:
            del lines[i]
            return m.group(1).strip(), "\n".join(lines).lstrip("\n")
    return fallback, paper_md


def readme_field(study_dir: Path, label: str) -> str:
    """Pull a `- **Label:** value` / `**Label:** value` line from README.md."""
    readme = study_dir / "README.md"
    if not readme.exists():
        return ""
    pat = re.compile(rf"\*\*{re.escape(label)}:\*\*\s*(.+?)\s*$", re.IGNORECASE)
    for line in readme.read_text(encoding="utf-8").splitlines():
        m = pat.search(line)
        if m:
            return m.group(1).strip()
    return ""


def derive_author(study_dir: Path) -> str:
    # An explicit "© <YEAR> <author(s)>." attribution line wins; else a README author field.
    readme = study_dir / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8").splitlines():
            m = re.search(r"©\s*\d{4}\s+(.+?)\.?\s*$", line)
            if m:
                return m.group(1).strip()
    return readme_field(study_dir, "Author")


def tools_available() -> dict:
    return {
        "pandoc": shutil.which("pandoc") is not None,
        "typst": shutil.which("typst") is not None,
    }


def render(study_dir: Path, out_dir: Path | None = None) -> dict:
    study_dir = study_dir.resolve()
    paper = study_dir / "paper.md"
    if not paper.exists():
        raise FileNotFoundError(f"no paper.md in {study_dir}")

    missing = [t for t, ok in tools_available().items() if not ok]
    if missing:
        raise RuntimeError(f"missing required tools on PATH: {', '.join(missing)}")

    slug = study_dir.name
    out_dir = out_dir or (study_dir / "build")
    out_dir.mkdir(parents=True, exist_ok=True)

    title, body = split_title(paper.read_text(encoding="utf-8"), fallback=slug)
    author = derive_author(study_dir)
    date = readme_field(study_dir, "Created")

    # Temp source with the H1 removed; rendered with study_dir as cwd so relative
    # `assets/…` paths resolve. Kept inside build/ and removed afterward.
    src = out_dir / f"{slug}.src.md"
    src.write_text(body, encoding="utf-8")
    pdf = out_dir / f"{slug}.pdf"
    epub = out_dir / f"{slug}.epub"

    meta = ["--metadata", f"title={title}"]
    if author:
        meta += ["--metadata", f"author={author}"]
    if date:
        meta += ["--metadata", f"date={date}"]

    common = [
        "pandoc", str(src),
        "--from", "gfm",            # authored for GitHub; treats lone `$` as literal currency
        "--toc", "--number-sections",
        "--resource-path", str(study_dir),
        *meta,
    ]
    try:
        subprocess.run(
            [*common, "-o", str(pdf), "--pdf-engine=typst"],
            cwd=study_dir, check=True, capture_output=True, text=True,
        )
        subprocess.run(
            [*common, "-o", str(epub)],
            cwd=study_dir, check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        # Surface the real pandoc/typst failure; never swallow it.
        raise RuntimeError(f"render failed:\n{e.stderr or e.stdout}") from e
    finally:
        src.unlink(missing_ok=True)

    return {"pdf": pdf, "epub": epub, "title": title}


def render_short(study_dir: Path, out_dir: Path | None = None) -> dict:
    """Render paper-short.md to a two-column short-form PDF (no EPUB, no TOC).

    Layout is passed via a metadata file because pandoc's Typst template rejects
    an inline `-V margin='{...}'` map.
    """
    study_dir = study_dir.resolve()
    paper = study_dir / "paper-short.md"
    if not paper.exists():
        raise FileNotFoundError(f"no paper-short.md in {study_dir}")

    missing = [t for t, ok in tools_available().items() if not ok]
    if missing:
        raise RuntimeError(f"missing required tools on PATH: {', '.join(missing)}")

    slug = study_dir.name
    out_dir = out_dir or (study_dir / "build")
    out_dir.mkdir(parents=True, exist_ok=True)

    title, body = split_title(paper.read_text(encoding="utf-8"), fallback=slug)
    author = derive_author(study_dir)
    date = readme_field(study_dir, "Created")

    src = out_dir / f"{slug}-short.src.md"
    src.write_text(body, encoding="utf-8")
    meta = out_dir / f"{slug}-short.meta.yaml"
    meta_lines = [
        "margin:",
        "  x: 1.6cm",
        "  y: 1.7cm",
        "fontsize: 10pt",
        "columns: 2",
    ]
    meta.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    # title/author/date are passed as pandoc --metadata flags (opaque strings,
    # not YAML) so a colon in the title (e.g. "…becomes useful: a case study")
    # can't break parsing of the metadata file.
    text_meta = ["--metadata", f"title={title}"]
    if author:
        text_meta += ["--metadata", f"author={author}"]
    if date:
        text_meta += ["--metadata", f"date={date}"]

    pdf = out_dir / f"{slug}-short.pdf"
    try:
        subprocess.run(
            [
                "pandoc", str(src), "--from", "gfm", "--pdf-engine=typst",
                "--resource-path", str(study_dir),
                "--metadata-file", str(meta),
                *text_meta,
                "-o", str(pdf),
            ],
            cwd=study_dir, check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"short-form render failed:\n{e.stderr or e.stdout}") from e
    finally:
        src.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)

    return {"pdf": pdf, "title": title}


def main(argv: list[str]) -> int:
    flags = {a for a in argv[1:] if a.startswith("--")}
    positional = [a for a in argv[1:] if not a.startswith("--")]
    if len(positional) != 1 or flags - {"--short"}:
        print("usage: render-paper.py <study_dir> [--short]", file=sys.stderr)
        return 2
    study_dir = Path(positional[0])
    if "--short" in flags:
        out = render_short(study_dir)
        print(f"wrote {out['pdf']}")
    else:
        out = render(study_dir)
        print(f"wrote {out['pdf']}")
        print(f"wrote {out['epub']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
