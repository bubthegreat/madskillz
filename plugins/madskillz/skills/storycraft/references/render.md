# Render pipeline — EPUB + PDF

Phase 3 of storycraft assembles the finished chapters into distributable files and commits them.

## Tool install

Both `pandoc` and `typst` must be on PATH before running the renderer.

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

`uv tool install typst` does **not** provide a CLI binary — use the official release binary or the
official installer instead.

**Option A — official installer (macOS/Linux):**
```bash
curl -fsSL https://typst.app/install.sh | sh
```
This places `typst` in `~/.local/bin` (or the configured install prefix).

**Option B — release binary (any Linux, no root):**
```bash
# Check https://github.com/typst/typst/releases for the latest version
TYPST_VERSION=0.13.1
curl -L "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
  | tar -xJ --strip-components=1 -C ~/.local/bin "typst-x86_64-unknown-linux-musl/typst"
```

**Option C — cargo:**
```bash
cargo install typst-cli
```

Verify: `typst --version`

---

Make sure `~/.local/bin` (or wherever the binaries landed) is in your `PATH`:
```bash
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc
```

## Running the renderer

```bash
uv run plugins/madskillz/skills/storycraft/scripts/render.py <book_dir>
```

`<book_dir>` is the absolute or relative path to the book folder inside the stories repo
(e.g. `~/stories/goblin-scouts`).

The script reads `book.yaml` for `title` and `author`, stitches `chapters/*.md` in filename order,
and writes:

| File | Format | Purpose |
|---|---|---|
| `<book_dir>/build/<slug>.epub` | EPUB 3 (reflowable) | Primary e-reader target |
| `<book_dir>/build/<slug>.pdf` | PDF via Typst | Print / fallback |

The script exits non-zero if either tool is missing or either render fails. The error output from
pandoc/typst is passed through so the underlying failure is visible.

## What the renderer does

1. Reads `book.yaml` → `title`, `author`.
2. Collects `chapters/NN-*.md` in sorted order.
3. Stitches them into a single combined Markdown (in memory → `build/<slug>.md` temp file).
4. Runs `pandoc <slug>.md -o <slug>.epub` with title/author metadata.
5. Runs `pandoc <slug>.md -o <slug>.pdf --pdf-engine=typst` (no LaTeX required).
6. Removes the temp `.md` file.

EPUB is the reflowable e-reader target (Kindle, Kobo, Apple Books). PDF is Typst-typeset and
suitable for printing or PDF readers; it is not fixed-layout.

## Committing the build artifacts

Build artifacts are committed so they sync to the e-reader via the repo. After a successful render:

```bash
git add <book_dir>/build/<slug>.epub <book_dir>/build/<slug>.pdf
git commit -m "book: <slug> build"
```

Follow the commit-message format from `repo-layout.md`. Never push — the user pushes manually.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `missing required tools on PATH: pandoc` | pandoc not installed or not on PATH | Install pandoc (see above); check `echo $PATH` |
| `missing required tools on PATH: typst` | `uv tool install typst` was used (no CLI) | Use the official installer or release binary (see above) |
| `pandoc: command not found` inside `uv run` | PATH not inherited | Set `PATH` in the shell before running `uv run` |
| Empty EPUB / PDF | No `chapters/*.md` files | Draft at least one chapter first (Phase 2) |
| PDF render error from typst | Typst version mismatch | Update typst to the latest release |
