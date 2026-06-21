---
name: ask-an-expert
description: >-
  Use when the user wants to ask a subject-matter expert a question directly ("ask a
  condensed-matter physics expert whether…," "consult an expert on survival analysis"),
  define or find an expert for a domain ("I need a <domain> expert," "find the right
  expert for this"), or when a peer-review panel hits a domain it cannot credibly judge
  and needs an expert minted or reused (resolving a `requested-expert.md`). Owns the
  shared `experts/` library and the expert-finder. Trigger on phrases like "ask an
  expert," "consult an expert," "is there an expert on X," "define an expert," or "find
  the right expert."
---

# ask-an-expert: reusable domain experts, on demand

Define, maintain, and query reusable **domain-expert personas**. Two ways in: ask an
already-defined expert a question directly, or have one **found and defined** for a domain
that isn't covered yet. Experts live in `experts/<concise-name>.md` and are reused across the
whole `scientific-*` research family and standalone.

## Integrity stance (non-negotiable)

1. An expert persona is a **tool, not a credential**. Never fabricate authority. An expert
   states its scope and its boundaries and says "outside my scope" rather than guessing.
2. Never mint a shallow "expert" to paper over a gap. If adequate expertise cannot be
   responsibly represented, say so plainly.
3. State confidence and uncertainty honestly; cite real, resolvable sources or mark a claim
   as unverified — never fabricate citations.
4. Reuse before you create. Minting a new expert is a last resort: first check whether a
   standing **peer-review reviewer** persona's mandate already covers the need (extend that
   reviewer), then whether an existing expert does. Do not spawn near-duplicate or
   redundant-with-a-reviewer personas.

## Step 1 — Determine the need

- **Direct question to an expert?** First check whether a **standing peer-review reviewer**
  already owns this (`scientific-peer-review/references/reviewers/` — e.g. citation/style → the
  citation-integrity reviewer, stats → the statistical reviewer, ethics → ethics-integrity): if
  one reasonably covers it, engage/extend that reviewer rather than minting an expert. Otherwise
  list `experts/` and pick the persona whose **Scope** covers the question. If one fits, go to
  Step 3. If none fits, go to Step 2.
- **A `requested-expert.md` to resolve** (handed over by `scientific-peer-review`'s
  domain-coverage triage)? Go to Step 2.

## Step 2 — Find the right expert (when none fits)

Follow `references/find-the-right-expert.md`: derive the *actual* expertise the question
demands, check whether a standing reviewer or an existing expert already covers it (reuse or
extend rather than duplicate), and only when neither fits, write a new
`experts/<concise-name>.md` per `references/expert-format.md`. The finder either routes to an
existing persona, returns a ready expert file, or gives an honest "expertise not establishable."

## Step 3 — Engage the expert

Load the chosen `experts/<name>.md`, adopt that persona, and answer the question with the
inputs it needs — within its stated Scope. If the question falls in its **Boundaries**, say so
and recommend (or find, via Step 2) the right expertise instead of guessing.

- **Answering directly:** a clear, sourced answer with stated confidence and any caveats.
- **Serving as a panel reviewer** (when `scientific-peer-review` adds this expert to the
  panel): return the report shape the panel provides, scoped to the claims you are qualified
  to judge.

## Relationship to the research family

- `scientific-peer-review` runs a domain-coverage triage; when the panel can't credibly judge a
  domain it writes a `requested-expert.md` and calls this skill to resolve it (reuse or mint),
  then adds the expert to the panel as a reviewer.
- A newly minted or updated expert is **challenged once** by the panel's adversarial reviewer
  (see `references/find-the-right-expert.md` → Adversarial gate). Auto-continue on success;
  on an egregious unmet gap the caller's gate halts — expertise is never faked.

## Edge cases

- Request too vague ("a physics expert") → the finder derives the concrete subfield required
  (e.g. superconductivity) rather than minting a vague generalist.
- Existing expert is close but incomplete → **update** it (record what was added), don't create
  a near-duplicate.
- Expertise can't be responsibly established → return "expertise not establishable" with the
  reason; never fake it.
- Question is outside the chosen expert's Scope → the expert defers and points to the right
  expertise.
