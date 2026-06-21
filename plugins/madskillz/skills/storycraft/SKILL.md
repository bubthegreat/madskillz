---
name: storycraft
description: >-
  Use when the user wants to write a story, book, or chapter — "write a story/book/chapter,"
  "work on my book," "draft the next chapter," "turn this into a book," "continue my goblin
  story," or "help me write a kids' chapter book." Co-designs world, characters, and outline
  with the user, then drafts chapter-by-chapter through a writers'-room of specialist agents,
  with a human checkpoint at every chapter boundary. Renders the finished book to EPUB + PDF
  and commits the build artifacts for e-reader sync. Storage is a configurable repo the user
  owns; the skill commits but never pushes.
---

# storycraft: a writers'-room for writing books

Turn a story idea into a **consistent, well-written, multi-chapter book** — co-designed with the
user, drafted chapter-by-chapter by a panel of specialist agents, stored in a configurable git
repo, and rendered to EPUB + PDF for an e-reader.

The skill addresses the recurring failures of chatbot-written stories: inconsistency with itself,
weird or unnatural language, overly repetitive literary devices, and out-of-place filler dialogue.
Each failure mode has a dedicated specialist. Consistency is anchored to a canonical story bible.
The human stays in control at every chapter boundary.

## Relationship to the family

- `personas.md` defines the writers'-room roster (Showrunner, Bible Keeper, Drafter, editorial
  panel, Editor-in-Chief); storycraft orchestrates them.
- `scripts/repetition_scan.py` and `scripts/render.py` are deterministic tools this skill invokes;
  LLM judgment builds on their output, not the other way around.
- `illustration-seam.md` documents the deferred v2 hook where art briefs and images would plug in
  (out of scope v1 — do not implement).

## Integrity stance (non-negotiable)

1. Never fabricate a check, a note, a revision, or a render. Report the real state or the real
   failure.
2. **Preserve the author's voice.** Anti-blandification is a first-class rule; the Editor-in-Chief
   rejects edits that flatten voice for mere "correctness."
3. Never claim a chapter passed a check it did not. Unresolved notes are surfaced at the
   checkpoint, not hidden.
4. The human approves every checkpoint. The skill commits but **never pushes** and never invents
   plot, characters, or canon the user did not approve.
5. The bible is canon. Drafts and editors read it; only the Continuity Checker → Bible Keeper
   path writes it, and only with adjudicated, user-visible canon.

## Phase 0 — Setup / resume

Delegate to **`repo-layout.md`** for all path resolution, config loading, and repo init.

Resolve the stories repo from `~/.claude/storycraft/config.yaml`. Pick an existing book slug or
create a new one. Load `book.yaml` + `bible/`. The skill is fully resumable from on-disk state —
load the existing `book.yaml` and bible, determine which phase was last completed, and continue
from there without re-running completed phases.

**Edge cases:**
- No stories repo configured → resolve per `repo-layout.md` (offer to create and init it).
- Resuming an existing book → load `book.yaml` + all bible files, then continue at the right phase
  based on what is already committed.
- Illustrations requested → note the seam (`illustration-seam.md`) and explain they are out of
  scope for v1.

## Phase 1 — Co-design (interactive)

Delegate to **`co-design.md`** for the full interactive protocol.

Supporting references: **`story-bible.md`** (bible file shapes and update rules),
**`personas.md`** (Showrunner and Bible Keeper briefs).

The Showrunner works with the user through: premise → audience/age + reading level →
genre/tone → POV/tense → characters & world → a chapter-by-chapter outline → a style guide
(voice, do/don't, and the explicit banned crutch phrases). The Bible Keeper writes all of this
to `bible/*`. Commit `book: <slug> bible v1`.

**Checkpoint:** the user approves the outline + bible before any prose is written. Do not proceed
to Phase 2 without that approval.

## Phase 2 — Per-chapter draft loop

Delegate to **`draft-loop.md`** for the full per-chapter protocol.

Supporting references: **`repetition-audit.md`** (scan spec + auditor judgment protocol),
**`personas.md`** (all panel persona briefs and structured-notes schema).

For each chapter beat in the outline:

1. Drafter writes the chapter from the outline beat + bible + the previous chapter's ending.
2. Editorial panel runs in parallel (see `personas.md` for each specialist's brief):
   Line Editor, Dialogue & Character Doctor, Repetition & Device Auditor, Continuity Checker,
   Audience-Fit Editor, Beta Reader.
3. The Repetition & Device Auditor reads the output of `repetition_scan.py` (see Scripts below)
   before judging — deterministic signal first, LLM judgment second. Follow `repetition-audit.md`.
4. Editor-in-Chief adjudicates: dedupes, resolves conflicts, applies agreed edits preserving
   voice, rejects over-editing. Produces the revised chapter.
5. Bible Keeper folds accepted new canon into `bible/*` per `story-bible.md`.
6. **Checkpoint:** present chapter N + a short "what changed / open questions" digest. User
   approves or redirects; on redirect, revise and re-checkpoint. On approval, commit
   `book: <slug> ch.NN`.

Drafting is sequential (each chapter depends on the prior); the editorial panel runs concurrently.

## Phase 3 — Assemble & render

Delegate to **`render.md`** for the full render pipeline.

Stitch chapters + minimal front matter (title page, chapter titles, dedication) and invoke
`render.py` (see Scripts below). Commit `build/<slug>.epub` and `build/<slug>.pdf` so they sync
to the e-reader via the repo.

## Scripts

Both scripts use PEP 723 inline deps and must be run via `uv run`.

**Repetition scan** (invoke during Phase 2, before the Repetition & Device Auditor's judgment):

```
uv run plugins/madskillz/skills/storycraft/scripts/repetition_scan.py <book_dir>
```

Emits a report: most-frequent n-grams (2–6 grams), crutch words above threshold, repeated
dialogue beats, and near-identical chapter openings. The Repetition & Device Auditor reads this
report and judges which repetitions are lazy vs. intentional motif. See `repetition-audit.md`.

**Render** (invoke during Phase 3):

```
uv run plugins/madskillz/skills/storycraft/scripts/render.py <book_dir>
```

Runs pandoc → EPUB and Typst → PDF. Commits `build/<slug>.epub` and `build/<slug>.pdf`. See
`render.md` for the full pipeline, front-matter stitching, and failure handling.

## Edge cases

- **No stories repo configured** → resolve per `repo-layout.md`; offer to create and init the
  repo before proceeding.
- **Resuming an existing book** → load `book.yaml` + all bible files; determine the last
  completed phase from on-disk state; continue from there without re-running completed phases.
- **Illustrations requested** → explain that illustration support is deferred to v2; the seam is
  documented in `illustration-seam.md`. Proceed with text-only output.
- **User redirects at a checkpoint** → revise and re-checkpoint; do not commit until the user
  approves.
- **Render failure** → report the real error from pandoc/Typst; do not fake a successful build.
- **bible/ out of date with prose** → treat the bible as canon per the integrity stance; surface
  the discrepancy to the user rather than silently patching either source.
