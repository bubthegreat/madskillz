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

**Audience.** The study is written for a **~9th-grade general reader** by default (see Step 2 and
`scientific-peer-review/references/expected-reader.md`). If it is deliberately aimed at a specialist
audience, record that intended audience as explicit context in the brief and the paper's framing —
the same honest-context discipline as a replication/validation study — so the drafting and the
review panel both calibrate to it.

**Record the question register — before anything else is written.** Extract the brief's questions
**verbatim** into `question-register.md` per `references/question-register.md`. The framing chosen at
the novelty gate (e.g. "synthesis + reconciliation") is recorded as the **approach**, in its own
field; it never replaces or narrows the questions. Every question later carries exactly one verdict —
**answered**, **answered-with-caveat**, **premise-rejected**, or **evidence-insufficient**.
*"Declined" is not a verdict and silence is not a verdict*: a question the study did not pursue is
`evidence-insufficient` with an honest reason and a statement of what evidence would settle it.
`premise-rejected` is a legitimate and often superior result — but it owes the reader the replacement
question. This register is what the **responsiveness** reviewer audits every cycle.

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
(3 sentences, 9th-grade). Commit `story-spine.md` alone as `narrative: story spine for <slug>`
before writing any prose in `paper.md`.

### Step 2b — Draft the paper

Open `paper.md` with `story-spine.md` visible. The abstract must derive from the **Abstract
Spine** field. Each Results/Analysis section must advance the **One-Sentence Arc** — a section
that could be removed without changing the story is either misplaced or should be cut.

**The manuscript is four documents, not one — read `references/manuscript-structure.md` before
drafting.** `paper.md` is capped at **4,300 words of body text, ≤4 display items and ≤50
references**, opening with a **≤200-word Summary paragraph** that avoids acronyms and measurements.
`methods.md` (**≤3,000 words, and it may contain no figures or tables**) carries everything needed to
interpret and replicate, and must include a *Deviations from the analysis plan* section.
`extended-data.md` holds up to **10** display items, each cited from the paper or the methods.
`supplementary.md` is uncapped. `paper.md` ends with **Data availability**, then **Code
availability**, then **References**. Section headings are **structural, never thematic** — `## 2.
Results`, not `## 3. The statistics are not measuring the same object`; a heading that states a
thesis is how a paper regrows to forty pages.

Nothing is deleted by this structure; material is relocated and still ships. Run
`uv run <skill>/scripts/check-budgets.py <study_dir>` — it enforces every cap above as a **build
gate**. Reviewers must never spend attention on arithmetic a script does perfectly.

**Delegate production, not just criticism — follow `references/evidence-pipeline.md`.** Do not
research, extract, analyse and write as a single agent and then hand the result to reviewers: in a
completed run that pattern produced 13 first-cycle blockers of which **zero were retrieval failures
and all thirteen were consolidator failures**. Instead, dispatch parallel **extraction agents** that
return structured rows — each row carrying a **verbatim quote containing the value**, plus its
denominator and population — have a second agent **independently re-extract at least 20%**, give
**analysis code its own author** who does not write prose, run a **stats adversary against the
headline result before drafting**, and let the synthesis agent cite **only rows that exist in the
store**. The mandatory quote field and the traceability gate are the two cheapest mechanisms here and
prevent the most damaging class of error; keep both at every study size.

Produce/organize any `data/`, `scripts/`, `assets/` the study needs. Be
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

**A draft is not a publication — never write revision history into the paper.** Everything the
paper says before the quality gate closes is a draft, and *all* of it is a draft until every blocker
is resolved. So the manuscript must never describe its own earlier states as though they had been
reported: no "weaker than we first reported," "we initially reported," "narrower than we first
framed it," "an earlier draft asserted," "this claim is withdrawn," "a retracted correction." Those
phrases fabricate a publication history that does not exist, and they mislead a reader into thinking
a public record was corrected when nothing was ever published. This is the most common way a
hard-revised paper leaks its own drafting process into print, and revising *toward* candour is
exactly when it happens — the impulse to confess is right, the framing is wrong.

State the finding as it now stands, in the present tense, at whatever strength the evidence
supports. When the *reason* for a framing is genuinely methodological, keep the reason and drop the
autobiography: "the comparison is sensitive to a choice that is easy to get wrong: dropping
singleton groups makes the rival grouping look weaker than it is" — not "an earlier version of this
analysis dropped singleton groups." When an error in **this study's own extraction or analysis**
bears on how much a reader should trust the rest, disclose it as a **methods finding about the
study**, not as a retraction of a claim: "during extraction we recorded X, which appeared
inconsistent with Y; it is not, because…" — kind 3, present tense, no implied prior report.

