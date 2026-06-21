# Phase 2 — per-chapter draft loop

This document defines the ordered steps for drafting each chapter during Phase 2 (autonomous drafting + human checkpoint). Repeat for every chapter beat in `bible/outline.md`.

**Concurrency rule:** Drafting is sequential across chapters — each chapter depends on the prior chapter's ending. The editorial panel runs concurrently within a single chapter.

---

## Step 1 — Drafter writes the chapter

Inputs the Drafter reads before writing:
- `book.yaml` (audience, reading level, genre, tone, POV, tense, banned_phrases)
- All `bible/*` (characters, world, premise, timeline, style-guide, glossary)
- `bible/outline.md` — the current chapter's beat(s)
- Previous chapter file `chapters/(N-1)-<slug>.md` — for voice/tense/ending continuity

Output: `chapters/NN-<slug>.md` (zero-padded, e.g. `01-opening.md`).

The Drafter does not draft or commit until the prior chapter's checkpoint has been approved.

---

## Step 2 — Editorial panel (parallel)

All six reviewers run **concurrently** on the current chapter draft. Each persona reads the chapter and emits structured notes in the shared schema:

```json
{
  "persona": "<persona name>",
  "severity": "blocker | major | minor | nit",
  "location": "<chapter/section/paragraph reference>",
  "problem": "<what is wrong and why it matters>",
  "suggested_fix": "<concrete edit or direction>"
}
```

`suggested_fix` is always populated — a note without it is malformed.

### Panel members

| Persona | Focus |
|---|---|
| Line Editor | Prose rhythm, clarity, reading-level fit, sentence-level awkwardness |
| Dialogue & Character Doctor | Natural dialogue, distinct character voices, kills filler beats |
| Repetition & Device Auditor | Scanner-grounded repetition check + lazy vs. intentional judgment (see `repetition-audit.md`) |
| Continuity Checker | Diffs draft against `bible/*`; flags contradictions; proposes new-canon bible diffs |
| Audience-Fit Editor | Vocabulary, themes, content, pacing fit for the target age and reading level |
| Beta Reader | Reacts "as a reader of the target age" — where it confused, bored, or delighted |

The Continuity Checker also produces **proposed bible diffs** (markdown patches to `bible/*.md`) for any legitimate new canon the draft introduces, clearly marked as proposed and not yet applied.

---

## Step 3 — Editor-in-Chief adjudicates

The Editor-in-Chief receives all panel notes and:

1. **Deduplicates** — merges notes pointing at the same issue.
2. **Resolves conflicts** — when reviewers disagree: continuity/correctness beats style, style beats nit. Genuine unresolvable conflicts are surfaced at the checkpoint for the user to decide.
3. **Applies agreed edits** — preserving the author's voice. A note that would flatten or genericize the prose is rejected even if technically "correct." A surfeit of minor edits that collectively blandify the text is grounds to reject the batch.
4. **Accepts or rejects** each Continuity Checker proposed bible diff; passes accepted diffs to the Bible Keeper.

Output:
- Revised chapter Markdown (the text that goes to checkpoint).
- **Change digest** — a short human-readable summary of what changed and why, plus any unresolved disagreements or open questions.

The Editor-in-Chief does not emit structured review notes and does not invent plot or new canon.

---

## Step 4 — Bible Keeper folds canon

The Bible Keeper applies all Editor-in-Chief-accepted Continuity Checker diffs to `bible/*`. No other persona may write to `bible/`. Rejected or uncertain proposals are logged in `notes/checkpoints.md`, not written to the bible.

---

## Step 5 — Checkpoint

Present to the user:
- The revised chapter (full text).
- The change digest (what changed, why, open questions).
- Any **unresolved notes** (notes the Editor-in-Chief could not resolve, or notes the user must decide on). Unresolved notes are **disclosed at the checkpoint, never hidden**.

The user then either:
- **Approves** — proceed to Step 6.
- **Redirects** — provide a direction or correction; revise the chapter and re-run the panel (or a targeted subset), then return to Step 5 (re-checkpoint).

---

## Step 6 — Commit

On user approval, commit the chapter (and any accepted bible updates) with:

```
book: <slug> ch.NN
```

For example: `book: goblin-scouts ch.03`.

The skill **never pushes**. The user pushes manually.

After commit, proceed to the next chapter beat in `bible/outline.md` and return to Step 1.
