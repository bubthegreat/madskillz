# Binding findings — the test every finding must pass

Every reviewer reads this file with its rubric. It sets **which findings the writer must act on**.
The goal is a paper that is accurate *and* readable: the numbers carry the meaning, and words are
added only where a reasonable reader would otherwise get it wrong.

## Why this file exists

A review panel left to itself ratchets toward hedging. Every correctness reviewer optimizes
defensibility, and declining to say something is always more defensible than saying it. Each cycle
adds a qualifier and none removes one, so a paper gets harder to read every round. Owners have
judged the result "written by someone more concerned about never being proven wrong than by someone
who wants to effectively communicate the truth."

Hedging does not buy accuracy. In one study, three review cycles stacked qualifiers onto sentences,
yet no reviewer caught that the grading scheme filed replicated correlations under "not supported."
The owner caught it. That was a real inference error, and it ran in the *understating* direction,
which no rubric asked about.

## The binding test

A finding is **binding** only when all three hold:

1. **A false belief.** A reasonable reader at the expected reading level (`expected-reader.md`),
   reading the sentence as written, would come away believing something specific.
2. **Contradicted by evidence.** That belief is contradicted by the evidence: a data row, a
   source, a figure or table, or the study's own method.
3. **A fix that removes the false belief.** The fix is a deletion or a factual correction, named
   in the finding.

The test runs in **both directions**. Understating is as binding as overstating:

| Overstates (binding) | Understates (binding) |
|---|---|
| a link reported as a cause | a replicated link reported as "not supported" |
| "a third is genetic" from a twin model | "no way to change it" from tests too small to detect a change |
| one team's result called "established" | "not shown" written as "shown not to work" |
| a wrong number, or a citation that does not say it | a precise null written as "unclear" |

Everything that fails the test is a **note**: non-binding, and the writer may ignore it. A note
that raises a real open question ("does this hold past three months?", "what about teams?") should be
phrased as that question, so the writer can add it to the study's `follow-ups.md` instead of adding a
qualifier to the sentence.

## Writing a binding finding

State it in this shape. A finding that cannot fill in every line is a note.

```
Sentence: "<quoted verbatim>" (location)
Reader would believe: <the specific false belief>
Evidence says: <what contradicts it, with the row id, source or figure>
Fix: delete <…> | correct <fact> to <fact>
```

- **Never draft replacement prose.** Name the deletion or the corrected fact. The writer owns the
  sentence. Reviewer-drafted sentences pasted into a paper are what produce committee prose.
- **A qualifier is a fix only when it is the correction.** "Linked (cause not shown)" corrects a
  reader who would infer cause. "The sample was small" corrects nothing when the interval or the
  figure already shows it.

## What is never binding

These are notes, however they are labeled:

- **Word choice, tone and phrasing** when the reader would not form a false belief.
- **A missing caveat** when the caveat already lives once in Methods or Limits.
- **A second qualifier.** One qualifier per claim. Full caveats live once, in Methods or Limits,
  and are referenced, not repeated.
- **Precision for its own sake.** Asking for an interval, a test statistic or an exact value in the
  prose. Numbers live in figures and tables (`expected-reader.md`, "Numbers in the text").
- **A true but strong sentence.** If the evidence supports it, it passes, however bold it reads.
- **Re-raising unchanged text.** On a re-review cycle, text that did not change since the last
  cycle can be the subject of a new finding only if the finding is binding.

## Severity

Severity applies to binding findings only (see `review-report-format.md`):
- **blocker**: the false belief is about a headline claim, a registered question's answer, or an
  integrity matter (fabrication, unsupported citation, data rights);
- **major**: the false belief is about any other claim;
- **minor**: the false belief is real but small, and a careful reader would likely catch it.

A note has no severity. The meta-editor lists notes separately, and they never become
"fix before publication."
