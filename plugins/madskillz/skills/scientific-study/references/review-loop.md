# Agentic peer-review quality-gate loop

The heart of `scientific-study`: revise the paper against the `scientific-peer-review`
panel until it clears, capturing the evolution as commits so a human can see how each
round of feedback changed the paper.

## The loop

```
cycle = 0
do:
  cycle += 1
  snapshot CURRENT paper.md -> review/cycle-<cycle>-paper.md   # the exact version this cycle reviews
  plan   = run scientific-peer-review on the CURRENT paper + artifacts   # the engine; cycle>1 also passes prior reports + the cycle-(cycle-1)-paper.md diff for re-engagement triage
  save plan -> review/cycle-<cycle>.md
  apply plan to paper.md (and artifacts) — edit faithfully
  commit "review cycle <cycle>: address <short summary>"   # snapshot + report + edits together
while plan has blocker-severity findings AND cycle < 3
```

- **Re-engage, don't blanket re-run.** From cycle 2 on, pass the previous cycle's
  reviewer reports and the diff since then (`review/cycle-(N-1)-paper.md` vs the current
  `paper.md`) into `scientific-peer-review`. Its meta-editor runs a **re-engagement
  triage**: any reviewer who had open findings is re-run to confirm the edits resolved
  them; a reviewer who was clean is consulted with a specific question about the diff and
  only re-run if the changes touch what they care about, otherwise their prior clean
  verdict is carried forward and disclosed as such. Never carry an *open* finding forward
  as resolved, and never present a carried-forward verdict as a fresh pass.
- **One commit per cycle.** Each cycle is its own commit so the diff history shows the
  paper's evolution. Never squash the cycles together before the PR.
- **Save each review.** Write every cycle's adjudicated plan to `review/cycle-N.md`,
  so reviewers (and the PR) can see what was raised and how it was addressed.
- **Snapshot each reviewed paper.** Before running the panel, copy the current
  `paper.md` to `review/cycle-N-paper.md` — the exact version that cycle N reviewed.
  This lets a reader diff `cycle-1-paper.md → cycle-2-paper.md → … → paper.md` (the
  final) to see the iterations the reviewers produced **without** git. Git history
  stays the source of truth for tracing back to code/asset changes; the snapshots
  optimize the common "show me how the paper changed across review" case. Commit each
  snapshot with its cycle.

## Expert gate (domain coverage)

`scientific-peer-review` runs a domain-coverage triage each review (see its `SKILL.md`). When
the paper needs expertise the panel lacks, it writes a `requested-expert.md`, resolves it via
the **`ask-an-expert`** skill (reuse or mint) — passing the study's **run-id
(`<topic>__<research-short-name>`) and `defer-publish`** so a minted expert is committed to the
madskillz sync clone on the run's branch and published as **one bundled madskillz PR at Step 6**
(see `git-workflow.md` §4.1 and ask-an-expert's `references/expert-writeback.md`), not left in the
research project — and adds the expert to the panel, auto-continuing the cycle. A minted/updated
expert is challenged once by the adversarial
reviewer. If adequate expertise **cannot** be established for a central claim (the egregious
case), the gate **halts**: stop the loop and surface "could not establish adequate expertise
for <domain>" — never fake a qualified review. Record experts consulted/minted, and any halt,
for the PR.

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

## Human-review follow-ups (Step 7)

After the PR is open, a human may request changes. For each request:
1. Apply the change.
2. Re-gate it: at minimum run a **focused** `scientific-peer-review` pass over the
   changed sections (a full panel pass if the change is substantial).
3. Commit as a **separate** commit (`human review: <summary>`) and push to the PR
   branch — so the human's requested changes are clearly visible as their own diff.

Never merge. The human merges the PR.
