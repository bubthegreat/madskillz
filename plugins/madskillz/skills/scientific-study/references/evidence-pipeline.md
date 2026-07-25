# The evidence pipeline — delegate production, not just criticism

## The failure this prevents

In a completed run, 3 subagents did research and 16 reviewed. In its sibling run, 4 researched and
22 reviewed. **~85% of delegation went to auditing work one agent had already done alone.** The
consolidator read the sources, extracted every number, coded every row, wrote the analysis, built
the figures and wrote the prose. Then experts checked it.

The first review cycle returned 13 blockers. Classified by origin:

- **Retrieval failures: 0.**
- **Consolidator failures: 13.**

The sharpest was a blocker where three of four within-instrument comparisons *were already in the
consolidator's own extraction* and it reported one — the one favouring its thesis. Others: a sign
inversion on a source it had read itself, a truncated quotation that manufactured a contradiction,
an abstract that contradicted its own §3.

None of those is a knowledge gap. Every one is **one agent holding everything and losing track**.
Adding reviewers cannot fix it, because review happens after the error is load-bearing and its
author is invested. The fix is upstream: no single agent should ever be in a position to make those
errors.

## The pipeline

```
brief
  → question register (Step 1)
  → EXTRACTION AGENTS         one per source cluster, parallel
       ↳ emit structured rows only, never prose
  → INDEPENDENT RE-EXTRACTION  second agent re-reads a random ≥20% sample
       ↳ disagreement quarantines the row; it is never averaged
  → ANALYSIS AGENT            writes scripts + derived data. NEVER prose
  → STATS ADVERSARY           tries to break the result BEFORE any drafting
  → SYNTHESIS AGENT           writes paper.md. May cite ONLY store rows
  → TRACEABILITY GATE         a build step, not a reviewer
  → review loop (Step 3)
```

### Extraction agents

One per source cluster, run in parallel, each with a clean context. They return **rows, not
narrative**. Every row carries:

| Field | Why |
|---|---|
| `value`, `unit` | the number |
| `denominator`, `population` | what it is a share *of* — the single most common defect |
| `wave` / `date` | temporal comparability |
| **`quote`** | **verbatim text containing the value, from the source** |
| `source_url`, `access_date` | provenance |
| `verified` | status from the study's verification vocabulary |

**The verbatim quote is the load-bearing field.** A sign cannot be inverted and a qualifier cannot
be truncated when the source's own words travel with the number. Two of the worst findings in the
run above — a reversed METR sign and a truncated "of meeting the human baseline" — are both
impossible once the quote is mandatory.

An extraction agent that cannot obtain a quote records `verified: no-unverified` and returns the row
anyway. It never paraphrases a number into existence.

### Independent re-extraction

A second agent, blind to the first's output, re-extracts a random sample of **at least 20%** of rows
from the same sources. Disagreements are **quarantined, not reconciled by averaging or by the
consolidator's judgment** — a quarantined row is either re-verified at primary tier or excluded with
its exclusion recorded.

This is the cheapest available estimate of the extraction's error rate, and it belongs in Methods.

### Analysis agent

Writes `scripts/` and derived data. **Writes no prose and does not know the paper's argument.**

The reason is a conflict of interest that has produced real defects: analysis code written by the
agent whose argument depends on the result acquires bugs that favour the result. In the run above, a
decomposition script silently dropped singleton groups — which made the rival explanation look
weaker — and a confidence interval was computed by a percentile bootstrap whose lower bound was ten
times higher than the exact interval. Both were written by the author of the claim they supported.

### Stats adversary

Runs **before drafting**, not in cycle 2 after the claim is load-bearing. Its charge: break the
headline result. Try the rival grouping. Try the exact interval against the approximate one. Try
leave-one-out. Report what survives.

Findings from this stage go into `methods.md` under *Deviations from the analysis plan* if they
changed a decision rule — which is also how the pre-specification discipline gets enforced in
practice.

### Synthesis agent

Writes `paper.md` against `question-register.md` and the evidence store. **It may cite only rows
that exist in the store.** It cannot introduce a number, and it cannot promote a claim the stats
adversary killed.

### Traceability gate

A **build step**, not a reviewer:

- Every numeric token in `paper.md` and `methods.md` resolves to a row id in `data/`, or the commit
  fails.
- Every registered question has a verdict.
- Budgets from `manuscript-structure.md` hold.

Reviewers must never spend attention on arithmetic a script does perfectly. In the run above, the
paper's own descriptive counts — how many rows came via archive, how many publishers, how many files
in `data/` — were **wrong in three consecutive cycles** despite eleven reviewers. They were
hand-maintained. Counts about the study's own artifacts should be *generated*, never typed.

## What this costs

More agents and more tokens, and it trades one failure mode for another: coordination and
store-schema drift instead of single-agent lapses. Budget for a schema decision up front — the
extraction row shape is the contract every downstream stage depends on, and changing it mid-run is
expensive.

It is also possible to over-fragment. Three to six extraction agents per study is the useful range;
one per source is coordination overhead with no independence benefit, since the failure being
prevented is *one agent holding everything*, not *one agent reading two papers*.

## Scaling down

For a small study, collapse to: 2–3 extraction agents, one analysis agent, one stats adversary,
synthesis on the main thread. Keep the **mandatory quote field** and the **traceability gate** at
every size — they are the cheapest two mechanisms here and they prevent the most damaging class of
error.
