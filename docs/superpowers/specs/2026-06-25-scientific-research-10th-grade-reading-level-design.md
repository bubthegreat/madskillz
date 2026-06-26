# Design: 10th-grade reading level for the scientific-research family

**Date:** 2026-06-25
**Branch:** `worktree-scientific-research-10th-grade-reading-level`
**Status:** approved design → ready for implementation plan

## Problem

The `scientific-*` research family currently calibrates its reader-facing prose to an
**"adjacent-field researcher with an educated-generalist floor."** The plain-language reviewer
even bakes in the assumption that the reader *"knows what a p-value and a confidence interval
are"* and that *"standard scientific concepts need no explanation."*

The owner wants the writing adapted so it is **easily understood by most people — roughly a
10th-grade reading level (age ~15–16, no specialist background)** — while **keeping the clarity
and correctness** the work needs. Anything technical should be *framed adequately*, not removed.

## Audience-bar surface area (where the level is currently encoded)

| File | What it says today |
|---|---|
| `scientific-study/SKILL.md:78` | "Write for the expected reader (adjacent-field body, educated-generalist floor)…" |
| `scientific-study/references/repo-layout.md:42-45` | "written for an adjacent-field researcher with an educated-generalist floor…" |
| `scientific-peer-review/references/reviewers/plain-language.md:9-13` | "The expected reader" block — **assumes p-value/CI knowledge; standard concepts need no explanation** |
| `scientific-peer-review/references/reviewers/accessibility-background.md:9-12` | "The expected reader" block — adjacent-field/educated-generalist |
| `scientific-peer-review/references/reviewers/terminology-acronyms.md` | "defined accessibly for the expected reader" (relative; no explicit level) |
| `scientific-peer-review/SKILL.md:65` | "Readability tier (always, for reader-facing drafts)" (tier name; no level) |
| `scientific-peer-review/references/review-report-format.md:34-37` | readability-tier severity ceiling (level-agnostic) |
| `ask-an-expert/SKILL.md:68` | "Answering directly: a clear, sourced answer…" (no reading-level target) |
| `commands/research.md` | router only; no level stated |

The **writer** (`scientific-study`) and the **judge** (`scientific-peer-review` readability tier)
must move together — otherwise the study writes for a 10th-grade reader while the panel still
judges against an adjacent-field peer, and the two contradict each other.

## Scope (approved)

All reader-facing surfaces of the family:

- **`scientific-study`** — writes the paper.
- **`scientific-peer-review`** — readability tier judges it.
- **`ask-an-expert`** — the **direct-answer-to-user** path only.
- **`commands/research.md`** — one-line statement of the house default.

**Out of scope (deliberately untouched):**

- Expert **persona definitions** (`experts/*.md`) — internal tooling: Scope/Boundaries/credentials,
  not reader-facing prose.
- The expert **panel-reviewer report shape** — machine-consumed by the meta-editor; when its
  findings land in the paper they are already governed by the readability tier.
- The **severity model** and the **integrity stance** — see "Invariants" below.

## Approach (approved): single source of truth

Define the standard **once** in a new shared reference and point every surface at it, rather than
restating the band in ~5 places (which already drift — only the plain-language rubric carries the
p-value assumption). This matches the family's existing shared-contract pattern: every reviewer is
already dispatched with `review-report-format.md` alongside its own rubric, so adding **one more
shared reference for the readability tier** is architecture-consistent, not a new mechanism.

Rejected alternative — inline the band in each file: less indirection, but guarantees the drift we
already observe and makes the writer/judge calibration easy to desync.

## Design

### 1. New file: `scientific-peer-review/references/expected-reader.md`

The canonical reading-level standard. Home is `scientific-peer-review` because the readability
tier is the authority on reader level, and the writer "writes to the standard it will be judged
against." It states:

- **House default.** Write so a motivated general reader at about a **10th-grade reading level**
  (age ~15–16, no specialist background) can follow **what was asked, what was done, what was
  found, and why it matters** — *without trading correctness for plainness.* Where a plain word
  would lose real meaning, **keep the precise term and define it; never delete it.** (This is the
  existing "earned-jargon / define-don't-delete" principle, recalibrated downward.)
- **What changes vs. a peer-level draft.** Do **not** assume general scientific literacy.
  Concepts an adjacent-field researcher knows cold — *p-value, confidence interval, control group,
  statistical significance, regression,* and the like — are themselves **defined in plain language
  on first use** and carried in the **Glossary**, because the 10th-grade reader has not met them.
- **Craft rules.** Short sentences; common words over rare ones; one idea per sentence; active
  voice; concrete examples and everyday analogies for abstract ideas; every acronym spelled out on
  first use; every symbol expanded. The **abstract is the true plain-language summary** — a reader
  at this level gets the whole story from it alone (there is no separate lay summary).
