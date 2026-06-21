# storycraft Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `storycraft` madskillz skill — a writers'-room that co-designs a book with the user, drafts it chapter-by-chapter with a specialist editorial panel, stores it in a configurable git repo, and renders it to EPUB + PDF.

**Architecture:** A madskillz skill = `SKILL.md` (orchestration spine) + `references/*.md` (phase protocols, personas, bible/repo/render specs) + `scripts/*.py` (two deterministic helpers: a repetition scanner and a renderer) + `evals/`. The two scripts are pure-stdlib Python run via `uv` and are built test-first; the references are authored protocol docs the agent follows; a final integration smoke renders a fixture book.

**Tech Stack:** Python 3 (stdlib only; PEP 723 inline-deps headers, run via `uv`), `pytest` (via `uv run --with pytest`), pandoc (EPUB), Typst (PDF, via `pandoc --pdf-engine=typst`), Markdown.

## Global Constraints

- Skill name is exactly `storycraft`. Skill lives at `plugins/madskillz/skills/storycraft/`.
- Standalone scripts use PEP 723 inline deps and are invoked with `uv run` (never `uv init`/`uv add`). Both scripts in this plan are stdlib-only, so their `dependencies` lists are empty.
- The skill **commits but never pushes**, and never invents plot/characters/canon past the user's checkpoint approval.
- Preserve the author's voice — anti-blandification is a first-class rule for the Editor-in-Chief.
- Output formats: EPUB (pandoc) + PDF (Typst). Committed under each book's `build/`.
- Story bible is the single source of truth: every persona reads it; only Continuity→Bible-Keeper writes it.
- Spec: `docs/superpowers/specs/2026-06-20-storycraft-skill-design.md` (source of truth for intent).
- Tests run from the repo root. Python test command: `uv run --with pytest pytest <path> -v`.

---

## File Structure

```
plugins/madskillz/skills/storycraft/
  SKILL.md                       # Task 8  — orchestration spine
  references/
    repo-layout.md               # Task 3  — stories-repo config + per-book layout
    story-bible.md               # Task 3  — bible file shapes + update rules
    personas.md                  # Task 4  — roster: each persona brief + output schema
    co-design.md                 # Task 5  — Phase 1 protocol
    draft-loop.md                # Task 6  — Phase 2 panel→adjudicate→checkpoint
    repetition-audit.md          # Task 6  — how the auditor consumes the scan
    render.md                    # Task 7  — EPUB/PDF pipeline + tool install
    illustration-seam.md         # Task 7  — deferred v2 hook
  scripts/
    repetition_scan.py           # Task 1
    render.py                    # Task 2
    tests/
      test_repetition_scan.py    # Task 1
      test_render.py             # Task 2
      fixtures/tinybook/         # Task 2 — 2-chapter fixture (book.yaml + chapters/)
  evals/evals.json               # Task 10
.claude-plugin/plugin.json       # Task 9  — register skill + version bump (if applicable)
docs/superpowers/plans/...       # this file
```

---

## Task 1: Repetition & Device Auditor scanner (`repetition_scan.py`)

