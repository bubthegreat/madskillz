# Design: `storycraft` — a writers'-room skill for writing books

**Date:** 2026-06-20
**Scope:** A new madskillz skill that turns a story idea into a consistent, well-written, multi-chapter
book — co-designed with the user, drafted chapter-by-chapter by a writers'-room of specialist agents,
stored in a configurable git repo, and rendered to EPUB + PDF for an e-reader. First target: kids'
chapter books (the owner's goblin stories); designed to be genre/audience-agnostic and usable by
anyone, not hardcoded to the owner.

## Motivation

Stories the owner wrote with a general chatbot "only passed muster because the kids didn't care."
The recurring failures: **inconsistency with itself**, **weird/unnatural language**, **overly
repetitive literary devices**, and **out-of-place conversational filler** ("And Jacob nodded" as the
default character beat). The kids are aging up and want a *real* book. The fix is a structured
pipeline where each failure mode has a dedicated specialist, consistency is anchored to a canonical
story bible, and the human stays in control at chapter boundaries.

## Decisions (confirmed)

- **Name:** `storycraft`.
- **Control model:** hybrid — interactive co-design of world/characters/outline, then per-chapter
  autonomous drafting with a human checkpoint at each chapter boundary.
- **Storage:** a **configurable** stories repo; lightweight commits as work proceeds; the human
  pushes manually (the skill never pushes).
- **Artifact:** text chapter-book now, **Markdown → EPUB + PDF**; illustrations deferred behind a
  clean seam (`illustration-seam.md`).
- **PDF engine:** **Typst** (no LaTeX install). EPUB via **pandoc**.
- **Build artifacts:** **committed** (`build/<slug>.epub` + `.pdf`) so they sync to the e-reader via
  the repo.
- **Room:** Standard panel + Beta Reader (see Personas).

## Integrity stance (non-negotiable)

1. Never fabricate a check, a note, a revision, or a render. Report the real state or the real failure.
2. **Preserve the author's voice.** Anti-blandification is a first-class rule; the Editor-in-Chief
   rejects edits that flatten voice for mere "correctness."
3. Never claim a chapter passed a check it did not. Unresolved notes are surfaced at the checkpoint,
   not hidden.
4. The human approves every checkpoint. The skill commits but **never pushes** and never invents
   plot, characters, or canon the user did not approve.
5. Continuity is grounded in the bible: drafts read it; only the Continuity→Bible-Keeper path writes it.

## Project layout (in the configurable stories repo)

Global config `~/.claude/storycraft/config.yaml`:
```yaml
stories_repo: ~/stories        # path the user configures (their own repo); usable by anyone
author: <name>
```
Each book is a folder in that repo:
```
<stories-repo>/
  <book-slug>/
    book.yaml          # audience/age, reading level, genre, tone, POV, tense, length target,
                       # status, banned_phrases[], illustrate: false
    bible/
      premise.md  characters.md  world.md  outline.md  timeline.md  style-guide.md  glossary.md
    chapters/
      01-<slug>.md  02-<slug>.md  …
    notes/
      ideas.md         # this book's parking lot
      checkpoints.md   # log of the user's per-chapter approvals/redirects
    build/
      <book-slug>.epub  <book-slug>.pdf   # committed
  ideas/               # cross-book concept backlog (e.g. seer-kid, soul-clone) so ideas never get lost
    <concept>.md
```

## Pipeline

### Phase 0 — Setup / resume
Resolve the stories repo from config (offer to create/init it if missing). Pick an existing book or
create a new `<book-slug>`. Load `book.yaml` + `bible/`. Resumable at any phase from on-disk state.

### Phase 1 — Co-design (interactive)
The **Showrunner** works with the user: premise → audience/age + reading level → genre/tone → POV/tense
→ characters & world → a chapter-by-chapter **outline** → a **style guide** (voice, do/don't, and the
explicit banned crutch phrases like "And X nodded"). The **Bible Keeper** writes all of this to
`bible/*`. Commit `book: <slug> bible v1`. **Checkpoint:** the user approves the outline + bible before
any prose is written.

### Phase 2 — Per-chapter draft loop (autonomous draft, human checkpoint)
For each chapter beat in the outline:
1. **Drafter** writes chapter N from the outline beat + bible + the previous chapter's ending (voice/
   tense continuity).
