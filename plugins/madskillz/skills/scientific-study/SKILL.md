---
name: scientific-study
description: >-
  Use when the user wants to produce or publish a research study or paper — run or
  produce a research study, "research X and write it up," produce a paper meant for
  publication, get a study peer-review-gated before a human sees it, or open a PR
  with the research. Trigger on phrases like "do a research study on…," "research and
  write up…," "produce a paper on…," "get this study ready to publish," or "open a
  PR with the research." Drafts and revises the paper itself and opens a PR to
  jmresearch/research for a human to merge; for review-only, use scientific-peer-review.
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

**Audience.** The study is written for a **~10th-grade general reader** by default (see Step 2 and
`scientific-peer-review/references/expected-reader.md`). If it is deliberately aimed at a specialist
audience, record that intended audience as explicit context in the brief and the paper's framing —
the same honest-context discipline as a replication/validation study — so the drafting and the
review panel both calibrate to it.

Then establish the `<topic>` and a slugified `<research-short-name>` (propose a
default, ask the user to confirm/override; validate as kebab-case). Resolve the repo
and create the study branch **in an isolated per-study worktree** per
`references/git-workflow.md` — this is what lets concurrent research teams run without
colliding on a shared checkout.

## Step 2 — Draft the paper and artifacts

### Step 2a — Write the story spine

After gathering evidence (from Step 1 deep-research or initial synthesis), write `story-spine.md`
in the study folder using the template in `references/story-spine.md`. Complete all five fields:
starting hypothesis, what the data showed, the turn, the one-sentence arc, and the abstract spine
(3 sentences, 10th-grade). Commit `story-spine.md` alone as `narrative: story spine for <slug>`
before writing any prose in `paper.md`.

### Step 2b — Draft the paper

Open `paper.md` with `story-spine.md` visible. The abstract must derive from the **Abstract
Spine** field. Each Results/Analysis section must advance the **One-Sentence Arc** — a section
that could be removed without changing the story is either misplaced or should be cut.

Write `paper.md` and produce/organize any `data/`, `scripts/`, `assets/` the study needs. Be
provenance-honest, using the **citation, cross-reference & provenance conventions** in
`references/repo-layout.md`: cited work as numbered `[N]` citations (the default house style;
the citation specialist may switch to author–date by field), data-derived values pointed to their
**Figure/Table**, assumptions stated in **prose**, and speculation hedged in the **Discussion**
with its caveats — do not assert unsupported claims, and do not invent data or citations. When
generating data figures, follow the visualization conventions in `references/visualization.md` —
seaborn is the required default library; see that file for the PEP 723 dependency header, theme
setup, and when to fall back to matplotlib. **Lead with a chart, not a table, whenever the point
of a comparison is its magnitude, difference, trend, or ranking** (see visualization.md's
chart-first rule): a table that lists numbers the reader is meant to *feel the relative size of*
is a chart rendered illegible. Ship the table too when exact values matter, but let the chart
carry the comparison.

**Claim discipline (sentence-level contract).** Every declarative sentence in `paper.md` is one
of exactly four kinds, and shows its support in-line:

1. **Data-derived** — points at its Figure/Table (or `data/` artifact).
2. **Cited** — carries a citation that supports the *specific* claim made.
3. **Definitional / methodological** — defines a term, or states what *this study* did or assumed.
4. **Marked speculation** — explicitly hedged, and located in the Discussion.