The revision history belongs in `review/`, `journey/transcript.md`, and the git log, which exist for
exactly this purpose and are where an auditor looks for it. The paper is the artifact; those are the
record. (Two things this rule does *not* forbid: retracting or correcting genuinely **published**
work, including this study's own prior published version if one exists — say so plainly and cite it;
and a **superseded-status header on a drafting artifact** such as `story-spine.md`, which is not the
paper and should say what the finished paper retracts from it.)

A sentence that fits none of these gets rewritten or cut before commit. Prevalence, consensus,
and priority claims — "most common," "widely used," "standard approach," "typically,"
"routinely," "commonly," "well known," "often," "first to" — are claims about the world: they
are kind 2 (cited) or they are rewritten as kind 3 claims about this study ("our baseline
retries every failure blindly," not "the standard response is to retry blindly"). The abstract
and introduction follow the same contract as every other section — they are where unsupported
world-claims concentrate, and the `claims-ledger` reviewer audits them sentence by sentence in
Step 3.

Write for the expected reader defined in
`scientific-peer-review/references/expected-reader.md` — by default a **~9th-grade general
reader** (no specialist background; standard concepts such as p-values are defined, not presumed),
unless this study is deliberately framed for a specialist audience (see Step 1): the abstract
doubles as the plain-language summary, and every acronym is defined on first use and every
specialized term is glossed in-line where it first appears. The back-matter — an **Acronyms**
index, a **Glossary**, and an optional **Background / further reading** section — sits at the
**end of `extended-data.md`**, not in `paper.md`; `paper.md` ends at **References** (see
`references/manuscript-structure.md`). Background readings must be verified sources or
clearly-marked topic suggestions, never fabricated citations. If this is a replication/validation
study (per Step 1), frame it as such.

### Step 2c — The house writing standards (the default register)

These are the owner's standing standards. They are the default for every study, and they apply to
all four manuscript documents unless a rule names one document.

**1 — 9th-grade prose.** Follow `scientific-peer-review/references/expected-reader.md` in full,
including its register rules: short declarative sentences carrying one idea each; every technical
term glossed in-line at first use; no sarcasm and no colloquialism; clear referents, so no pronoun
ever points at two possible things; and **one bound per claim, stated once, next to the claim** —
never a stack of qualifiers.

**2 — Minimal citations.** Each point cites **the single best source that proves or disproves it**.
One point, one citation. Do not pile on agreeing sources to look thorough; a stack of citations
hides which source the claim actually rests on. A point may carry more than one citation **only
when the text states the reason** — for example, "four samples set that range, one of them a
synthesis of the others' field, which is why four sources are cited," or "two sources are cited
because each half of the sentence rests on different evidence." If the reason cannot be written
into the sentence, the extra citations do not belong there. **Every other source in the store is
still inventoried** — in the supplementary documents, each with a one-line reason it carries no
claim in the paper. Nothing is dropped; it is relocated.

**3 — No process or iteration narrative, anywhere in the manuscript.** The manuscript reports what
is true, not how the work got there. Nothing in `paper.md`, `methods.md`, `extended-data.md` or
`supplementary.md` describes how agents were organized, how a draft changed, what a review round
asked for, or what an earlier version said. That record belongs in `review/`, `journey/` and the
git log, which exist for it. This is broader than the draft-history rule above: **`methods.md`
describes the procedure that produced the result, not the history of the writing.** "A second
agent re-extracted 20% of the rows" is procedure and belongs in Methods. "After cycle 2 a reviewer
asked for the re-check" is history and belongs in `review/`.

**4 — Banned phrasings.** Each of these is a build defect, not a style note:

- **Invented jargon dressed as a standard term.** Do not coin a phrase — "the priced seam," "the
  accountability gap" — and then use it as though the field already uses it. If a term is this
  study's own shorthand, say so in the sentence that introduces it, or use plain words instead.
- **A comparison against an unquantified foil.** "Smaller than the popular claim" is not a
  comparison until the popular claim carries a number. Quantify both sides, or drop the comparison
  and state the measured value on its own.
- **Pre-rating flourishes.** "And it's a big one," "the interesting part is," "strikingly,"
  "notably." These tell the reader how to feel before the reader has the number. State the number
  and let it rate itself.
- **Hedge stacking.** "May possibly suggest, in some cases, that…" is not caution. It is an
  unfalsifiable sentence. Write the one real bound, once (standard 1).

Commit the initial draft (`draft: initial <slug>`).

## Step 3 — Agentic peer-review quality-gate loop

Follow `references/review-loop.md`. For each cycle (max 3):

1. Invoke `scientific-peer-review` on the current paper + artifacts (all four manuscript
   documents, plus `question-register.md`) → get the adjudicated, severity-ranked revision plan.
   The panel includes the **responsiveness** reviewer, which audits the paper against the register:
   a registered question the paper never addresses is a **blocker**, and a paper whose largest
   section serves no registered question is a **major**.
2. **Edit the paper** to address blocker/major findings (and minors where cheap).
3. Commit the revision as its own commit (`review cycle N: address <summary>`),
   and save that cycle's review report under `review/` so the evolution is visible.

**Stop** when the meta-editor reports **no blocker-severity findings**, or after 3
cycles. A cycle does not close while `check-budgets.py` exits non-zero — being over budget is not a
finding to disclose, it is a build failure to fix. Carry the residual (unresolved or disputed) findings forward to the PR
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
uv run <skill>/scripts/check-budgets.py <topic>/<research-short-name>   # must exit 0 first
uv run <skill>/scripts/render-paper.py <topic>/<research-short-name>
```

**One run produces two builds, and both are committed.** They serve two different readers.

| Build | Files | Contents | Table of contents | For |
|---|---|---|---|---|
| **Paper only** | `build/<research-short-name>-paper-only.pdf` / `.epub` | `paper.md` alone | **No** | Reading. It is short, so it needs no contents page |
| **Full assembly** | `build/<research-short-name>.pdf` / `.epub` | `paper.md`, then Methods, Extended Data and Supplementary Information as clearly labelled back sections | Yes | Checking the work |

The paper-only build is the one a person actually reads. The full assembly is the one a person
opens to verify a number, so it keeps its table of contents and its back sections.

Both are Typst-typeset PDFs (no LaTeX) and reflowable EPUBs (adjustable text on an e-reader), with
the `assets/` figures and tables embedded, written into the study folder's `build/`. Commit all
four files so they ship in the PR (`render: build PDF + EPUB …`). `pandoc` and `typst` must be on
PATH — install per `references/render.md` if missing; if neither can be installed, publish without
the artifacts and say so. Never fake a build.

## Step 5b — (retired in v0.22.0)

The condensed short form (`paper-short.md`) is **gone**. It existed because papers ran 30–40 pages
and needed a reader-facing digest; a 4,300-word paper opening with a 200-word Summary paragraph *is*
the digest. Keeping both meant a second document to hold in sync, and in practice a fresh compression
pass reacquired overclaims the full paper had been forced to drop — in one run, of ten caveat
sentences lost in compression, not one omission made the paper look worse.

If a study folder still contains `paper-short.md` from an earlier version, delete it as part of the
next revision and say so in the PR.

## Step 6 — Publish as a PR

Lay out the folder per `references/repo-layout.md`, push the study branch, and open
a PR into the default branch of `jmresearch/research` (per `git-workflow.md`). The
PR description summarizes: **the question register with each question's verdict** (so a human sees at
a glance which of their questions were answered, and how), the study (and whether it is novel or a
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
- Manuscript over budget → **not** a residual to disclose; `check-budgets.py` must exit 0 before a
  cycle closes. Relocate material to `methods.md` / `extended-data.md` / `supplementary.md` rather
  than deleting it (see `references/manuscript-structure.md`).
- A method section that is mostly tables → Nature's rule that **Methods may contain no figures or
  tables** is real and is the one most studies violate. Those tables become Extended Data items and
  Methods references them. Plan for a rewrite, not a move.
- A registered question the evidence cannot settle → verdict `evidence-insufficient`, **plus what
  evidence would settle it**. Never omit the question, and never write "declined".
- The brief's premise turns out to be wrong → verdict `premise-rejected`. This is a finding, often
  the best one; state what the premise was, what the evidence shows, and what the reader should ask
  instead.
- A study folder still carrying `paper-short.md` from before v0.22.0 → delete it in the next
  revision and note it in the PR.
- Asked to just review (not produce/revise) → use `scientific-peer-review` directly.
- Asked to blog the study / write it up in the owner's voice → out of scope here; use the standalone
  `blog` skill (the study still saves `journey/transcript.md` as provenance, Step 8).
- Asked to merge → out of scope; the human merges the PR.