2. **Editorial panel (parallel)** reviews the draft, each returning structured notes
   `{severity, location, problem, suggested_fix}`:
   - **Line Editor** — awkward/weird phrasing, sentence rhythm, clarity, reading-level fit.
   - **Dialogue & Character Doctor** — natural dialogue, distinct character voices, kills filler beats.
   - **Repetition & Device Auditor** — consumes the deterministic scan (below) + judges lazy vs.
     intentional repetition across the whole manuscript.
   - **Continuity Checker** — diff vs. bible (facts, timeline, names); proposes bible updates.
   - **Audience-Fit Editor** — vocabulary/themes/content fit for the target age; engagement.
   - **Beta Reader** — reacts "as a kid" (confusing? boring? where it dragged or delighted).
3. **Editor-in-Chief** adjudicates: dedupe, resolve conflicts, apply agreed edits **preserving voice**,
   reject over-editing. Produces the revised chapter.
4. **Bible Keeper** folds accepted new canon into `bible/*`.
5. **Checkpoint:** present chapter N + a short "what changed / open questions" digest. User approves or
   redirects; on redirect, revise and re-checkpoint. On approval, commit `book: <slug> ch.NN`.

Drafting is sequential (each chapter depends on the prior); the editorial panel runs concurrently.

### Phase 3 — Assemble & render
Stitch chapters + minimal front matter (title page, chapter titles, dedication) → `scripts/render.py`
(PEP 723 inline deps, run via `uv`): **pandoc** → EPUB, **Typst** → PDF. Commit
`build/<slug>.{epub,pdf}` so they sync to the e-reader via the repo.

## Story Bible — the consistency backbone

`bible/` is the single source of truth. `references/story-bible.md` specifies each file's shape and the
**update rules**: drafts and editors *read* the bible; only the Continuity Checker → Bible Keeper path
*writes* it, and only with adjudicated, user-visible canon. The style guide carries the banned-phrase
list the Repetition Auditor and Dialogue Doctor enforce.

## Repetition & Device Auditor mechanism

`scripts/repetition_scan.py` (standalone, PEP 723 inline deps) runs across the manuscript and emits a
report: most-frequent n-grams (2–6 grams), crutch words above a threshold, repeated dialogue beats,
and near-identical chapter openings (similarity over the first N sentences). The auditor persona reads
the report and judges which repetitions are lazy vs. intentional motif. Deterministic signal first,
LLM judgment second.

## Personas as subagents

Each room role is a focused subagent (brief + structured-notes schema) defined in
`references/personas.md`, orchestrated panel→adjudicate exactly like `scientific-peer-review`. Roster:
Showrunner, Bible Keeper, Drafter, [Line Editor, Dialogue Doctor, Repetition Auditor, Continuity
Checker, Audience-Fit, Beta Reader], Editor-in-Chief.

## Skill file layout (in madskillz)

```
plugins/madskillz/skills/storycraft/
  SKILL.md
  references/
    co-design.md          # Phase 1 protocol
    draft-loop.md         # Phase 2 protocol (panel + adjudicate + checkpoint)
    story-bible.md        # bible file shapes + update rules
    personas.md           # the roster: each persona brief + output schema
    repetition-audit.md   # the scan spec + the auditor's judgment protocol
    repo-layout.md        # per-book layout + stories-repo config resolution
    render.md             # EPUB (pandoc) + PDF (Typst) pipeline
    illustration-seam.md  # the deferred v2 hook (where art briefs/images would plug in)
  scripts/
    repetition_scan.py    # PEP 723 inline deps
    render.py             # PEP 723 inline deps (pandoc + typst)
  evals/evals.json
```

## Testing

- `evals/evals.json` — triggering accuracy ("write a story/book/chapter," "work on my book").
- Unit tests for `scripts/repetition_scan.py` (known repeated phrases are detected; clean text is
  clean) and `scripts/render.py` (a fixture Markdown renders to a valid EPUB + PDF), mirroring the
  hook-test pattern.
- One end-to-end **2-chapter "tiny book"** smoke: co-design a trivial outline, draft 2 chapters, render
  both formats — must produce a valid EPUB + PDF.

## Out of scope (v1)

- Illustrations / image generation and fixed-layout art (a clean seam is left in
  `illustration-seam.md`).
- Auto-push / PR flow (storage is manual-push by decision).
- Publishing to any store or device sync beyond committing the build artifacts.
- Non-prose formats (screenplay, comic script).

## Success criteria

- From a premise, the skill co-designs a bible + outline the user approves, then drafts chapters that
  (a) stay consistent with the bible, (b) read naturally for the target age, (c) avoid repeated devices
  and filler dialogue (verified by the auditor's scan), with the author's voice intact.
- The user controls each chapter at its checkpoint; nothing is invented past their approval.
- `build/<slug>.epub` and `.pdf` render cleanly and are committed for e-reader sync.
- The skill is genre/audience-agnostic and points at a stories repo the user configures.
