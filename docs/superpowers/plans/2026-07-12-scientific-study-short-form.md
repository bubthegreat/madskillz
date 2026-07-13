# Scientific-study Short-Form Summary — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an always-on step to the `scientific-study` skill that produces a re-gated, two-column specialist short-form PDF alongside every study's full paper.

**Architecture:** A new `render_short()` path in the existing `render-paper.py` renders `paper-short.md` two-column via a pandoc→Typst metadata file. The SKILL gains Step 5b (author `paper-short.md` → re-gate with claims-ledger + adversarial → render short) documented against a new `references/short-form.md` condensation contract. No change to the existing full-paper render.

**Tech Stack:** Python 3.10+ stdlib (PEP 723 script), pandoc + Typst, pytest for the script test, Markdown skill/reference files, JSON evals.

## Global Constraints

- Skill path root: `plugins/madskillz/skills/scientific-study/`.
- The short form is **additive** — it never replaces the full `paper.md`, PDF, or EPUB.
- The short form introduces **no number** not already in `paper.md` / the study's `data/` files.
- Best-effort render, fail-closed honesty: never fake a build; if `pandoc`/`typst` are missing, skip the short PDF and say so.
- Short-render params (verbatim): `columns: 2`, `fontsize: 10pt`, `margin: {x: 1.6cm, y: 1.7cm}`, **no** `--toc`, **no** `--number-sections`; output `build/<slug>-short.pdf`; **no EPUB** for the short form.
- pandoc's Typst template rejects inline `-V margin='{...}'` — layout MUST be passed via `--metadata-file`.
- Re-gate rigor: **claims-ledger + adversarial** reviewers on every short form, framed as a compression check, plus an automatic numbers-trace check.
- Bump `plugins/madskillz/.claude-plugin/plugin.json` version at the end.

---

### Task 1: Add `render_short()` to `render-paper.py`

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/scripts/render-paper.py`
- Create: `plugins/madskillz/skills/scientific-study/scripts/tests/test_render_short.py`

**Interfaces:**
- Consumes: existing helpers `split_title()`, `derive_author()`, `readme_field()`, `tools_available()` in `render-paper.py`.
- Produces: `render_short(study_dir: Path, out_dir: Path | None = None) -> dict` returning `{"pdf": Path, "title": str}`; CLI `render-paper.py <study_dir> --short`.

- [ ] **Step 1: Write the failing test**

Create `plugins/madskillz/skills/scientific-study/scripts/tests/test_render_short.py`:

```python
import importlib.util
import shutil
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "render-paper.py"


