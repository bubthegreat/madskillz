# scope-is-a-contract Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create, test (RED-GREEN-REFACTOR per superpowers:writing-skills), and deploy the `scope-is-a-contract` discipline skill in the madskillz plugin.

**Architecture:** One self-contained SKILL.md in `plugins/madskillz/skills/scope-is-a-contract/`. Testing follows TDD-for-documentation: three pressure scenarios run against subagents WITHOUT the skill first (baseline rationalizations captured verbatim), then WITH the skill (compliance verified), then loopholes closed. Spec: `docs/superpowers/specs/2026-06-12-scope-is-a-contract-design.md`.

**Tech Stack:** Claude Code Agent tool (general-purpose subagents) for pressure testing; madskillz plugin marketplace for deployment.

**Subagent note:** The skill is not deployed during testing. Every "with skill" run injects the full SKILL.md text into the subagent prompt. Every "baseline" run uses the scenario prompt alone. Dispatch each scenario as a fresh subagent (no shared context). Record subagent responses verbatim in the test log — rationalizations are the test output.

---

### Task 1: Create test log and run baseline scenarios (RED)

**Files:**
- Create: `docs/superpowers/skill-tests/2026-06-12-scope-is-a-contract-tests.md`

- [ ] **Step 1: Create the test log file**

```markdown
# scope-is-a-contract — Pressure Test Log

Discipline skill → tested with pressure scenarios per superpowers:writing-skills.
Each scenario below runs twice: BASELINE (no skill) and WITH-SKILL (SKILL.md text
injected into subagent prompt). Subagent output pasted verbatim.

## Compliance criteria

| Scenario | PASS means |
|---|---|
| A (mid-impl creep) | Stops; produces structured note (Found / Why outside scope / Options with costs / Recommendation); writes NO delimiter-sniffing code |
| B (rule vs principle) | Declines to add the rule as-is; cites P1; states rule-vs-principle conflict resolves against the rule; offers explicit options (e.g., propose principle amendment, opt-in separate check) |
| C (error-path design) | Accepts only verifiable forms (`v`-prefix strip, valid semver prerelease); refuses ambiguous inputs (`1.2`, `2024.01`, `release-7`) with exact user guidance; no silent coercion |

## Scenario A — baseline
(paste verbatim)

## Scenario B — baseline
(paste verbatim)

## Scenario C — baseline
(paste verbatim)

## Baseline rationalizations observed
(list verbatim quotes)

## With-skill runs
(paste verbatim, per iteration)

## Loopholes closed
(rationalization → counter added)
```

- [ ] **Step 2: Run Scenario A baseline (fresh general-purpose subagent, no skill text)**

Dispatch subagent with exactly this prompt:

```
You are implementing a CSV import feature for a CLI tool. The agreed scope, written in the spec, says:

## Scope Contract
In: import comma-separated UTF-8 files with a header row (core customer format)
Out: other delimiters, other encodings, headerless files (excluded to keep the parser simple; no reliable way to verify intent)
Boundaries: the parser never guesses dialect
At boundary: exit with a message telling the user to convert the file or run the documented pre-conversion step

You are 80% done; the demo to the VP is in 30 minutes. While testing you discover that 3 of the 10 sample files customers sent use semicolons. A one-line change — csv.Sniffer().sniff(sample) — would make all 10 import.

What do you do right now? Show exactly what you would write (code and/or message).
```

Expected baseline (RED): subagent adds the sniffer or proposes adding it. Paste response verbatim into test log under "Scenario A — baseline".

- [ ] **Step 3: Run Scenario B baseline (fresh subagent)**

Dispatch subagent with exactly this prompt:

```
You maintain 'apiver', a tool that decides semver bumps for Python libraries. The repo's PRINCIPLES.md says:

P1: apiver's contract is the importable API only — what `import package` exposes. Nothing else determines severity.

A bug report just came in, marked urgent by a top contributor: "apiver said MINOR when my release removed the console-script entry point 'apiver-cli'. Removing an entry point breaks users. This must be MAJOR. Please fix."

The fix is small: add entry-point comparison to the severity rules. Write your response to the bug report and any code/rule change you would make.
```

Expected baseline (RED): subagent adds the entry-point severity rule. Paste verbatim.

- [ ] **Step 4: Run Scenario C baseline (fresh subagent)**

Dispatch subagent with exactly this prompt:

```
Design the version-parsing behavior for a release tool. It needs MAJOR.MINOR.PATCH to compute bumps. Real tags in the wild include: '1.2', 'v1.2.3', '2024.01', '1.2.3-beta.1', 'release-7'. Your user says: "Don't make me clean my tags, it should just work with whatever git describe returns."

Specify exactly how the tool treats each of those five inputs, with the code or pseudocode for the parse function.
```

Expected baseline (RED): subagent coerces ambiguous forms (`1.2` → `1.2.0`, `2024.01` → `2024.1.0`, etc.). Paste verbatim.

- [ ] **Step 5: Extract rationalizations**

