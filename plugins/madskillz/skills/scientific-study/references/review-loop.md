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
  apply the plan's BINDING findings to paper.md (and artifacts) — edit faithfully
  run the editor pass (below)
  commit "review cycle <cycle>: address <short summary>"   # snapshot + report + edits together
while plan has blocker-severity findings AND cycle < 3
```

## What the loop may and may not do

The loop's danger is the **hedge ratchet**: every correctness reviewer optimizes defensibility, so
each cycle adds qualifiers and none removes them. After three cycles a clear paper reads like
committee prose, and it is not more accurate for it. These rules hold it level:

- **Only binding findings are applied.** A finding binds when a reasonable reader would believe
  something the evidence contradicts, in either direction (`scientific-peer-review/references/
  binding-findings.md`). Notes are optional, and a note is never applied by adding a qualifier.
- **Open doubts become follow-up questions, not qualifiers.** A note that raises an uncertainty, a
  "what about X", or a caveat the evidence cannot settle is written up as a question in
  `follow-ups.md` (the question, why it is open, what study would answer it). The sentence it was
  aimed at stays as it was. The paper's Discussion lists the main follow-ups in an **Open questions**
  subsection and points to `follow-ups.md` for the rest. This keeps the doubt visible without
  feeding the hedge ratchet. A binding finding is still fixed in the text; moving it to follow-ups
  does not resolve it.
- **Cycle 1 reviews everything. Cycles 2 and 3 verify.** From cycle 2 on, reviewers check that each
  binding finding was fixed and look for new binding findings in **changed** text. Unchanged text
  gets a new finding only if it is binding. No reframing after cycle 1.
- **The editor pass runs after every cycle**, before the commit. One editor with deletion authority
  reads the revised paper whole and:
  - deletes every qualifier that no binding finding requires, keeping at most one per claim;
  - merges repeated caveats into one place in Methods or Limits;
  - moves any caveat that marks an open question rather than correcting a false belief out of the
    prose and into `follow-ups.md`;
  - moves intervals, test statistics and p-values from the prose to the figure or table that holds
    the result, leaving the plain-words meaning in the sentence;
  - restores sentences that the cycle's edits made harder to read.
  It may **not** change a claim's strength, a number, a label or a citation. It reports its
  qualifier count before and after.
- **No extra agent rounds without the owner.** The loop runs the panel at most three times. Any
  further agent round — a grading pass, a re-extraction, a re-review, a verification pass — needs
  the owner's approval first, even when a reviewer or the meta-editor suggests one. Judgment calls
  the panel lists as "decisions for the owner" go to the owner as questions, not to a new agent.
- **After the final cycle, fix only what is blatantly wrong or misleading** (binding findings), and
  say in the PR that those fixes were not re-reviewed. Everything else is a disclosed residual.

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
  correcting the fact, the label, the number or the citation, or deleting the sentence that
  misleads. Fix the false belief the finding names; do not add a qualifier unless that qualifier is
  itself the correction.
- Address binding **minors** when cheap; otherwise list them as residual. Notes are optional; skip
  any note whose fix would add a qualifier or precision to the prose. If the note names a real open
  question, add it to `follow-ups.md` instead.
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
2. Re-gate it: run a **focused**, binding-findings-only `scientific-peer-review` pass over the
   changed sections. Ask the owner before running a full panel pass, and skip the pass when the
   owner says the change is final.
3. Commit as a **separate** commit (`human review: <summary>`) and push to the PR
   branch — so the human's requested changes are clearly visible as their own diff.

Never merge. The human merges the PR.