def load():
    spec = importlib.util.spec_from_file_location("render_paper", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HAVE_TOOLS = bool(shutil.which("pandoc") and shutil.which("typst"))


def test_render_short_missing_file(tmp_path):
    mod = load()
    study = tmp_path / "empty"
    study.mkdir()
    with pytest.raises(FileNotFoundError):
        mod.render_short(study)


@pytest.mark.skipif(not HAVE_TOOLS, reason="pandoc/typst not on PATH")
def test_render_short_produces_two_column_pdf(tmp_path):
    mod = load()
    study = tmp_path / "my-study"
    study.mkdir()
    (study / "paper-short.md").write_text(
        "# My Study (short form)\n\n**A. Author** · 2026-01-01\n\n"
        "## 1. Introduction\n\nA condensed paragraph citing 0.910.\n",
        encoding="utf-8",
    )
    (study / "README.md").write_text(
        "- **Created:** 2026-01-01\n© 2026 A. Author.\n", encoding="utf-8"
    )
    out = mod.render_short(study)
    assert out["pdf"].name == "my-study-short.pdf"
    assert out["pdf"].exists() and out["pdf"].stat().st_size > 0
    # the temp source + metadata file are cleaned up
    assert not (study / "build" / "my-study-short.src.md").exists()
    assert not (study / "build" / "my-study-short.meta.yaml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/madskillz/skills/scientific-study/scripts && uv run --with pytest pytest tests/test_render_short.py -v`
Expected: FAIL — `AttributeError: module 'render_paper' has no attribute 'render_short'`.

- [ ] **Step 3: Add `render_short()` and extend the CLI**

In `render-paper.py`, add this function immediately after `render()` (before `def main`):

```python
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
        f"title: {title}",
    ]
    if author:
        meta_lines.append(f"author: {author}")
    if date:
        meta_lines.append(f"date: {date}")
    meta.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    pdf = out_dir / f"{slug}-short.pdf"
    try:
        subprocess.run(
            [
                "pandoc", str(src), "--from", "gfm", "--pdf-engine=typst",
                "--resource-path", str(study_dir),
                "--metadata-file", str(meta),
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
```

Replace the existing `main()` with a version that accepts `--short`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/madskillz/skills/scientific-study/scripts && uv run --with pytest pytest tests/test_render_short.py -v`
Expected: PASS (both tests; `test_render_short_produces_two_column_pdf` runs because pandoc+typst are on PATH here).

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/scripts/render-paper.py \
        plugins/madskillz/skills/scientific-study/scripts/tests/test_render_short.py
git commit -m "feat(scientific-study): render_short() two-column short-form PDF path"
```

---

### Task 2: Document the short render in `references/render.md`

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/references/render.md`

**Interfaces:**
- Consumes: `render_short()` / `render-paper.py <dir> --short` from Task 1.
- Produces: documented command the SKILL Step 5b references.

- [ ] **Step 1: Append the short-form render section**

Add to the end of `references/render.md`:

```markdown
## Short-form render (two-column condensation)

The condensed `paper-short.md` (see `references/short-form.md`) renders to a dense two-column PDF,
**no EPUB, no table of contents**:

```bash
uv run <skill>/scripts/render-paper.py <topic>/<research-short-name> --short
```

It writes `build/<research-short-name>-short.pdf`. Layout is fixed in the script — `columns: 2`,
`fontsize: 10pt`, `margin {x: 1.6cm, y: 1.7cm}` — passed via a pandoc `--metadata-file` (an inline
`-V margin='{...}'` map is rejected by pandoc's Typst template). The full-paper render is unchanged;
`--short` only adds the condensed PDF. Same fail-closed rule: if `pandoc`/`typst` are missing, skip
the short PDF and say so — never fake a build.
```

- [ ] **Step 2: Verify the file reads correctly**

Run: `grep -n "Short-form render" plugins/madskillz/skills/scientific-study/references/render.md`
Expected: one match.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/references/render.md
git commit -m "docs(scientific-study): document the --short two-column render"
```

---

### Task 3: Create the condensation contract `references/short-form.md`

**Files:**
- Create: `plugins/madskillz/skills/scientific-study/references/short-form.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the reference SKILL Step 5b loads for the condensation + re-gate procedure.

- [ ] **Step 1: Write the reference file**

Create `plugins/madskillz/skills/scientific-study/references/short-form.md`:

```markdown
# Short-form condensation contract

After the full paper clears the quality gate (Step 3) and renders (Step 5), produce a condensed
`paper-short.md` **in addition to** the full paper — never replacing it. Audience: **specialist**
(a domain reader who knows the field's terms).

## What the short form is

A compression of the gated `paper.md`, not new work. It performs **no new analysis** and uses
**no number** that is not already in `paper.md` / the study's `data/` files. If a needed number is
not there, leave `[[NEEDS-DATA: …]]` rather than invent it.

## Keep / drop

**Keep:** the title (suffix "(short form)") + a one-line byline; a **1-paragraph abstract**; a
compressed Introduction (the question + the paper's arc in 2–4 sentences); a compressed Methods
(strip inline plain-language asides such as "*stratified* means…"); Results that **lean on the
existing figures** and the 1–2 most load-bearing tables instead of restating every number in prose;
a tightened Discussion; **Limitations compressed to one dense paragraph**; the References list.

**Drop:** the Glossary, the Acronyms index, Background / further reading, and inline term
definitions (the specialist reader does not need them).

**Reuse figures.** Reference the same `assets/*.png` the full paper already built — do not
regenerate them.

## Preserve every caveat

Compression is where caveats get dropped and overclaims sneak back. Every hedge the full paper
earned — within-noise / directional-only results, confounds, single-source limits, disclosed
residuals — MUST survive in compressed form. The short form must be **neither more nor less honest**
than the paper it summarizes.

## Re-gate (required)

Invoke `scientific-peer-review`'s **claims-ledger** and **adversarial** reviewers on
`paper-short.md` (with the `data/` files), framed as a **compression check against the full paper**:
did shortening drop a caveat, reintroduce an overclaim, or mislabel a metric? Also confirm every
number in the short form appears in `paper.md`/`data/` (numbers-trace check). Apply blocker/major
fixes; disclose any residual in the PR. If a finding traces to the full paper too, fix it in **both**.

## Render

Render two-column per `references/render.md`:

    uv run <skill>/scripts/render-paper.py <topic>/<research-short-name> --short

Target **≤5 pages excluding references** (typically ~2–3). Commit `paper-short.md` and
`build/<slug>-short.pdf`; note the short form in the PR description and README. Best-effort: if
`pandoc`/`typst` are unavailable, keep `paper-short.md` and skip the PDF with a recorded note —
never fake a build.
```

- [ ] **Step 2: Verify**

Run: `grep -n "Re-gate (required)" plugins/madskillz/skills/scientific-study/references/short-form.md`
Expected: one match.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/references/short-form.md
git commit -m "docs(scientific-study): add short-form condensation contract"
```

---

### Task 4: Add Step 5b to `SKILL.md`

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/SKILL.md`

**Interfaces:**
- Consumes: `references/short-form.md` (Task 3), `references/render.md` (Task 2).
- Produces: the always-on Step 5b in the study flow + edge cases.

- [ ] **Step 1: Insert Step 5b after the render step (Step 5)**

In `SKILL.md`, immediately after the Step 5 block (the render step, which ends with "…Never fake a build.") and before `## Step 6 — Publish as a PR`, insert:

```markdown
## Step 5b — Condensed short form (always, in addition to the full paper)

Produce a specialist short-form summary **alongside** the full paper — never replacing it — per
`references/short-form.md`:

1. **Author `paper-short.md`** — a specialist condensation of the gated `paper.md`: a 1-paragraph
   abstract, compressed Introduction/Methods/Discussion, Results that lean on the existing figures
   and the 1–2 key tables, Limitations in one dense paragraph, References kept; Glossary, Acronyms,
   Background, and inline definitions dropped. Introduce **no number** not already in `paper.md` /
   `data/`; preserve every caveat in compressed form.
2. **Re-gate for compression drift** — run `scientific-peer-review`'s **claims-ledger** and
   **adversarial** reviewers on `paper-short.md` as a compression check (dropped caveat,
   reintroduced overclaim, mislabeled metric), plus a numbers-trace check. Fix blocker/major
   findings; a finding that traces to the full paper is fixed in **both**; disclose residuals.
3. **Render two-column** — `uv run <skill>/scripts/render-paper.py <topic>/<research-short-name>
   --short` → `build/<slug>-short.pdf`, target ≤5 pages excluding references. No EPUB. Best-effort:
   if `pandoc`/`typst` are missing, keep `paper-short.md` and skip the PDF with a recorded note —
   never fake a build.

Commit `paper-short.md` + `build/<slug>-short.pdf`; the PR (Step 6) ships them in addition to the
full paper and notes the short form.
```

- [ ] **Step 2: Add the short-form edge cases**

In the `## Edge cases` list of `SKILL.md`, add these bullets:

```markdown
- Short form must never be more (or less) honest than the full paper → it inherits and discloses the
  same residuals; a re-gate finding that traces to the full paper is fixed in both (see Step 5b).
- `pandoc`/`typst` missing for the short render → keep `paper-short.md`, skip the short PDF, say so;
  never fake (same as the full render).
- Human-review follow-up (Step 7) that changes claims/numbers → regenerate the short form (re-gate +
  re-render) so it does not drift from the paper.
```

- [ ] **Step 3: Reference the PR-description note (Step 6)**

In `## Step 6 — Publish as a PR`, find the sentence beginning "The PR description summarizes:" and
add `the condensed short form (paper-short.md + build/<slug>-short.pdf),` to that list of items.

- [ ] **Step 4: Verify**

Run: `grep -n "Step 5b" plugins/madskillz/skills/scientific-study/SKILL.md`
Expected: at least one match (the heading).

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/SKILL.md
git commit -m "feat(scientific-study): always-on Step 5b condensed short form"
```

---

### Task 5: Add the eval and bump the plugin version

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/evals/evals.json`
- Modify: `plugins/madskillz/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: the Step 5b behavior (Task 4).
- Produces: an eval locking the short-form behavior; a bumped plugin version.

- [ ] **Step 1: Add the eval**

In `evals/evals.json`, insert this object into the `tests` array immediately before the
`no-trigger-control` test:

```json
    {
      "id": "short-form-alongside-full",
      "prompt": "Produce a study on <topic> and get it ready to publish.",
      "should_trigger": true,
      "grading_criteria": [
        "After the full paper passes the quality gate and renders, also produces a condensed paper-short.md and a two-column build/<slug>-short.pdf (Step 5b) — in ADDITION to the full paper, never replacing it",
        "The short form is a specialist condensation: drops the glossary, acronyms index, background, and inline definitions; keeps a 1-paragraph abstract, the figures, the 1-2 key tables, and references",
        "Introduces NO number that is not already in paper.md / data/ (no new analysis)",
        "Re-gates the short form with the claims-ledger and adversarial reviewers as a compression check and fixes any dropped-caveat / reintroduced-overclaim / mislabeled-metric finding",
        "Targets <= 5 pages excluding references; if pandoc/typst are unavailable, keeps paper-short.md and skips the PDF with a recorded note, never faking a build"
      ]
    },
```

- [ ] **Step 2: Validate the JSON**

Run: `python3 -c "import json; json.load(open('plugins/madskillz/skills/scientific-study/evals/evals.json')); print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Bump the plugin version**

In `plugins/madskillz/.claude-plugin/plugin.json`, change `"version": "0.20.0"` to `"version": "0.21.0"`.

- [ ] **Step 4: Validate and commit**

Run: `python3 -c "import json; json.load(open('plugins/madskillz/.claude-plugin/plugin.json')); print('ok')"`
Expected: `ok`.

```bash
git add plugins/madskillz/skills/scientific-study/evals/evals.json \
        plugins/madskillz/.claude-plugin/plugin.json
git commit -m "test(scientific-study): eval short form; bump madskillz to 0.21.0"
```

---

## Verification (end-to-end)

- [ ] Run the short render against the real exemplar study (already built this session) to confirm the script path matches the hand-built oracle:

Copy the existing `stacked-fanin-pipeline-diversity` study folder (with its `paper-short.md`) to a scratch dir and run:
`uv run plugins/madskillz/skills/scientific-study/scripts/render-paper.py <scratch>/stacked-fanin-pipeline-diversity --short`
Expected: writes `build/stacked-fanin-pipeline-diversity-short.pdf`; opening it shows a two-column layout ≤5 pages excluding references.

- [ ] Confirm the full render still works unchanged: `render-paper.py <scratch>/stacked-fanin-pipeline-diversity` writes both `.pdf` and `.epub`.