- **Override (specialist audience).** A study written **deliberately** for a specialist audience
  states its intended audience **explicitly in its framing** — the same honest-context discipline
  used to mark a replication/validation study. When such a declaration is present, **both the
  writer and the reviewers calibrate to that declared audience** instead of the default. Absent a
  declaration, the 10th-grade default applies. The override **raises the assumed-knowledge bar; it
  never lowers the correctness/integrity bar**, and the Glossary/Acronyms machinery still applies.
- **Defer to correctness (unchanged).** A readability suggestion never reduces precision or
  overrides a correctness finding; conflicts are reframed as "define the term" and surfaced to the
  meta-editor.

### 2. Point each surface at the shared standard (carry only local specifics)

- **`scientific-study/SKILL.md:78`** — replace the "adjacent-field body, educated-generalist floor"
  phrasing with: write for the reader defined in
  `scientific-peer-review/references/expected-reader.md` (10th-grade default). Keep the existing
  abstract-as-plain-summary, define-every-acronym/term, and back-matter requirements.
- **`scientific-study/SKILL.md` Step 1 (framing)** — add the override-recording step: if the study
  is deliberately for a specialist audience, record that intended audience as explicit context (in
  the brief and the paper's framing), exactly as replication/validation intent is recorded today.
- **`scientific-study/references/repo-layout.md:42-45`** — rewrite the "expected reader" paragraph
  to point at the shared standard (10th-grade default + override), keeping the back-matter spec.
- **`scientific-peer-review/SKILL.md` Step 2** — when dispatching the **readability tier**, include
  `references/expected-reader.md` alongside the rubric and `references/review-report-format.md`
  (state it the same way report-format is stated today). Correctness-tier dispatch is unchanged.
- **`reviewers/plain-language.md`** — replace its "The expected reader" block with a pointer to the
  shared file; **delete the "knows what a p-value is / standard concepts need no explanation"
  assumption.** Keep the earned-jargon test, verbosity, and structure checks.
- **`reviewers/accessibility-background.md`** — replace its "The expected reader" block with the
  pointer; the navigability/background-needs checks stand (more concepts now need background, which
  the shared band determines).
- **`reviewers/terminology-acronyms.md`** — "defined accessibly for the expected reader" now
  resolves to the shared band; add a one-line pointer so "accessibly" is unambiguous.
- **`ask-an-expert/SKILL.md` Step 3 (direct-answer path only)** — answer at the default band unless
  the user is clearly asking at a specialist level / requests specialist depth (the override). The
  panel-reviewer path and persona internals are untouched.
- **`commands/research.md`** — one sentence: the family writes for a ~10th-grade general reader by
  default (overridable for explicitly specialist studies), without sacrificing correctness.

### 3. Invariants (must NOT change)

- **Severity model.** Readability findings stay **normally `minor`**, may rise to **`major`** only
  for the already-enumerated cases (a missing/badly-misleading abstract; an essential concept the
  *target* reader cannot follow and has no pointer for; a missing required reader-facing section).
  **Never `blocker`.** Correctness still outranks presentation in every conflict. (At 10th grade,
  "essential concept the reader can't follow" now legitimately catches an undefined p-value.)
- **Integrity stance.** No fabricated reviews/sources; honest coverage; define-don't-delete. The
  reading-level change must not weaken any of this.

### 4. Evals

Add or adjust **one eval each** to lock the recalibration so it cannot silently regress:

- **`scientific-peer-review/evals`** — the plain-language (or terminology) reviewer flags an
  **undefined standard concept** (e.g. a `p-value` used without a plain-language definition) for a
  default-audience draft — something the old "needs no explanation" rubric would have passed.
- **`scientific-study/evals`** — the drafted paper's **abstract is followable by a general
  (~10th-grade) reader**, and standard concepts are defined on first use.

Match the existing eval format in each `evals/evals.json`; do not invent a new harness.

### 5. Delivery

- Work on branch `worktree-scientific-research-10th-grade-reading-level` (this worktree), off
  `origin/main`.
- Bump `plugins/madskillz/.claude-plugin/plugin.json` **0.13.0 → 0.14.0** — a behavior change to
  the skills, per the repo's hand-bump convention.
- Open a **PR for human review** (per the global "propagate to canonical + push for review" rule).
  The canonical source is this repo and the active install (`0.13.0` @ `925660d`) is in sync, so
  editing here + version bump + PR is the correct propagation path.
- **Memory side effect:** the `user-background` auto-memory notes the owner is the "expected
  reader" calibration target. That is now **decoupled** for this family (it targets a 10th-grade
  general reader, not the owner). Update that memory note to reflect the decoupling.

## Acceptance criteria

1. A single canonical `expected-reader.md` exists and is the only place the band/craft-rules/override are defined.
2. Every in-scope surface points at it; no surface still says "adjacent-field/educated-generalist," and the p-value/CI "needs no explanation" assumption is gone.
3. The readability tier is dispatched with `expected-reader.md`.
4. ask-an-expert direct answers default to ~10th grade with the specialist override; persona internals + panel report shape untouched.
5. Severity model and integrity stance unchanged.
6. Evals updated to lock the recalibration.
7. `plugin.json` bumped to 0.14.0; PR opened; `user-background` memory updated.
