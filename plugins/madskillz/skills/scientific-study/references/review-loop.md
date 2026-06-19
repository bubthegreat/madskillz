# Agentic peer-review quality-gate loop

The heart of `scientific-study`: revise the paper against the `scientific-peer-review`
panel until it clears, capturing the evolution as commits so a human can see how each
round of feedback changed the paper.

## The loop

```
cycle = 0
do:
  cycle += 1
  plan   = run scientific-peer-review on the CURRENT paper + artifacts   # the engine
  save plan -> review/cycle-<cycle>.md
  apply plan to paper.md (and artifacts) — edit faithfully
  commit "review cycle <cycle>: address <short summary>"
while plan has blocker-severity findings AND cycle < 3
```

- **Engine, not copy.** Always invoke `scientific-peer-review` fresh on the *current*
  draft each cycle. Do not reuse a prior cycle's findings as if re-run — the whole
  point is to confirm the edits actually resolved them.
- **One commit per cycle.** Each cycle is its own commit so the diff history shows the
  paper's evolution. Never squash the cycles together before the PR.
- **Save each review.** Write every cycle's adjudicated plan to `review/cycle-N.md`,
  so reviewers (and the PR) can see what was raised and how it was addressed.

## Stopping criterion

Stop when **either**:
- the meta-editor reports **no blocker-severity findings** (the gate is passed), or
- **3 cycles** have run (the cap).

A passing gate still commonly leaves **minor/major non-blockers**. Those are carried
into the PR description as "residual findings," not silently dropped.

## Applying feedback faithfully

- Address **blockers** and **majors** by actually editing the paper/artifacts —
  fixing the claim, adding the missing analysis caveat, correcting the citation,
  narrowing an out-of-scope conclusion, etc.
- Address **minors** when cheap; otherwise list them as residual.
- **Never** "resolve" a finding by deleting the inconvenient claim and pretending the
  underlying problem is gone, by fabricating data/citations to satisfy a reviewer, or
  by editing the review report. Resolve the substance or carry it forward.
- **Disputed findings:** if you genuinely believe a finding is wrong, do not silently
  ignore it — record your rebuttal and surface it in the PR for the human to
  adjudicate (integrity stance: surface, don't smooth).

## Residual-findings disclosure (into the PR)

When the loop ends, compile the residuals (anything not resolved — including the case
where 3 cycles ended with blockers still open, and any disputed findings) into the PR
description so the human reviews with full knowledge. Hitting the cap with open
blockers is published **flagged**, never as a clean pass.

## Human-review follow-ups (Step 6)

After the PR is open, a human may request changes. For each request:
1. Apply the change.
2. Re-gate it: at minimum run a **focused** `scientific-peer-review` pass over the
   changed sections (a full panel pass if the change is substantial).
3. Commit as a **separate** commit (`human review: <summary>`) and push to the PR
   branch — so the human's requested changes are clearly visible as their own diff.

Never merge. The human merges the PR.
