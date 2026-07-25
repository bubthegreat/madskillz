# The question register — and why "declined" is not a verdict

## The failure this prevents

A study was given this brief:

> "Research current AI adoption trends and challenges to understand the biggest things that make AI
> adoptions in businesses successful or unsuccessful and where they get the most ROI and least ROI."

Two questions. The framing gate turned them into *"reconcile the conflicting failure statistics,"*
which is a **method**, not the question. That reframing became the paper's spine. Four review cycles
then applied pressure, and pressure lands on whichever section is most quantitative — so the
reconciliation section grew to 1,961 words and the capability section to 1,828, while *where ROI
concentrates* got 1,106 and *what distinguishes successful adopters* got 681.

The brief's two actual questions received less space than the framing device invented to approach
them. No reviewer objected, because **every reviewer in the panel checks defensibility and none
checks responsiveness**.

That is a one-sided objective, and it has a dominant strategy: **narrow until everything is
defensible.** Declining to answer is always more defensible than answering. A study can therefore
pass the quality gate by retreating from the question it was asked.

## The register

At **Step 1**, before any drafting, extract the brief's questions **verbatim** into
`question-register.md` in the study folder, and commit it with the story spine.

```markdown
# Question register

Brief, verbatim:
> <the user's request, quoted exactly>

| # | Question (in the brief's own words) | Verdict | Where answered |
|---|---|---|---|
| Q1 | What makes AI adoptions in businesses successful or unsuccessful? | | |
| Q2 | Where do businesses get the most ROI and the least ROI? | | |

## Framing
The approach chosen at the novelty gate: <e.g. synthesis + reconciliation>.
This is the **method**, not the question. It does not replace or narrow Q1–Q2.
```

Rules:

- Questions are the **user's**, in the user's words. Do not paraphrase them into something more
  tractable — the paraphrase is where the drift starts.
- The framing chosen at the novelty gate is recorded **as the approach**, in its own field, never as
  a substitute question.
- If the study discovers a question worth answering that the brief did not ask, it is **added** as a
  new row marked `emergent`, not swapped in for an original.
- The register is updated only to fill verdicts, never to remove or soften a question.

## The four verdicts

Every registered question carries exactly one, stated in `paper.md` where it is addressed and
summarized in the register:

| Verdict | Means | Requires |
|---|---|---|
| **answered** | The evidence supports a direct answer | The answer, with its support |
| **answered-with-caveat** | Answered, but the answer is bounded | The answer *and* the specific bound |
| **premise-rejected** | The question rests on an assumption the evidence contradicts | What the premise was, what the evidence shows, and what the reader should ask instead |
| **evidence-insufficient** | The evidence base cannot settle it | Why, plus **what evidence would settle it** |

**"Declined" is not on the list, and silence is not a verdict.** A question the study chose not to
pursue is `evidence-insufficient` with an honest reason, or it is `answered-with-caveat` at whatever
strength the evidence supports — never absent.

**`premise-rejected` is a finding, often the best one.** "The failure statistics disagree because
they count different objects, so the question 'what is the real failure rate' has no answer as
posed" is a complete, useful, publishable answer. It is *not* a reason to stop answering; the reader
still needs to know what to ask instead.

**`evidence-insufficient` must be constructive.** "No source publishes a multi-year realized-value
series on a stable instrument" is a real finding about the evidence base — but on its own it leaves
the reader nowhere. Name the study that would settle it.

## How it is enforced

- The **responsiveness reviewer** (`scientific-peer-review/references/reviewers/responsiveness.md`)
  runs every cycle and audits `paper.md` against the register. A registered question with no verdict,
  or a verdict the text does not support, is a **major** finding. A question silently dropped is a
  **blocker**.
- The **PR body** reproduces the register with its verdicts, so a human sees at a glance which of
  their questions were answered and which were not.
- `scripts/check-budgets.py` fails the build if `question-register.md` is missing or has an empty
  verdict cell.

## Interaction with the word budget

The register and the 4,300-word cap work together, and neither is sufficient alone. The cap forces
choices about where the words go; the register decides **which** choices are acceptable. Without the
register, a capped paper just becomes a shorter version of the wrong paper.
