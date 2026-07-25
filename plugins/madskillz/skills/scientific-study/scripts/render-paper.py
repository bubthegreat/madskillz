# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Render a scientific-study manuscript to PDF + EPUB.

Assembles the four-document contract -- paper.md, then Methods, Extended Data
and Supplementary Information -- into one PDF and one EPUB.

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


# The four-document manuscript, in reading order. paper.md is required; the rest
# are appended as clearly labelled back sections when present.
BACK_SECTIONS = [
    ("methods.md", "Methods"),
    ("extended-data.md", "Extended Data"),
    ("supplementary.md", "Supplementary Information"),
]


def assemble(study_dir: Path, body: str) -> str:
    """paper.md body plus Methods / Extended Data / Supplementary, in order.

    Each back section is demoted to sit under one H1 so the table of contents
    shows four top-level parts rather than four merged section trees.
    """
    parts = [body.rstrip()]
    for name, heading in BACK_SECTIONS:
        f = study_dir / name
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8").strip()
        if not text:
            continue
        # Drop the file's own H1, if any; we supply the part heading.
        text = re.sub(r"\A# .*?(\n|$)", "", text, count=1)
        parts.append(f"# {heading}\n\n{text.strip()}")
    return "\n\n".join(parts) + "\n"


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
    src.write_text(assemble(study_dir, body), encoding="utf-8")
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

    included = [h for f, h in BACK_SECTIONS if (study_dir / f).exists()]
    return {"pdf": pdf, "epub": epub, "title": title, "parts": included}


def main(argv: list[str]) -> int:
    flags = {a for a in argv[1:] if a.startswith("--")}
    positional = [a for a in argv[1:] if not a.startswith("--")]
    if len(positional) != 1 or flags:
        print("usage: render-paper.py <study_dir>", file=sys.stderr)
        if "--short" in flags:
            print("note: --short was removed in v0.22.0 with the condensed short form; "
                  "a 4,300-word paper is its own digest.", file=sys.stderr)
        return 2
    out = render(Path(positional[0]))
    print(f"wrote {out['pdf']}")
    print(f"wrote {out['epub']}")
    if out["parts"]:
        print(f"  assembled back sections: {', '.join(out['parts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
