---
name: scientific-peer-review
description: >-
  Run a draft scientific paper or study through an adversarial multi-reviewer
  peer-review panel and return one adjudicated, severity-ranked revision plan.
  Use whenever the user wants to peer-review a paper or draft, find out what a
  tough reviewer would say, pressure-test a study for statistical,
  reproducibility, consistency, ethics, or citation problems, verify whether
  citations are real and support their claims, or get a draft "peer-review
  ready" before submission. Trigger on phrases like "review this paper," "what
  would Reviewer 2 say," "is this study sound," "check my stats," "are these
  citations real," or "is this ready to submit." Reviews only — it does not
  write or revise the paper.
---

# scientific-peer-review: adversarial peer-review panel

Take a draft scientific paper or study and run it through an adversarial,
multi-reviewer panel, then synthesize one adjudicated, severity-ranked revision
plan. This tells an author exactly what a tough, fair external reviewer would
say — before they submit.

**Review only.** The deliverable is a plan. This skill never edits the paper.
Re-review = run it again. Writing/revising belongs to the author (or a future
`scientific-writeup` skill).

## Integrity stance (non-negotiable)

1. Never fabricate a verdict or a verification. A check you cannot run is
   reported as skipped, never as passed.
2. No silent citation pass — an unverifiable reference is flagged "verification
   pending," never asserted as verified.
3. Surface, don't smooth — genuine reviewer disagreement is reported for the
   human to adjudicate, never averaged away.
4. The review states its own coverage: which reviewers ran, which inputs were
   present, which checks were skipped.
5. Integrity and correctness outrank presentation in every conflict.

## Step 1 — Gather inputs

Required: the **draft manuscript**. If it is not actually provided, ask for it —
do not review from a verbal description.

Optional (each strengthens specific reviewers; absence is handled, not faked):
pre-registration, analysis outputs/results tables, code/reproducibility package,
reference list/bibliography. Note what is present and what is missing.

Detect: are subagents available (Claude Code) or not (e.g. claude.ai)? Is there
network/web access for citation resolution?

## Step 2 — Fan out the reviewer panel

Run these reviewers, each reading ONLY its own rubric plus the manuscript and
available inputs. The panel has two tiers; the coverage statement names which ran.

**Correctness tier (always):**

| Reviewer | Rubric |
|---|---|
| Adversarial ("Reviewer 2") | `references/reviewers/adversarial.md` |
| Reproducibility | `references/reviewers/reproducibility.md` |
| Internal consistency | `references/reviewers/consistency.md` |
| Statistical / methodological | `references/reviewers/statistical.md` |
| Ethics & integrity (can veto) | `references/reviewers/ethics-integrity.md` |
| Citation-integrity | `references/reviewers/citation-integrity.md` |

**Readability tier (always, for reader-facing drafts):**

| Reviewer | Rubric |
|---|---|
| Plain-language / clarity | `references/reviewers/plain-language.md` |
| Terminology & acronym | `references/reviewers/terminology-acronyms.md` |
| Accessibility / background | `references/reviewers/accessibility-background.md` |

The readability tier defers to the correctness tier in every conflict (presentation
never outranks correctness); its findings are normally `minor` and never `blocker`.

**Re-review cycles (incremental re-engagement).** When you are invoked with the previous
cycle's reports and the diff since then (the `scientific-study` loop does this from cycle 2
on), do not blanket-rerun the panel. The meta-editor first runs a re-engagement triage
(`references/reviewers/meta-editor.md`): reviewers with open findings are re-run to confirm
resolution; clean reviewers are consulted on the diff via their `Interests` and only re-run
if it touches them, else their prior verdict is carried forward and disclosed. A first-time
review (no prior state) runs the full panel.

- **In Claude Code:** dispatch them as parallel subagents (use
  `superpowers:dispatching-parallel-agents`). Independent context is what makes
  the reviews genuinely independent.
- **Where subagents are unavailable:** run each reviewer sequentially in a fresh
  framing, adopting one rubric at a time and not reusing prior reviewers'
  reasoning. Disclose the weaker independence in the output.
- **Citation resolution:** when network/web tools exist, the citation-integrity
  reviewer verifies identifiers (reuse the `deep-research` skill or web tools).
  When they don't, it flags references "verification pending" — never a silent
  pass.

Each reviewer returns the report shape in `references/review-report-format.md`.

## Step 3 — Meta-editor synthesis

After all reviewers return, run the meta-editor (`references/reviewers/meta-editor.md`)
over every report. It deduplicates, resolves conflicts (integrity/correctness
wins), ranks findings, surfaces genuine disagreements, and emits ONE ordered
revision plan plus the overall call and the coverage statement.

## Step 4 — Deliver and stop

Present the reviewer reports and the meta-editor deliverable. Stop. Do not revise
the paper. If asked to also rewrite, say that is out of scope here and point to
applying the plan manually.

This skill is the review **engine**. To draft a study, drive it through this panel
in a revise→re-review loop, and publish the result as a PR to `jmresearch/research`,
use the `scientific-study` skill — it owns the writing, the loop, and publishing;
this skill stays review-only.

## Edge cases

- No draft → ask for it; never review from a description.
- Draft only, nothing else → run all reviewers on what's there; the coverage statement
  makes the thinness explicit; Reproducibility/Statistical narrow their claims.
- No network → citation resolution flagged pending, not passed.
- Ethics red flag (human subjects without approval, dual-use, fabrication signs)
  → Ethics-integrity raises a blocker/veto, surfaced prominently.
- Reviewers disagree → meta-editor surfaces the split, does not average it.
- Asked to also rewrite → out of scope; point to applying the plan.
- No subagents (claude.ai) → sequential reviews, reduced independence disclosed.