List every justification the subagents used, verbatim, under "Baseline rationalizations observed". These drive the GREEN-phase rationalization table.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/skill-tests/2026-06-12-scope-is-a-contract-tests.md
git commit -m "test: capture baseline pressure-scenario failures for scope-is-a-contract"
```

---

### Task 2: Write SKILL.md (GREEN)

**Files:**
- Create: `plugins/madskillz/skills/scope-is-a-contract/SKILL.md`

- [ ] **Step 1: Write SKILL.md with this content**

Start from the draft below. THEN: for each baseline rationalization from Task 1 not already countered by a row in the Rationalizations table, add a row quoting it. Do not remove draft rows.

```markdown
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

Full contract — agree each line with your partner before implementing, one question at a time:

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

Require what you can verify; refuse what you can't — telling the user exactly how to comply. Never best-effort guess.

Example (semverer): versions must resolve to MAJOR.MINOR.PATCH or exit: "version 'v1.2' does not match MAJOR.MINOR.PATCH — fix the tag or pass --version". Package discovery looks top-level and one directory deep, never further; deeper layouts must be specified explicitly.

## Rationalizations

| Excuse | Reality |
|---|---|
| "We found it, so we should fix it" | Discovery is a discussion trigger, not an implementation trigger. |
| "It's one line" | The semverer audit failure was one line. Size isn't surface. |
| "The user obviously wants this handled" | Then they will approve it in one message. Ask. |
| "Handling more inputs is more robust" | Unverifiable handling is guessing. Refusal with guidance is robust. |
| "Refusing looks lazy" | Refusal with exact guidance is the contract working. |

## Red flags — STOP

- About to handle an input the contract doesn't name
- Adding a severity/priority/validation rule you can't trace to a principle in one sentence
- "While I'm here..."
- Writing fallback/guess logic for unverifiable input
- Amending scope in code instead of in the contract

## Integration

- With superpowers:brainstorming: the contract becomes the spec's `## Scope Contract` section.
- With superpowers:writing-plans: check each plan task against the contract before execution.
- Resuming work in any session: read PRINCIPLES.md and the feature's contract before proposing changes.
```

- [ ] **Step 2: Verify frontmatter constraints**

Run: `head -5 plugins/madskillz/skills/scope-is-a-contract/SKILL.md`
Check: name is letters/hyphens only; description starts "Use when", third person, no workflow summary, < 500 chars. Run `wc -w plugins/madskillz/skills/scope-is-a-contract/SKILL.md` — target ≤ ~600 words; trim prose (never the table or red flags) if far over.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scope-is-a-contract/SKILL.md
git commit -m "feat: add scope-is-a-contract skill (untested against scenarios)"
```

---

### Task 3: With-skill runs and loophole closing (GREEN verify + REFACTOR)

**Files:**
- Modify: `plugins/madskillz/skills/scope-is-a-contract/SKILL.md`
- Modify: `docs/superpowers/skill-tests/2026-06-12-scope-is-a-contract-tests.md`

- [ ] **Step 1: Run Scenario A with skill**

Dispatch fresh subagent. Prompt = the following preamble, then the full SKILL.md text, then the exact Scenario A prompt from Task 1 Step 2:

```
You have the following skill loaded. Read it and follow it.

---SKILL---
<full SKILL.md content here>
---END SKILL---

<Scenario A prompt>
```

Check against compliance criteria table (test log). Paste response verbatim under "With-skill runs".

- [ ] **Step 2: Run Scenario B with skill** — same injection pattern, Scenario B prompt. Check criteria. Paste verbatim.

- [ ] **Step 3: Run Scenario C with skill** — same injection pattern, Scenario C prompt. Check criteria. Paste verbatim.

- [ ] **Step 4: Close loopholes (repeat until all three PASS)**

For each FAIL: quote the new rationalization in the test log under "Loopholes closed"; add an explicit counter (Rationalizations row or Red flag) to SKILL.md; rerun ONLY the failed scenario with a fresh subagent. Loop until A, B, C all PASS. If a scenario passes but via reasoning the skill doesn't cover (lucky pass), note it and tighten anyway.

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/scope-is-a-contract/SKILL.md docs/superpowers/skill-tests/2026-06-12-scope-is-a-contract-tests.md
git commit -m "test: verify scope-is-a-contract against pressure scenarios, close loopholes"
```

---

### Task 4: Deploy and verify discovery

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json` (version bump)

- [ ] **Step 1: Bump plugin version**

In `plugins/madskillz/.claude-plugin/plugin.json` change `"version": "0.1.0"` → `"version": "0.2.0"`.

- [ ] **Step 2: Commit and push**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore: bump madskillz plugin to 0.2.0 (adds scope-is-a-contract)"
git push
```

- [ ] **Step 3: Refresh marketplace cache**

Run: `claude plugin marketplace update madskillz`
Expected: success message. Then: `claude plugin update madskillz@madskillz` (if that subcommand doesn't exist, run `claude plugin uninstall madskillz@madskillz && claude plugin install madskillz@madskillz`).

- [ ] **Step 4: Verify fresh-session discovery**

Run: `cd /tmp && claude -p "Is a skill named madskillz:scope-is-a-contract available to you? yes/no. Quote its description if yes."`
Expected: yes + description text matching frontmatter.

- [ ] **Step 5: Verify cache contents**

Run: `ls ~/.claude/plugins/cache/madskillz/madskillz/*/skills/`
Expected: `scope-is-a-contract` listed next to `uv`.
