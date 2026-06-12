---
name: scope-is-a-contract
description: Use when starting feature work, designing error paths or input validation, and when mid-implementation an unhandled edge case, a bug report, "should also handle", or "while I'm here" tempts adding behavior beyond agreed scope.
---

# Scope Is a Contract

## Overview

Scope is a contract agreed before code and defended during code. The out-of-scope list is as load-bearing as the in-scope list — it is what makes KISS/DRY/YAGNI applicable: you can only keep something simple when you know what you decided not to handle.

**Violating the letter of the contract is violating its spirit.**

## Before code: agree the contract

Contract-surface test decides the path:

| Change touches... | Path |
|---|---|
| Public API, user-visible behavior, error paths, new accepted inputs | Full contract (below) |
| Internal only: bugfix within agreed scope, rename, refactor, docs | One-sentence scope statement in chat ("Fixing X; not touching Y"), get ack |

Full contract — agree each line with your partner before implementing, one question at a time. Clarifying questions are not the contract; the written artifact is. Write it even when the answers feel settled in chat:

```
## Scope Contract
In: <what this handles> (why)
Out: <what it deliberately does not handle> (why excluded)
Boundaries: <the lines that keep the design simple>
At boundary: <exact refusal behavior + guidance text>
Amendments: <dated, approved scope changes>
```

Lives as a section in the feature's spec doc (`docs/superpowers/specs/...`), or `docs/scope/<feature>.md` when no spec exists.

## PRINCIPLES.md

Check the repo root. Missing → offer to create it (core purpose in one sentence; named principles P1..Pn; global boundaries). Declined → put a core-purpose line in the contract instead.

Every proposed rule or behavior must be explainable in one sentence pointing at one principle. Can't? Stop and discuss. Rule contradicts a principle? The rule is wrong, not the principle. Two designs detect the same thing? Less machinery wins.

## During code: stop-and-discuss

Edge case, bug report, or "should also handle" outside the contract → STOP. Do not write the code. Surface:

```
Found: <what>
Why outside scope: <which contract line / principle>
Options: <each with cost>
Recommendation: <one>
```

Proceed only on an explicit decision; record it as a dated amendment to the contract. Scope grows only by decision, never by accretion. One-liners count.

## Error paths: refuse with guidance

Require what you can verify; refuse what you can't — telling the user exactly how to comply. Never best-effort guess, and never warn-and-proceed: emitting a warning while acting on an assumption is still guessing.

Example (semverer): versions must resolve to MAJOR.MINOR.PATCH or exit: "version 'v1.2' does not match MAJOR.MINOR.PATCH — fix the tag or pass --version". Package discovery looks top-level and one directory deep, never further; deeper layouts must be specified explicitly.

## Rationalizations

| Excuse | Reality |
|---|---|
| "We found it, so we should fix it" | Discovery is a discussion trigger, not an implementation trigger. |
| "It's one line" | The semverer audit failure was one line. Size isn't surface. |
| "The user obviously wants this handled" | Then they will approve it in one message. Ask. |
| "Handling more inputs is more robust" | Unverifiable handling is guessing. Refusal with guidance is robust. |
| "Refusing looks lazy" | Refusal with exact guidance is the contract working. |
| "A warning makes the assumption visible, so proceeding is fine" | Visibility is not permission. Warn-and-proceed on unverifiable input is still guessing. Refuse with the exact fix. |
| "We asked clarifying questions — scope is covered" | Questions in chat evaporate with the session. Write the contract artifact; the next session cannot check changes against a conversation. |

## Red flags — STOP

- About to handle an input the contract doesn't name
- Adding a severity/priority/validation rule you can't trace to a principle in one sentence
- "While I'm here..."
- Writing fallback/guess logic for unverifiable input
- Amending scope in code instead of in the contract
- Padding or defaulting missing parts of an input ("1.2" → "1.2.0") instead of refusing
- Scope decisions living only in chat, with no artifact a later session can check

## Integration

- With superpowers:brainstorming: the contract becomes the spec's `## Scope Contract` section.
- With superpowers:writing-plans: check each plan task against the contract before execution.
- Resuming work in any session: read PRINCIPLES.md and the feature's contract before proposing changes.