A sentence that fits none of these gets rewritten or cut before commit. Prevalence, consensus,
and priority claims — "most common," "widely used," "standard approach," "typically,"
"routinely," "commonly," "well known," "often," "first to" — are claims about the world: they
are kind 2 (cited) or they are rewritten as kind 3 claims about this study ("our baseline
retries every failure blindly," not "the standard response is to retry blindly"). The abstract
and introduction follow the same contract as every other section — they are where unsupported
world-claims concentrate, and the `claims-ledger` reviewer audits them sentence by sentence in
Step 3.

Write for the expected reader defined in
`scientific-peer-review/references/expected-reader.md` — by default a **~10th-grade general
reader** (no specialist background; standard concepts such as p-values are defined, not presumed),
unless this study is deliberately framed for a specialist audience (see Step 1): the abstract
doubles as the plain-language summary, define every acronym on first use and every specialized
term in the glossary, and end the manuscript with the required back-matter — an **Acronyms**
index, a **Glossary**, and an optional **Background / further reading** section (see
`references/repo-layout.md`). Background readings must be verified sources or clearly-marked
topic suggestions, never fabricated citations. If this is a replication/validation study (per
Step 1), frame it as such. Commit the initial draft (`draft: initial <slug>`).

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

## Step 5 — Render the manuscript (PDF + EPUB)

Build distributable copies of the finished `paper.md` so the study can be read off a
screen — e-readers, tablets, print — not only as Markdown in the repo. Run the
renderer (see `references/render.md`):

```bash
uv run <skill>/scripts/render-paper.py <topic>/<research-short-name>
```

It writes `build/<research-short-name>.pdf` (Typst-typeset, no LaTeX) and
`build/<research-short-name>.epub` (reflowable, adjustable text on an e-reader) into
the study folder, with a table of contents and the `assets/` figures and tables
embedded. Commit them so they ship in the PR (`render: build PDF + EPUB …`). `pandoc`
and `typst` must be on PATH — install per `references/render.md` if missing; if
neither can be installed, publish without the artifacts and say so. Never fake a build.

## Step 6 — Publish as a PR

Lay out the folder per `references/repo-layout.md`, push the study branch, and open
a PR into the default branch of `jmresearch/research` (per `git-workflow.md`). The
PR description summarizes: the study (and whether it is novel or a
replication/validation), how each review cycle changed the paper, any **residual
findings**, any domain **experts** consulted or minted (and any unmet-expertise halt),
and the compliance outcomes. If this run **minted or updated** any experts, also open the
**separate bundled madskillz PR** that ships them (per `git-workflow.md` §4.1) and link it from
the research PR's "Domain experts" section — minted experts live in the madskillz repo, not in
`jmresearch/research`. Report the PR URL. The human reviews and merges there.

## Step 7 — Human-review follow-ups

When a human requests changes in the PR, apply them, **run them back through the
quality gate** (at minimum a focused re-review of the changed sections via
`scientific-peer-review`), and push as a **separate commit** to the same PR branch
so the requested changes are clearly visible. Update the PR description. Repeat as
needed. Never merge — the human does.

## Step 8 — Save the dialogue transcript (provenance)

Save the human<->assistant dialogue of the study to `journey/transcript.md` — the owner's questions
and direction, and the substantive replies/corrections (not tool-call noise). This is **provenance**:
it makes clear which thinking was the owner's vs. where the AI did the heavy lifting. Commit it with
the study. It is **not** part of `paper.md` and carries **no privacy gate** (it is the owner's own
dialogue). The study may also **read** this transcript for refinement context when revising.

## Edge cases

- No brief and no draft → ask what study to produce; never invent a topic.
- Novelty check finds the work is already well-established → confirm intent with the
  user before proceeding (Step 1); continue only as an acknowledged replication or
  after refining the question.
- Loop hits 3 cycles with blockers remaining → publish the PR anyway with the
  blockers prominently flagged as unresolved; do not hide them, do not fake a pass.
- `pandoc`/`typst` missing for the render step → install per `references/render.md`;
  if neither can be installed, publish without the PDF/EPUB and say so. Never fake a build.
- A reviewer finding is disputed → surface it in the PR for the human to adjudicate.
- `gh` missing/unauthed, no push access, or offline → stop with guidance; never fake
  a commit/push/PR (see `git-workflow.md`).
- Dataset not redistributable → reference-only stub; PII/PHI or missing consent →
  block; unknown status → fail-closed (see `compliance-gate.md`).
- Paper needs expertise the panel lacks → the review's domain-coverage triage mints/reuses a
  domain expert via `ask-an-expert`; if adequate expertise cannot be established for a central
  claim, the gate halts and that is surfaced, never faked (see `review-loop.md`).
- Asked to just review (not produce/revise) → use `scientific-peer-review` directly.
- Asked to blog the study / write it up in the owner's voice → out of scope here; use the standalone
  `blog` skill (the study still saves `journey/transcript.md` as provenance, Step 8).
- Asked to merge → out of scope; the human merges the PR.
