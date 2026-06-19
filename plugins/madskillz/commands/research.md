---
description: Entry point to the scientific research family — produce an agentic-peer-reviewed study (published as a PR), or run the peer-review panel on a draft.
argument-hint: [a research question/topic to study, or a draft to review]
---

You are the entry point to the `scientific-*` research skill family. Route to the
skill that matches the request:

- **Produce a research study** (draft a paper, drive it through the agentic
  peer-review quality-gate loop, run the compliance/privacy gate, and open a PR to
  the private `jmresearch/research` repo for a human to review and merge) → invoke
  the **`scientific-study`** skill. This is the default for "do a study on…,"
  "research and write up…," or "get this ready to publish."
- **Just review an existing draft** (adversarial multi-reviewer panel → one ranked
  revision plan, review-only) → invoke the **`scientific-peer-review`** skill.

Study design, analysis, and reproducibility packaging will be routed from here as
they are added.

Request: $ARGUMENTS

If nothing was provided above, ask the user what study to produce (or what draft to
review) before proceeding — never invent a topic or review from a verbal description.
