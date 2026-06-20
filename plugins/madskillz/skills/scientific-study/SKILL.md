---
name: scientific-study
description: >-
  Produce a publication-ready scientific research study: frame the question (with a
  novelty/prior-art check), draft the paper (plus data/scripts/assets), then drive
  it through an agentic peer-review quality-gate loop — revising the paper against
  the panel's feedback until it clears, with a dataset-licensing/privacy compliance
  gate — and publish it as a PR to the private jmresearch/research repo for a human
  to review and merge. Use whenever the user wants to run/produce a research study,
  write a research paper meant for publication, "research X and write it up," get a
  study peer-review-gated before a human sees it, or push an agentic-reviewed paper
  up for review. Trigger on phrases like "do a research study on…," "research and
  write up…," "produce a paper on…," "get this study ready to publish," or "open a
  PR with the research." Drafts and revises the paper itself; reuses
  scientific-peer-review as the review engine; humans review and merge in the PR.
---

# scientific-study: agentic-peer-reviewed research, published as a PR

Turn a research request into a **publication-ready paper** that has already passed
agentic peer review before any human sees it. The skill frames the question, drafts
the paper (and its data/scripts/assets), then loops it through the
`scientific-peer-review` panel — **editing the paper to address each round of
feedback** — until it clears the quality gate, runs a compliance/privacy gate, and
**opens a PR** to the private `jmresearch/research` repo. A human reviews and merges
the PR; nothing reaches `main` without that human approval.

The point: spend agentic review to deliver a high-quality first draft, minimizing
the manual effort a human must spend before publication. Every round of review is a
separate commit, so a reviewer can see exactly how the feedback changed the paper.

## Relationship to the family

- `scientific-peer-review` is the review-only **engine** this skill invokes in a
  loop. This skill owns framing, drafting, revising, gating, and publishing.
- The paper evolves on a study branch; humans are the final gate, in the PR.

## Integrity stance (non-negotiable)

1. Never fabricate a review, a revision, a compliance verdict, a commit, or a push.
   Report the real state or the real failure.
2. Never publish past a gate that did not actually pass. Residual findings the loop
   could not resolve are **disclosed in the PR**, never hidden.
3. Apply reviewer feedback faithfully. A finding you genuinely dispute is surfaced
   in the PR for the human, not silently dropped.
4. Honor data rights and privacy even for a private repo (see the compliance gate).
5. The human merges. This skill opens and updates the PR; it never merges to `main`
   and never pushes to the default branch directly.

## Step 1 — Frame the study (with the novelty gate)

Take the research brief/request (or a draft the user provides). As part of initial
discovery and question framing, run a **novelty / prior-art check**: gauge whether
the question is likely to produce genuinely novel results, or is already
well-established in the literature (use web search / the `deep-research` skill when
available; say so honestly when you cannot).

- **If there is sufficient evidence the study would NOT yield novel results**
  (the question is already well-answered): **stop and ask the user to confirm**
  before diving into the full flow — summarize the prior art and offer: proceed as
  a deliberate **replication/validation** study, **refine** the question to
  something novel, or **cancel**. Do not silently continue, and do not silently
  abort.
- **If the user confirms** they intend to validate/replicate something already
  well-researched, record that intent as explicit context (in the brief and the
  paper's framing) and continue — the study is then framed honestly as a
  replication/validation, not as novel work.

Then establish the `<topic>` and a slugified `<research-short-name>` (propose a
default, ask the user to confirm/override; validate as kebab-case). Resolve the repo
and create the study branch per `references/git-workflow.md`.

## Step 2 — Draft the paper and artifacts

Write `paper.md` and produce/organize any `data/`, `scripts/`, `assets/` the study
needs. Be provenance-honest: distinguish what is **cited**, what is **data-derived**,
and what is **speculation/assumption** — do not assert unsupported claims, and do
not invent data or citations. Write for the expected reader (adjacent-field body,
educated-generalist floor): the abstract doubles as the plain-language summary, define every
acronym on first use and every specialized term in the glossary, and end the manuscript with the
required back-matter — an **Acronyms** index, a **Glossary**, and an optional **Background /
further reading** section (see `references/repo-layout.md`). Background readings must be verified
sources or clearly-marked topic suggestions, never fabricated citations. If this is a
replication/validation study (per Step 1),
frame it as such. Commit the initial draft (`draft: initial …`).

## Step 3 — Agentic peer-review quality-gate loop

Follow `references/review-loop.md`. For each cycle (max 3):

1. Invoke `scientific-peer-review` on the current paper + artifacts → get the
   adjudicated, severity-ranked revision plan.
2. **Edit the paper** to address blocker/major findings (and minors where cheap).
3. Commit the revision as its own commit (`review cycle N: address <summary>`),
   and save that cycle's review report under `review/` so the evolution is visible.

**Stop** when the meta-editor reports **no blocker-severity findings**, or after 3
cycles. Carry the residual (unresolved or disputed) findings forward to the PR
description — never drop them.

## Step 4 — Compliance & privacy gate

Apply `references/compliance-gate.md` to every dataset/third-party artifact before
publishing: classify licensing (include / reference-only), screen for PII/PHI and
human-subjects consent. **Fail-closed** — unknown status is not published without a
recorded override. Record the outcome in `COMPLIANCE.md`.

## Step 5 — Publish as a PR

Lay out the folder per `references/repo-layout.md`, push the study branch, and open
a PR into the default branch of `jmresearch/research` (per `git-workflow.md`). The
PR description summarizes: the study (and whether it is novel or a
replication/validation), how each review cycle changed the paper, any **residual
findings**, any domain **experts** consulted or minted (and any unmet-expertise halt),
and the compliance outcomes. Report the PR URL. The human reviews and merges there.

## Step 6 — Human-review follow-ups

When a human requests changes in the PR, apply them, **run them back through the
quality gate** (at minimum a focused re-review of the changed sections via
`scientific-peer-review`), and push as a **separate commit** to the same PR branch
so the requested changes are clearly visible. Update the PR description. Repeat as
needed. Never merge — the human does.

## Edge cases

- No brief and no draft → ask what study to produce; never invent a topic.
- Novelty check finds the work is already well-established → confirm intent with the
  user before proceeding (Step 1); continue only as an acknowledged replication or
  after refining the question.
- Loop hits 3 cycles with blockers remaining → publish the PR anyway with the
  blockers prominently flagged as unresolved; do not hide them, do not fake a pass.
- A reviewer finding is disputed → surface it in the PR for the human to adjudicate.
- `gh` missing/unauthed, no push access, or offline → stop with guidance; never fake
  a commit/push/PR (see `git-workflow.md`).
- Dataset not redistributable → reference-only stub; PII/PHI or missing consent →
  block; unknown status → fail-closed (see `compliance-gate.md`).
- Paper needs expertise the panel lacks → the review's domain-coverage triage mints/reuses a
  domain expert via `ask-an-expert`; if adequate expertise cannot be established for a central
  claim, the gate halts and that is surfaced, never faked (see `review-loop.md`).
- Asked to just review (not produce/revise) → use `scientific-peer-review` directly.
- Asked to merge → out of scope; the human merges the PR.
