---
description: Entry point to the scientific research family — runs the adversarial peer-review panel on a draft (more research phases coming).
argument-hint: [path to draft, or what you want reviewed]
---

You are the entry point to the `scientific-*` research skill family. The built
capabilities today are **peer review** and **archival**; study design, write-up,
analysis, and reproducibility packaging will be routed from here as they are added.

Invoke the `scientific-peer-review` skill to run the adversarial multi-reviewer
panel.

To preserve a completed or reviewed study — push the paper plus its pertinent
data/scripts/assets to the private `jmresearch/research` repo under
`<topic>/<research-short-name>/`, after a dataset-licensing and privacy compliance
gate — invoke the `scientific-archive` skill. It is the family's final, archival
phase and the hand-off target from peer review.

What to review: $ARGUMENTS

If no draft (or path to one) was provided above, ask the user for the draft
before proceeding — never review from memory or a verbal description.
