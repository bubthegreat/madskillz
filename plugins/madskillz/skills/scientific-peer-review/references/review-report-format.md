# Review report format

Every reviewer returns this exact shape. The meta-editor consumes them and emits the
deliverable. Never invent a verdict for a check you could not run — report it as skipped.

## Per-reviewer report

```
Reviewer: <role>
Inputs available: <list> | Checks skipped (missing input): <list or "none">
Recommendation: accept | minor | major | reject
Findings (severity-ranked):
  - [severity: blocker|major|minor] [location: §/line/table]
    Issue: …
    Why it matters: …
    Required change: …
Questions for authors: …
Reviewer notes (optional): <reviewer-specific summary — e.g. Reproducibility's
  conceptual/runnable/bit-for-bit rating, or "no human-subjects/dual-use concern">
```

A check blocked by a missing input or an absent tool appears in up to three places: the
header's `Checks skipped`, a *finding* when it affects a verdict (e.g. an unresolvable
citation is a blocker), and the meta-editor Coverage section. Never report a blocked check as
passed.

Severity scale (shared across reviewers):
- **blocker** — must be fixed before the paper can be submitted; invalidates a central claim,
  or is an integrity/citation failure.
- **major** — needs new analysis, data, or substantial reframing.
- **minor** — improvable but not disqualifying; may be deferred with a note.

**Readability tier severity ceiling:** readability findings (plain-language, terminology &
acronym, accessibility / background) are normally `minor` and may rise to `major` only for a
completeness failure — a term/acronym used but never defined or missing from its index, a missing
required reader-facing section (Acronyms / Glossary), or a missing/badly-misleading abstract. They
are **never `blocker`**; the correctness tier owns blockers, and readability defers to correctness
in every conflict.

## Meta-editor deliverable

```
# Peer-review summary

## Coverage
Reviewers run: <list>
Tiers run: <correctness | correctness + readability>
Inputs available: <list>
Checks not performed: <list, with the missing input that blocked each>
Review independence: parallel subagents | sequential (weaker independence)
Engagement this cycle (re-review only): <per reviewer — full re-review | re-engaged (changes touched interests) | consulted, declined (prior clean verdict carried forward) | first pass>

## Reviewer recommendations
<one line per reviewer: role → recommendation>

## Disagreements
<material conflicts stated explicitly, e.g. "Adversarial: reject vs Statistical: minor — author
adjudicates". If none: "none">

## Revision plan (ranked)
1. [blocker] [from: <reviewer(s)>] [location] — <required change>
2. [major]   …
3. [minor]   …

## Overall call: accept | minor revision | major revision | reject
```
