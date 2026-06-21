# Rendering the paper to PDF + EPUB

Before publishing (Step 5) — and again after any human-review change (Step 6) — build a
human-readable **PDF and EPUB** from `paper.md` and **commit them into the study folder** so they
ride along in the PR. A human can then read the paper offline or on an e-reader without rebuilding
it.

## Output location

```
<topic>/<research-short-name>/build/<research-short-name>.pdf
<topic>/<research-short-name>/build/<research-short-name>.epub
```

The `build/` artifacts are **committed** — they are the deliverable a human reads, so they go in the
PR. Do **not** add `build/` to `.gitignore`.

## Commands

Run from the **study folder** (so relative `assets/…` image paths resolve), as its own commit:

```bash
cd <topic>/<research-short-name>
mkdir -p build
SHORT="<research-short-name>"
TITLE=$(grep -m1 '^# ' paper.md | sed 's/^# //')        # the paper's H1
pandoc paper.md -o "build/$SHORT.pdf"  --pdf-engine=typst --toc --metadata title="$TITLE"
pandoc paper.md -o "build/$SHORT.epub"                   --toc --metadata title="$TITLE"
git add build/
git commit -m "render: build PDF + EPUB for $SHORT"
```

- **PDF engine: Typst** (`--pdf-engine=typst`) — fast, no TeX install required, good Unicode/Greek/
  arrow coverage. Needs `pandoc` (≥3) and `typst` on `PATH`.
- `--toc` adds a table of contents (helpful on an e-reader). Running from the study folder (or
  passing `--resource-path=.`) lets images referenced as `assets/…` be found.
- EPUB is the better e-reader format (reflowable); PDF is fixed-layout. Produce **both**.

## Re-render on every change

After any human-review edit (Step 6) or post-gate revision, **re-run both commands and re-commit** so
the PDF/EPUB never drift from `paper.md`. The Markdown is the source of truth; the build artifacts are
generated.

## Integrity / tool-availability (same stance as the rest of the skill)

- If `pandoc` or the PDF engine is **not installed**, do **not** fabricate or hand-place a file.
  Render whatever you can (e.g., EPUB only), and **state in the PR** which artifact was skipped and
  why. A missing render is disclosed, never faked.
- If the paper uses heavy LaTeX math and Typst chokes on a construct, fall back to
  `--pdf-engine=tectonic` or `--pdf-engine=xelatex` if available; otherwise render EPUB only and note
  the PDF was skipped.
- Never edit `paper.md` just to make it render — fix the render invocation instead.