Deterministic phrase/n-gram scanner. Pure stdlib. The auditor persona consumes its JSON report.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/scripts/repetition_scan.py`
- Test: `plugins/madskillz/skills/storycraft/scripts/tests/test_repetition_scan.py`

**Interfaces:**
- Produces (importable):
  - `tokenize(text: str) -> list[str]`
  - `find_repeated_ngrams(text: str, n_min: int = 2, n_max: int = 6, min_count: int = 3) -> list[dict]` → each `{"ngram": str, "n": int, "count": int}`, sorted by count desc.
  - `find_crutches(text: str, banned: list[str] | None = None, min_count: int = 4) -> list[dict]` → each `{"phrase": str, "count": int, "banned": bool}`.
  - `chapter_opening_similarity(chapters: list[str], sentences: int = 2, threshold: float = 0.6) -> list[dict]` → each `{"a": int, "b": int, "similarity": float}` for chapter index pairs above threshold.
  - `scan(chapters: list[str], banned: list[str] | None = None) -> dict` → `{"repeated_ngrams": [...], "crutches": [...], "similar_openings": [...]}`.
- CLI: `python repetition_scan.py <book_dir>` reads `<book_dir>/chapters/*.md` (sorted) and prints `scan(...)` as JSON; reads `banned_phrases` from `<book_dir>/book.yaml` if present (simple line parse — see Step 5).

- [ ] **Step 1: Write the failing tests**

```python
# plugins/madskillz/skills/storycraft/scripts/tests/test_repetition_scan.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import repetition_scan as rs


def test_tokenize_lowercases_and_splits_words():
    assert rs.tokenize("Jacob nodded, then JACOB ran!") == ["jacob", "nodded", "then", "jacob", "ran"]


def test_find_repeated_ngrams_flags_filler_beat():
    text = "And Jacob nodded. " * 3 + "The wind blew softly over the quiet hills."
    grams = rs.find_repeated_ngrams(text, min_count=3)
    assert any(g["ngram"] == "and jacob nodded" and g["count"] >= 3 for g in grams)


def test_find_repeated_ngrams_clean_text_is_clean():
    text = "A goblin sneezed. The kettle wept. Stars argued about nothing in particular."
    assert rs.find_repeated_ngrams(text, min_count=3) == []


def test_find_crutches_flags_banned_phrase_even_below_default_threshold():
    text = "She nodded. He nodded once more."
    crutches = rs.find_crutches(text, banned=["nodded"], min_count=4)
    assert any(c["phrase"] == "nodded" and c["banned"] for c in crutches)


def test_chapter_opening_similarity_detects_same_opening():
    a = "The sun rose over the marsh. Grendel woke up grumpy."
    b = "The sun rose over the marsh. Then something else entirely happened."
    sims = rs.chapter_opening_similarity([a, b], sentences=1, threshold=0.5)
    assert sims and sims[0]["a"] == 0 and sims[0]["b"] == 1


def test_scan_returns_all_three_sections():
    report = rs.scan(["And Jacob nodded. " * 3], banned=["nodded"])
    assert set(report) == {"repeated_ngrams", "crutches", "similar_openings"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest plugins/madskillz/skills/storycraft/scripts/tests/test_repetition_scan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'repetition_scan'`.

- [ ] **Step 3: Write the implementation**

```python
# plugins/madskillz/skills/storycraft/scripts/repetition_scan.py
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Deterministic repetition/device scanner for storycraft.

Flags repeated n-grams, crutch phrases, and near-identical chapter openings so the
Repetition & Device Auditor persona can judge lazy vs. intentional repetition.
Pure stdlib; run with `uv run repetition_scan.py <book_dir>`.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

_WORD = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def find_repeated_ngrams(text: str, n_min: int = 2, n_max: int = 6, min_count: int = 3) -> list[dict]:
    toks = tokenize(text)
    out: list[dict] = []
    for n in range(n_min, n_max + 1):
        if len(toks) < n:
            break
        counts = Counter(tuple(toks[i:i + n]) for i in range(len(toks) - n + 1))
        for gram, c in counts.items():
            if c >= min_count:
                out.append({"ngram": " ".join(gram), "n": n, "count": c})
    out.sort(key=lambda g: (-g["count"], -g["n"]))
    return out


def find_crutches(text: str, banned: list[str] | None = None, min_count: int = 4) -> list[dict]:
    toks = tokenize(text)
    counts = Counter(toks)
    banned_set = {b.lower() for b in (banned or [])}
    out: list[dict] = []
    seen: set[str] = set()
    for phrase in banned_set:
        c = text.lower().count(phrase)
        if c >= 1:
            out.append({"phrase": phrase, "count": c, "banned": True})
            seen.add(phrase)
    for word, c in counts.items():
        if c >= min_count and word not in seen and len(word) > 2:
            out.append({"phrase": word, "count": c, "banned": False})
    out.sort(key=lambda x: (not x["banned"], -x["count"]))
    return out


def _opening(text: str, sentences: int) -> set[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return set(tokenize(" ".join(parts[:sentences])))


def chapter_opening_similarity(chapters: list[str], sentences: int = 2, threshold: float = 0.6) -> list[dict]:
    openings = [_opening(c, sentences) for c in chapters]
    out: list[dict] = []
    for i in range(len(openings)):
        for j in range(i + 1, len(openings)):
            a, b = openings[i], openings[j]
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac >= threshold:
                out.append({"a": i, "b": j, "similarity": round(jac, 3)})
    out.sort(key=lambda x: -x["similarity"])
    return out


def scan(chapters: list[str], banned: list[str] | None = None) -> dict:
    joined = "\n\n".join(chapters)
    return {
        "repeated_ngrams": find_repeated_ngrams(joined),
        "crutches": find_crutches(joined, banned=banned),
        "similar_openings": chapter_opening_similarity(chapters),
    }


def _read_banned(book_dir: Path) -> list[str]:
    """Best-effort parse of `banned_phrases:` from book.yaml without a yaml dep.

    Supports a flow list (banned_phrases: ["a", "b"]) or a block list of `- item` lines.
    """
    f = book_dir / "book.yaml"
    if not f.exists():
        return []
    banned: list[str] = []
    in_block = False
    for line in f.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("banned_phrases:"):
            rest = s.split(":", 1)[1].strip()
            if rest.startswith("[") and rest.endswith("]"):
                return [x.strip().strip("\"'") for x in rest[1:-1].split(",") if x.strip()]
            in_block = True
            continue
        if in_block:
            if s.startswith("- "):
                banned.append(s[2:].strip().strip("\"'"))
            elif s and not s.startswith("#"):
                break
    return banned


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: repetition_scan.py <book_dir>", file=sys.stderr)
        return 2
    book_dir = Path(argv[1])
    chapter_files = sorted((book_dir / "chapters").glob("*.md"))
    chapters = [p.read_text(encoding="utf-8") for p in chapter_files]
    print(json.dumps(scan(chapters, banned=_read_banned(book_dir)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest pytest plugins/madskillz/skills/storycraft/scripts/tests/test_repetition_scan.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/storycraft/scripts/repetition_scan.py \
        plugins/madskillz/skills/storycraft/scripts/tests/test_repetition_scan.py
git commit -m "feat(storycraft): deterministic repetition/device scanner"
```

---

## Task 2: Renderer (`render.py`) — Markdown → EPUB + PDF

Stitches a book's chapters into one Markdown doc and renders EPUB (pandoc) and PDF (pandoc `--pdf-engine=typst`). Pure stdlib (shells out). Tests skip cleanly when pandoc/typst are absent.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/scripts/render.py`
- Test: `plugins/madskillz/skills/storycraft/scripts/tests/test_render.py`
- Create fixture: `plugins/madskillz/skills/storycraft/scripts/tests/fixtures/tinybook/book.yaml`, `.../chapters/01-start.md`, `.../chapters/02-end.md`

**Interfaces:**
- Consumes: a book dir laid out per Task 3 (`book.yaml`, `chapters/*.md`).
- Produces (importable):
  - `read_meta(book_dir: Path) -> dict` → at least `{"title": str, "author": str}` (best-effort `book.yaml` parse; defaults `title=<dir name>`, `author=""`).
  - `combine(book_dir: Path) -> str` → single Markdown string: a `# <title>` H1, then each chapter file in sorted order separated by blank lines.
  - `render(book_dir: Path, out_dir: Path | None = None) -> dict` → writes `<out_dir or book_dir/build>/<slug>.epub` and `.pdf`; returns `{"epub": Path, "pdf": Path}`. Raises `RuntimeError` if pandoc/typst missing.
  - `tools_available() -> dict` → `{"pandoc": bool, "typst": bool}` (via `shutil.which`).
- CLI: `python render.py <book_dir>` → renders into `<book_dir>/build/`.

- [ ] **Step 1: Create the fixture tiny book**

```yaml
# plugins/madskillz/skills/storycraft/scripts/tests/fixtures/tinybook/book.yaml
title: The Tiny Goblin
author: Test Author
audience: "ages 7-9"
banned_phrases: ["nodded"]
illustrate: false
```

```markdown
<!-- .../fixtures/tinybook/chapters/01-start.md -->
# The Sneeze

A small goblin named Pib discovered that sneezing turned the lights blue.
```

```markdown
<!-- .../fixtures/tinybook/chapters/02-end.md -->
# The Fix

Pib learned to sneeze on purpose, and the village never bought candles again.
```

- [ ] **Step 2: Write the failing tests**

```python
# plugins/madskillz/skills/storycraft/scripts/tests/test_render.py
import sys, pathlib, zipfile
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import render

FIX = pathlib.Path(__file__).parent / "fixtures" / "tinybook"


def test_read_meta_reads_title_and_author():
    meta = render.read_meta(FIX)
    assert meta["title"] == "The Tiny Goblin"
    assert meta["author"] == "Test Author"


def test_combine_includes_title_and_both_chapters_in_order():
    md = render.combine(FIX)
    assert "# The Tiny Goblin" in md
    assert md.index("The Sneeze") < md.index("The Fix")


def test_render_produces_valid_epub_and_pdf(tmp_path):
    tools = render.tools_available()
    if not (tools["pandoc"] and tools["typst"]):
        pytest.skip(f"pandoc/typst not installed: {tools}")
    out = render.render(FIX, out_dir=tmp_path)
    assert out["epub"].exists() and out["pdf"].exists()
    assert zipfile.is_zipfile(out["epub"])
    with zipfile.ZipFile(out["epub"]) as z:
        assert z.read("mimetype").decode() == "application/epub+zip"
    assert out["pdf"].read_bytes()[:5] == b"%PDF-"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --with pytest pytest plugins/madskillz/skills/storycraft/scripts/tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'render'`.

- [ ] **Step 4: Write the implementation**

```python
# plugins/madskillz/skills/storycraft/scripts/render.py
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --with pytest pytest plugins/madskillz/skills/storycraft/scripts/tests/test_render.py -v`
Expected: PASS — `test_read_meta...` and `test_combine...` pass; `test_render_produces_valid_epub_and_pdf` PASSES if pandoc+typst are installed, else SKIPS with the tools message. If skipped, install and re-run to confirm: `pandoc --version` and `typst --version` must both work (see `references/render.md`, Task 7).

- [ ] **Step 6: Commit**

```bash
git add plugins/madskillz/skills/storycraft/scripts/render.py \
        plugins/madskillz/skills/storycraft/scripts/tests/test_render.py \
        plugins/madskillz/skills/storycraft/scripts/tests/fixtures/
git commit -m "feat(storycraft): EPUB+PDF renderer (pandoc + typst)"
```

---

## Task 3: References — `repo-layout.md` + `story-bible.md`

The structural foundation: how the stories repo + per-book project are laid out and resolved, and the exact shape and update rules of the story bible.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/references/repo-layout.md`
- Create: `plugins/madskillz/skills/storycraft/references/story-bible.md`

- [ ] **Step 1: Write `repo-layout.md`** — must contain, concretely:
  - **Config resolution:** read `~/.claude/storycraft/config.yaml` (`stories_repo:` path, `author:`); if missing, prompt the user for the stories-repo path and offer to `git init` it; record it. Never hardcode a path or owner.
  - **Per-book layout** (copy the tree from the spec §"Project layout"): `book.yaml`, `bible/`, `chapters/NN-<slug>.md`, `notes/{ideas,checkpoints}.md`, `build/` (committed), and the top-level `ideas/` concept backlog.
  - **`book.yaml` fields** (exact keys): `title, author, audience, reading_level, genre, tone, pov, tense, target_chapters, target_words_per_chapter, status, banned_phrases[], illustrate`.
  - **Naming:** `<book-slug>` is kebab-case; chapters are zero-padded `NN-<slug>.md`.
  - **Commit/push rule:** commit at each checkpoint with messages `book: <slug> <what>`; **never push** (the user pushes).
- [ ] **Step 2: Write `story-bible.md`** — must specify each `bible/` file's shape and the update rules:
  - File shapes: `premise.md` (logline + themes), `characters.md` (per character: name, role, voice, traits, arc), `world.md` (setting, rules, factions), `outline.md` (chapter-by-chapter beats), `timeline.md` (ordered events), `style-guide.md` (voice, POV/tense, do/don't, the banned-phrase list), `glossary.md` (canonical names/terms/spellings).
  - **Read/write rule (verbatim intent):** every persona *reads* the bible; only the Continuity Checker → Bible Keeper path *writes* it, and only with adjudicated, user-visible canon.
- [ ] **Step 3: Verify both files exist and cover the required keys**

Run:
```bash
grep -q "banned_phrases" plugins/madskillz/skills/storycraft/references/repo-layout.md && \
grep -q "stories_repo" plugins/madskillz/skills/storycraft/references/repo-layout.md && \
for f in premise characters world outline timeline style-guide glossary; do \
  grep -q "$f" plugins/madskillz/skills/storycraft/references/story-bible.md || echo "MISSING $f"; done
```
Expected: no `MISSING` output; both greps succeed.

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/storycraft/references/repo-layout.md \
        plugins/madskillz/skills/storycraft/references/story-bible.md
git commit -m "docs(storycraft): repo layout + story bible references"
```

---

## Task 4: Reference — `personas.md` (the writers' room)

The roster, each persona's brief, and the **structured note schema** the panel returns.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/references/personas.md`

**Interfaces:**
- Produces (referenced by `draft-loop.md`, Task 6): the note schema all editorial personas emit — `{ "persona": str, "severity": "blocker|major|minor|nit", "location": str, "problem": str, "suggested_fix": str }`.

- [ ] **Step 1: Write `personas.md`** — one section per persona, each with **Mandate**, **Reads** (which bible files / inputs), **Emits** (the note schema above, or for non-reviewers their artifact):
  - **Showrunner** — premise/structure/outline/pacing; the lead in co-design. Emits bible drafts.
  - **Bible Keeper** — owns `bible/*`; the only writer of canon. Emits bible diffs.
  - **Drafter** — writes a chapter from outline beat + bible + prior chapter ending. Emits chapter Markdown.
  - **Line Editor** — weird/awkward phrasing, rhythm, clarity, reading-level. Emits notes.
  - **Dialogue & Character Doctor** — natural dialogue, distinct voices, kills filler beats (e.g. "And X nodded"). Emits notes.
  - **Repetition & Device Auditor** — consumes `repetition_scan.py` output (see `repetition-audit.md`); judges lazy vs intentional. Emits notes.
  - **Continuity Checker** — diffs draft vs bible; proposes canon updates. Emits notes + proposed bible diffs.
  - **Audience-Fit Editor** — vocabulary/themes/content for the target age; engagement. Emits notes.
  - **Beta Reader** — reacts "as a kid" (confusing/boring/where it dragged or delighted). Emits notes.
  - **Editor-in-Chief** — adjudicates all notes: dedupe, resolve conflicts, apply agreed edits **preserving voice**, reject over-editing. Emits the revised chapter + a change digest.
- [ ] **Step 2: Verify the schema and all 10 personas are present**

Run:
```bash
for p in Showrunner "Bible Keeper" Drafter "Line Editor" "Dialogue" "Repetition" "Continuity" "Audience-Fit" "Beta Reader" "Editor-in-Chief"; do \
  grep -q "$p" plugins/madskillz/skills/storycraft/references/personas.md || echo "MISSING $p"; done
grep -q "suggested_fix" plugins/madskillz/skills/storycraft/references/personas.md || echo "MISSING schema"
```
Expected: no `MISSING` output.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/storycraft/references/personas.md
git commit -m "docs(storycraft): writers'-room personas + note schema"
```

---

## Task 5: Reference — `co-design.md` (Phase 1)

The interactive co-design protocol the Showrunner follows to produce the approved bible + outline.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/references/co-design.md`

- [ ] **Step 1: Write `co-design.md`** — an ordered, interactive protocol:
  1. Elicit premise → audience/age + reading level → genre/tone → POV/tense → target length.
  2. Develop characters + world with the user.
  3. Produce a chapter-by-chapter **outline** (beats), and a **style guide** including the banned crutch phrases (seed with "And X nodded"-type filler).
  4. Bible Keeper writes `bible/*` (per `story-bible.md`).
  5. Commit `book: <slug> bible v1`.
  6. **Checkpoint:** present the outline + bible summary; the user must approve before any prose. On redirect, revise and re-present.
  - State the integrity rule: never invent premise/characters the user didn't approve; ask, don't assume.
- [ ] **Step 2: Verify the checkpoint + commit rules are present**

Run: `grep -Eq "[Cc]heckpoint" plugins/madskillz/skills/storycraft/references/co-design.md && grep -q "bible v1" plugins/madskillz/skills/storycraft/references/co-design.md && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/storycraft/references/co-design.md
git commit -m "docs(storycraft): phase 1 co-design protocol"
```

---

## Task 6: References — `draft-loop.md` + `repetition-audit.md` (Phase 2)

The per-chapter heart: draft → parallel panel → adjudicate → bible update → checkpoint → commit; and how the auditor consumes the scanner.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/references/draft-loop.md`
- Create: `plugins/madskillz/skills/storycraft/references/repetition-audit.md`

**Interfaces:**
- Consumes: persona note schema (Task 4); `repetition_scan.py` CLI (Task 1: `python repetition_scan.py <book_dir>` → JSON with `repeated_ngrams`/`crutches`/`similar_openings`).

- [ ] **Step 1: Write `draft-loop.md`** — the ordered loop for each outline chapter:
  1. Drafter writes chapter N (inputs: outline beat, bible, prior chapter ending).
  2. Editorial panel runs **in parallel** (Line Editor, Dialogue Doctor, Repetition Auditor, Continuity Checker, Audience-Fit, Beta Reader); each emits notes per the schema.
  3. Editor-in-Chief adjudicates → applies agreed edits preserving voice, rejects over-editing → revised chapter + change digest.
  4. Bible Keeper folds accepted canon into `bible/*`.
  5. **Checkpoint:** present chapter N + change digest + open questions; user approves or redirects (revise + re-checkpoint).
  6. Commit `book: <slug> ch.NN`. Unresolved notes are disclosed at the checkpoint, never hidden.
  - State concurrency: drafting is sequential across chapters; the panel is concurrent within a chapter.
- [ ] **Step 2: Write `repetition-audit.md`** — how the Repetition Auditor works:
  - Run `uv run plugins/madskillz/skills/storycraft/scripts/repetition_scan.py <book_dir>`; read the JSON.
  - Interpret: `repeated_ngrams` (filler beats/phrases), `crutches` (`banned: true` = style-guide violations to always fix; others = overuse to judge), `similar_openings` (chapters starting alike).
  - The persona judges lazy vs intentional motif and emits notes (schema from Task 4). Deterministic signal first, judgment second.
- [ ] **Step 3: Verify the loop + scanner wiring are present**

Run:
```bash
grep -Eq "parallel|panel" plugins/madskillz/skills/storycraft/references/draft-loop.md && \
grep -q "ch.NN" plugins/madskillz/skills/storycraft/references/draft-loop.md && \
grep -q "repetition_scan.py" plugins/madskillz/skills/storycraft/references/repetition-audit.md && echo OK
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/storycraft/references/draft-loop.md \
        plugins/madskillz/skills/storycraft/references/repetition-audit.md
git commit -m "docs(storycraft): phase 2 draft loop + repetition audit protocol"
```

---

## Task 7: References — `render.md` + `illustration-seam.md` (Phase 3 + seam)

How to render + the tool install, and the documented hook for future illustrations.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/references/render.md`
- Create: `plugins/madskillz/skills/storycraft/references/illustration-seam.md`

- [ ] **Step 1: Write `render.md`**:
  - Tool install: `pandoc` (system package) and `typst` (e.g. `uv tool install typst` or the official release); verify with `pandoc --version` and `typst --version`.
  - Run `uv run plugins/madskillz/skills/storycraft/scripts/render.py <book_dir>` → writes `build/<slug>.{epub,pdf}`.
  - EPUB is the e-reader target (reflowable); PDF via Typst is print/fallback.
  - **Commit** the build artifacts (`git add <book>/build/<slug>.epub <slug>.pdf`) so they sync via the repo.
- [ ] **Step 2: Write `illustration-seam.md`** — the deferred v2 hook: where art briefs/images would plug in (an `illustrate: true` in `book.yaml`, a per-chapter `art/` brief produced by a future Illustration Designer persona, and a fixed-layout PDF path). State clearly it is **not implemented in v1**.
- [ ] **Step 3: Verify**

Run: `grep -q "typst" plugins/madskillz/skills/storycraft/references/render.md && grep -Eq "not implemented|deferred|v2" plugins/madskillz/skills/storycraft/references/illustration-seam.md && echo OK`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/storycraft/references/render.md \
        plugins/madskillz/skills/storycraft/references/illustration-seam.md
git commit -m "docs(storycraft): render pipeline + illustration seam"
```

---

## Task 8: `SKILL.md` — the orchestration spine

Ties the phases and references together; sets triggering, integrity stance, and invocation.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/SKILL.md`

- [ ] **Step 1: Write `SKILL.md`** with:
  - **Frontmatter:** `name: storycraft`; a `description` that triggers on "write a story/book/chapter," "work on my book," "draft the next chapter," "turn this into a book" (third-person, like sibling skills).
  - **Overview:** writers'-room that co-designs then drafts chapter-by-chapter with checkpoints; renders EPUB+PDF; stores in a configurable repo.
  - **Integrity stance:** copy the 5 points from the spec (no fabrication; preserve voice / anti-blandification; never claim an unpassed check; human approves every checkpoint; commit-not-push; bible is canon).
  - **Phase 0–3** each as a short section that **delegates to the matching reference** (`repo-layout.md`, `co-design.md`, `draft-loop.md` + `repetition-audit.md` + `personas.md`, `render.md`), naming them explicitly.
  - **Scripts:** point to `scripts/repetition_scan.py` and `scripts/render.py` with their `uv run` invocations.
  - **Edge cases:** no stories repo configured → resolve per `repo-layout.md`; resuming an existing book → load `book.yaml` + bible and continue at the right phase; illustrations requested → `illustration-seam.md` (out of scope v1).
- [ ] **Step 2: Verify frontmatter + reference wiring**

Run:
```bash
head -5 plugins/madskillz/skills/storycraft/SKILL.md | grep -q "name: storycraft" && \
for r in repo-layout co-design draft-loop personas repetition-audit render; do \
  grep -q "$r" plugins/madskillz/skills/storycraft/SKILL.md || echo "MISSING ref $r"; done
```
Expected: no `MISSING` output.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/storycraft/SKILL.md
git commit -m "feat(storycraft): SKILL.md orchestration spine"
```

---

## Task 9: Register the skill (plugin manifest + version)

Make `storycraft` discoverable and bump the plugin version.

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json` (version bump; and the skills list **only if** skills are enumerated there)

- [ ] **Step 1: Inspect how skills are registered**

Run:
```bash
cat plugins/madskillz/.claude-plugin/plugin.json
ls plugins/madskillz/.claude-plugin/ 2>/dev/null
```
Expected: see the current `version` and whether skills are auto-discovered (a `skills/` dir) or listed explicitly. madskillz auto-discovers skills from `skills/`, so typically only a version bump is needed.

- [ ] **Step 2: Bump the version**

Edit `plugins/madskillz/.claude-plugin/plugin.json`: increment the minor version (new feature), e.g. `0.8.1` → `0.9.0`. If skills are explicitly listed anywhere, add `storycraft`.

- [ ] **Step 3: Validate JSON**

Run: `python3 -c 'import json;json.load(open("plugins/madskillz/.claude-plugin/plugin.json"));print("valid")'`
Expected: `valid`.

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore(storycraft): register skill + bump plugin version"
```

---

## Task 10: Evals (`evals/evals.json`)

Triggering accuracy for the skill description.

**Files:**
- Create: `plugins/madskillz/skills/storycraft/evals/evals.json`

- [ ] **Step 1: Inspect a sibling eval file for the exact format**

Run: `cat plugins/madskillz/skills/blog/evals/evals.json`
Expected: see the schema (prompts that should/should not trigger the skill). Mirror it exactly.

- [ ] **Step 2: Write `evals/evals.json`** following that schema with positives ("write a goblin story for my kids", "draft the next chapter of my book", "turn these notes into a book", "work on my novel") and negatives ("write a blog post about X", "do a research study on Y").

- [ ] **Step 3: Validate JSON**

Run: `python3 -c 'import json;json.load(open("plugins/madskillz/skills/storycraft/evals/evals.json"));print("valid")'`
Expected: `valid`.

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/storycraft/evals/evals.json
git commit -m "test(storycraft): triggering evals"
```

---

## Task 11: End-to-end verification

Confirm the deterministic pipeline works on a real fixture, and document the manual full-skill smoke.

**Files:**
- None created (verification only).

- [ ] **Step 1: Run the full Python suite**

Run: `uv run --with pytest pytest plugins/madskillz/skills/storycraft/scripts/tests/ -v`
Expected: all pass (render test passes if pandoc+typst installed; otherwise install them per `references/render.md` and re-run so it does NOT skip).

- [ ] **Step 2: Deterministic integration smoke — scan + render the fixture**

Run:
```bash
uv run plugins/madskillz/skills/storycraft/scripts/repetition_scan.py \
  plugins/madskillz/skills/storycraft/scripts/tests/fixtures/tinybook
uv run plugins/madskillz/skills/storycraft/scripts/render.py \
  plugins/madskillz/skills/storycraft/scripts/tests/fixtures/tinybook
```
Expected: scan prints JSON with the three sections; render writes `fixtures/tinybook/build/tinybook.epub` + `.pdf`. Verify: `ls fixtures/tinybook/build/` shows both; `head -c5 .../tinybook.pdf` is `%PDF-`. Then clean up the generated `build/` (it's a fixture): `rm -rf plugins/madskillz/skills/storycraft/scripts/tests/fixtures/tinybook/build`.

- [ ] **Step 3: Documented manual full-skill smoke (one-time, by the human/agent runner)**

Invoke the skill on a throwaway premise ("a 2-chapter goblin story for ages 7-9"), confirm: it resolves/creates a stories repo, co-designs a bible+outline with a checkpoint, drafts 2 chapters each through panel→adjudicate→checkpoint, updates the bible, and renders committed EPUB+PDF. This exercises the LLM personas (not unit-testable); record the result in the PR description.

- [ ] **Step 4: Open the PR**

```bash
git push -u origin storycraft-skill
gh pr create --base main --head storycraft-skill \
  --title "storycraft: writers'-room book-writing skill" \
  --body "Implements docs/superpowers/specs/2026-06-20-storycraft-skill-design.md. See plan docs/superpowers/plans/2026-06-20-storycraft-skill.md."
```

---

## Self-Review

**Spec coverage:**
- Configurable stories repo + per-book layout → Task 3. ✓
- Hybrid control (co-design + per-chapter checkpoints) → Tasks 5, 6. ✓
- Writers'-room personas + adjudicator + Beta Reader → Task 4. ✓
- Story bible as canon backbone → Task 3 (+ used in 5/6). ✓
- Repetition/device auditor (deterministic scan) → Task 1 + Task 6 (`repetition-audit.md`). ✓
- EPUB (pandoc) + PDF (Typst), committed → Task 2 + Task 7. ✓
- Illustration seam (deferred) → Task 7. ✓
- Integrity stance (commit-not-push, anti-blandification) → Tasks 8 (SKILL.md) + 3 (repo-layout). ✓
- Skill registration + triggering → Tasks 9, 10. ✓
- Testing (scripts unit + 2-chapter smoke) → Tasks 1, 2, 11. ✓

**Placeholder scan:** No "TBD"/"add error handling"/"similar to Task N". Doc tasks specify exact sections/keys and a grep-based verification, not "write the docs." ✓

**Type consistency:** `scan()`/`render()`/`combine()`/`read_meta()`/`tools_available()` signatures match between Task 1/2 code and their Interfaces blocks; the note schema (`persona/severity/location/problem/suggested_fix`) is defined in Task 4 and consumed by Task 6. ✓
