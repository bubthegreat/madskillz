# Research family — token/performance optimization: deferred items

**Date:** 2026-06-20 · **Branch:** scientific-peer-review

Companion to the one-pass optimization review of the `scientific-*` research family. The
**safe** edits below were applied in this session; the **deferred** items are recorded here for
later assessment (they trade some quality/robustness for tokens, or their token ROI turned out
to be marginal).

## Applied this session (safe)

- **A1 — Descriptions trimmed to triggers-only.** The three SKILL `description` blocks
  (`scientific-study`, `scientific-peer-review`, `ask-an-expert`) dropped their workflow
  narratives, kept every trigger phrase/keyword. ~200 words off the *always-on* system-prompt
  footprint, and — per `writing-skills` SDO — removes the "agent follows the description instead
  of reading the skill" failure mode. Net quality **improvement**, not just a token cut.
- **A3 — Meta-editor deliverable relocated.** Moved the `## Meta-editor deliverable` block out of
  `references/review-report-format.md` (which all 9 reviewers load) into
  `references/reviewers/meta-editor.md` (which only the meta-editor loads). Saves ~150 words ×
  ~9 reviewers ≈ **~1,350 words per first-pass cycle**. The single biggest realized per-run win.
- **A2 — Redundant rubric boilerplate stripped.** The shared "return the report shape / list
  inputs available / list checks skipped" contract is now stated once in
  `scientific-peer-review/SKILL.md` Step 2 and removed from the 9 rubrics; each rubric keeps its
  unique checks and its severity anchor. ~180 words/cycle, and rubrics are now purely "what makes
  this reviewer distinct."

Realized savings: ~always-on −200 words; ~per first-pass cycle −1,500 words of reviewer-context
load (less on re-engagement cycles, where fewer reviewers run).

## Deferred — reassess (marginal token ROI, kept for now)

- **A4 — Cross-file de-duplication** (the "expected reader" definition, the integrity rules,
  "never fabricate citations" restated across files).
  **Finding:** most duplicates live in *separate subagent contexts* (each reviewer runs as its
  own agent), so deduping across files does **not** reduce any single context's load — near-zero
  runtime token benefit. Only same-context dups help (e.g. `scientific-study/SKILL.md` Step 2
  restating `repo-layout.md` back-matter, ~40 words). **Recommendation:** treat as a
  maintainability/consistency pass, not a token win; do it only if those files are being edited
  anyway.
- **A5 — Trim `Edge cases` sections that restate steps.**
  **Finding:** these lists are deliberate scannable safety nets, loaded once per study run.
  Trimming ~150 words risks the "preserve the requirements" goal for negligible per-run savings.
  **Recommendation:** keep; at most remove only verbatim restatements (e.g. the novelty-gate and
  disputed-finding edge cases that duplicate Step 1 / the integrity stance word-for-word).

## Deferred — tradeoff items (real savings, touch quality/robustness)

These are the high-leverage savings, but each gives something up. They reduce the **number of
reviewer subagent invocations** — the dominant cost, because every reviewer re-reads the whole
manuscript.

- **B1 — Conditional readability tier.** The 3 readability reviewers are severity-capped (never a
  blocker), so they never gate the loop. Run them **once on the final/clean cycle** instead of
  every cycle. Saves up to ~6 reviewer invocations on a 3-cycle run. *Trade:* no iterative prose
  refinement during the loop (minor — the loop ignores their findings for continuation anyway).
  **Highest-value deferred item; pairs well with B2.**
- **B2 — Mechanical re-engagement instead of the "consult" sub-call.** The meta-editor already
  has each clean reviewer's `Interests` line and the diff; let it decide re-run vs carry-forward
  itself rather than spawning each clean reviewer to answer "does this touch you?" Eliminates N
  consult invocations per re-review cycle. *Trade:* the meta-editor judges relevance instead of
  the reviewer (slightly higher chance of mis-skipping). The `Interests` lines were added for
  exactly this.
- **B3 — Collapse the 3 readability reviewers into 1** "reader-experience" reviewer (they share
  the expected-reader frame + defer-to-correctness rule). ~2 subagents/cycle. *Trade:* less
  specialization; acceptable since all three are minor-only. Compounds with B1.
- **B4 — Make cycle 3 conditional on progress.** Only run the 3rd full panel if cycle 2 actually
  reduced the blocker count. *Trade:* one fewer revision opportunity in the rare "thrashing" case
  (already published-flagged on cap).
- **B5 — Quick-pass input-starved reviewers.** On a "draft only" run, Statistical /
  Reproducibility self-cap yet still fan out as full-rubric subagents; gate them to a short pass
  when their key inputs are absent. ~1–2 subagents on thin drafts. *Trade:* slightly less
  thorough early (they admit they can't do more anyway).

**Suggested order if/when greenlit:** B1 + B2 first (biggest win, lowest regret), then reassess
B3/B4/B5. Net of A + B1 + B2 ≈ ~40–50% fewer reviewer invocations per study.

## Do-not-cut guardrails (these *are* the requirements)

- The per-SKILL **integrity-stance** repetition is deliberate anti-rationalization bulletproofing.
- The **fail-closed compliance gate** and the **independent-subagent** review model.
- The **report-format contract** itself (split it — A3 — but don't shrink the fields).

## Verification still owed

- Re-run the `evals/evals.json` triggering suites for the 3 skills via the skill-creator/eval
  harness (descriptions changed; all trigger phrases were preserved, so triggering should hold or
  improve).
- Per `writing-skills`, pressure-test that reviewers still emit the correct report shape now that
  the output contract lives only in `SKILL.md` + `review-report-format.md` (not in each rubric).
