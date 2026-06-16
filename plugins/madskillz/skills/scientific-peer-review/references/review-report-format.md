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
```

Severity scale (shared across reviewers):
- **blocker** — must be fixed before the paper can be submitted; invalidates a central claim,
  or is an integrity/citation failure.
- **major** — needs new analysis, data, or substantial reframing.
- **minor** — improvable but not disqualifying; may be deferred with a note.

## Meta-editor deliverable

```
# Peer-review summary

## Coverage
Reviewers run: <list> (tier: correctness-only | + communication)
Inputs available: <list>
Checks not performed: <list, with the missing input that blocked each>
Review independence: parallel subagents | sequential (weaker independence)

## Reviewer recommendations
<one line per reviewer: role → recommendation>

## Disagreements
<material conflicts stated explicitly, e.g. "Adversary: reject vs Domain: accept — author
adjudicates". If none: "none">

## Revision plan (ranked)
1. [blocker] [from: <reviewer(s)>] [location] — <required change>
2. [major]   …
3. [minor]   …

## Overall call: accept | minor revision | major revision | reject
```
