# Render pipeline — PDF + EPUB

Step 5 of scientific-study builds distributable copies of the finished `paper.md` so
the study can be read off a screen (e-readers, tablets, print) instead of only as
Markdown in the repo. PDF is typeset with Typst (no LaTeX); EPUB is reflowable.

## Tools

Both `pandoc` and `typst` must be on PATH before running the renderer. If either is
missing, install it (below) — **never fake a build**. If neither can be installed in
the environment, publish the PR without the rendered artifacts and say so explicitly;
do not claim files that were not produced.

### pandoc

**Option A — system package (preferred if available):**
```bash
sudo apt install pandoc          # Debian/Ubuntu
brew install pandoc              # macOS
```

**Option B — static release binary (any Linux, no root):**
```bash
# Check https://github.com/jgm/pandoc/releases for the latest version
PANDOC_VERSION=3.6.4
curl -L "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-amd64.tar.gz" \
  | tar -xz --strip-components=2 -C ~/.local/bin "pandoc-${PANDOC_VERSION}/bin/pandoc"
```

Verify: `pandoc --version`

### typst

`uv tool install typst` does **not** provide a CLI binary — use the official installer
or a release binary instead.

**Option A — official installer (macOS/Linux):**
```bash
curl -fsSL https://typst.app/install.sh | sh        # lands in ~/.local/bin
```

**Option B — release binary (any Linux, no root):**
```bash
# Check https://github.com/typst/typst/releases for the latest version
TYPST_VERSION=0.13.1
curl -L "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
  | tar -xJ --strip-components=1 -C ~/.local/bin "typst-x86_64-unknown-linux-musl/typst"
```

Verify: `typst --version`. Make sure `~/.local/bin` is on `PATH`.

## Running the renderer

```bash
uv run plugins/madskillz/skills/scientific-study/scripts/render-paper.py <study_dir>
```

`<study_dir>` is the study folder containing `paper.md`
(e.g. `astrophysics/colorblind-light-shell`). The script:

1. Takes the manuscript's first `# H1` as the document **title** and drops that line
   from the body so it is not typeset twice; lifts **author** (from a `© <year> …`
   or `**Author:**` line in `README.md`) and **date** (`**Created:**`) when present.
2. Runs `pandoc` with the **study folder as the working directory**, so the paper's
   relative `assets/…` image paths and pipe tables resolve. Reader is `gfm` (the
   papers are authored for GitHub; a lone `$` stays literal currency, not math).
3. Writes **two builds**, four files, with numbered sections:

| File | Format | Contents | Table of contents | Purpose |
|---|---|---|---|---|
| `build/<slug>-paper-only.pdf` | PDF via Typst | `paper.md` alone | **No** | Reading; fixed-layout / print |
| `build/<slug>-paper-only.epub` | EPUB 3 (reflowable) | `paper.md` alone | **No** | Reading on an e-reader |
| `build/<slug>.pdf` | PDF via Typst | full assembly | Yes | Checking the work |
| `build/<slug>.epub` | EPUB 3 (reflowable) | full assembly | Yes | Checking the work |

The paper-only build is the copy a person reads. The paper is short, so a contents page in front of
it is noise. The full assembly is the copy a person opens to verify a number, so it keeps its
contents page and its back sections. Commit all four.

The script exits non-zero if either tool is missing or either render fails, passing
through the underlying pandoc/typst error so the failure is visible.

## Committing the build artifacts

Commit the rendered files so they ship in the PR (and can sync to a device via the
repo). Stage only this study's folder — never `git add -A` (the worktree also holds
other studies):

```bash
git -C "$WT" add "<topic>/<research-short-name>/build"
git -C "$WT" commit -m "render: build PDF + EPUB for <research-short-name>"
```

Commit **all four files** — both builds ship in the PR.

End the commit message with the `Co-Authored-By:` trailer per `git-workflow.md`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `missing required tools on PATH: pandoc` | pandoc not installed / not on PATH | Install pandoc (above); check `echo $PATH` |
| `missing required tools on PATH: typst` | `uv tool install typst` used (no CLI) | Use the official installer or release binary |
| `pandoc: command not found` inside `uv run` | PATH not inherited | Set `PATH` before running `uv run` |
| Figures missing from the PDF/EPUB | image paths not resolving | Confirm `assets/…` paths are relative and the files exist in the study folder |
| PDF render error from typst | Typst version mismatch / unsupported construct | Update typst; check the passed-through error for the offending line |

## The four-document assembly

The **full** build assembles the whole manuscript, in reading order, into one PDF and one EPUB
(the paper-only build skips all of this and renders `paper.md` by itself):

| Order | File | Rendered as |
|---|---|---|
| 1 | `paper.md` | the paper (its H1 becomes the document title) |
| 2 | `methods.md` | `# Methods` |
| 3 | `extended-data.md` | `# Extended Data` |
| 4 | `supplementary.md` | `# Supplementary Information` |

Only `paper.md` is required; the others are appended when present and non-empty. Each back document's
own H1 is dropped and replaced with the part heading, so the table of contents shows four top-level
parts rather than four merged section trees. The command prints which parts it assembled.

Run `scripts/check-budgets.py` first — it must exit 0. Rendering an over-budget manuscript produces a
PDF that looks finished and is not.

> `--short` was removed in v0.22.0 along with the condensed short form. A 4,300-word paper opening
> with a 200-word Summary paragraph is its own digest. Passing `--short` now prints a note and exits
> non-zero rather than silently doing nothing.

