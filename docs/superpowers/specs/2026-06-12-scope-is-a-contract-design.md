# scope-is-a-contract — Skill Design

**Date:** 2026-06-12
**Status:** Approved
**Home:** `plugins/madskillz/skills/scope-is-a-contract/SKILL.md`

## Problem

Scope creep arrives looking small and reasonable: an edge case found mid-implementation,
a bug report, a "while I'm here". Absorbed silently, these accrete until secondary
features redefine primary design. Concrete failure (semverer): a bug report about the
audit command led to severity rules that contradicted the tool's declared contract —
entry-point removal became "major" when the contract was the importable API only.
The fix required writing PRINCIPLES.md and walking the rules back.

The skill encodes: scope is a contract agreed before code, defended during code.

## Core principles the skill encodes

1. **Scope is a contract, agreed before code.** In-scope, out-of-scope, and boundaries
   are defined explicitly before implementation. The out-of-scope list is as
   load-bearing as the in-scope list — it is what makes KISS/DRY/YAGNI applicable.
2. **Bounded scope over best-effort guessing.** Require what you can verify; refuse
   what you can't, with guidance telling the user how to comply. (semverer: versions
   must resolve to MAJOR.MINOR.PATCH or exit gracefully telling the user to comply
   with the spec; package discovery looks top-level and one directory deep, never
   further — deeper layouts must be explicitly specified.)
3. **Edge cases found mid-implementation are discussion triggers, not implementation
   triggers.** Scope grows only by deliberate, approved decision — never by accreting
   edge cases.
4. **Secondary features never redefine primary design.** Any proposed rule/behavior
   must trace to an agreed principle. When rule and principle conflict, the rule is
   wrong, not the principle.
5. **A decision must be explainable in one sentence pointing at one principle.**
   When two designs detect/do the same thing, the one with less machinery wins.

Anti-loophole line, stated early in the skill: violating the letter of the contract
is violating its spirit.

## Decisions made

| Question | Decision |
|---|---|
| Relation to superpowers:brainstorming | Complement. This skill owns the scope contract artifact + mid-implementation enforcement; brainstorming keeps owning the design dialogue. Cross-referenced by name only (no `@` force-loads). |
| Trigger | Hybrid: auto-fires at feature-work start, on mid-implementation creep symptoms ("found an edge case", "should also handle", "while I'm here", bug-report-driven rule changes, error-path design), and by manual invoke. |
| Artifact | Two-level. `PRINCIPLES.md` at repo root = durable project contract (core purpose in one sentence, named principles P1..Pn, global boundaries). Per-feature scope contract = short fixed template as `## Scope Contract` section in the feature's spec doc (`docs/superpowers/specs/...`); standalone `docs/scope/<feature>.md` when no spec doc exists. |
| Lightweight path | Contract-surface test. Touches public API / user-visible behavior / error paths / new inputs → full contract. Internal-only (bugfix within agreed scope, rename, refactor, docs) → one-sentence inline scope statement acked in chat, no artifact. Stop-and-discuss stays armed on both paths. |
| PRINCIPLES.md creation | Offer on first full-contract feature in a repo lacking it. Declined → the scope contract carries its own core-purpose line so rule-tracing still works. No root files forced into team repos. |
| Structure | One skill, all content inline (~500 words). No supporting files: template is ~10 lines; a case-study file would be the narrative anti-pattern. |

## Skill content (sections)

1. **Frontmatter** — name `scope-is-a-contract`; description is trigger-only (no
   workflow summary, per CSO):
   > Use when starting feature work, designing error paths or input validation, and
   > when mid-implementation an unhandled edge case, a bug report, "should also
   > handle", or "while I'm here" tempts adding behavior beyond agreed scope.
2. **Overview** — core principle + letter-is-spirit line.
3. **Lightweight path** — contract-surface test (above), so the skill is not
   bureaucracy for small changes.
4. **Scope contract template** (inline):
   ```
   ## Scope Contract
   In: <what this feature handles> (why)
   Out: <what it deliberately does not handle> (why excluded)
   Boundaries: <the lines that keep the design simple>
   At boundary: <exact refusal behavior + guidance text>
   Amendments: <dated, approved scope changes>
   ```
5. **PRINCIPLES.md protocol** — check root; offer-if-missing; decline fallback;
   every rule cites a principle in one sentence; conflict → rule is wrong;
   equal detection → less machinery wins.
6. **Stop-and-discuss protocol** — out-of-contract edge case → STOP coding; surface
   structured note: **Found / Why outside scope / Options with costs /
   Recommendation**; proceed only on explicit decision; record decision as dated
   amendment in the contract. Never absorb silently, including "one-liners".
7. **Refuse-with-guidance vs silent-absorb** — error-path design test with the
   semverer example inline (version spec compliance; bounded discovery depth).
8. **Rationalization table + red flags** — populated from RED-phase baseline
   testing, not invented. Anticipated entries: "we found it, so fix it", "it's one
   line", "user obviously wants this handled", "handling more is more robust",
   "refusing looks lazy".
9. **Integration** — cross-references: superpowers:brainstorming (contract becomes a
   spec section), superpowers:writing-plans (plan tasks checked against contract).
   Later sessions read PRINCIPLES.md + the feature's contract before proposing
   changes.

## Testing plan (writing-skills Iron Law: no skill without failing test first)

Discipline-enforcing skill → pressure-scenario testing with subagents.

**RED (baseline, no skill):**
- (a) Mid-implementation edge case + sunk cost + time pressure — does the agent
  silently absorb it into the code?
- (b) Bug report pushing a rule that contradicts the project's declared core purpose
  (semverer audit re-enactment) — does the agent add the rule?
- (c) Error-path design task — does the agent best-effort guess instead of
  refuse-with-guidance?

Capture rationalizations verbatim.

**GREEN:** write SKILL.md countering the observed rationalizations specifically;
rerun the same scenarios; agents must comply.

**REFACTOR:** close any new rationalizations with explicit counters; finalize
rationalization table and red-flags list; re-test until bulletproof.

**Deploy:** commit to madskillz, push, `/plugin marketplace update madskillz`;
verify skill appears in fresh session skill list with `madskillz:` namespace.

## Out of scope (for this skill)

- No changes to superpowers skills themselves.
- No hooks/mechanical enforcement — this is a judgment-call discipline skill;
  if a rule later proves regex-enforceable, automate it then.
- No project-specific conventions baked in (those belong in each repo's
  PRINCIPLES.md / CLAUDE.md).
