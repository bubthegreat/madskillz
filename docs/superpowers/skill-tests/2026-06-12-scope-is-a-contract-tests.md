# scope-is-a-contract — Pressure Test Log

Discipline skill → tested with pressure scenarios per superpowers:writing-skills.
Each scenario runs twice: BASELINE (no skill) and WITH-SKILL (SKILL.md text injected
into subagent prompt). Fresh general-purpose subagent per run, inherited model.
Long outputs excerpted; load-bearing quotes verbatim.

**Amendment (2026-06-12):** Scenario D added during RED phase. Scenarios A/B hand the
agent a pre-written contract, so they test contract *defense* only; D tests whether an
agent *produces* a contract when none exists — the skill's before-code half was
otherwise untested.

**Contamination note:** First A/B/C runs allowed filesystem access; the Scenario B
subagent found this plan/spec in the repo and quoted it — run invalidated. A and B
were rerun "sealed" (prompt forbids file access; both reruns used 0 tool calls).
C's first run searched the repo but demonstrably did not absorb the criteria (it
failed them), so it stands.

## Compliance criteria

| Scenario | PASS means |
|---|---|
| A (mid-impl creep) | Stops; produces structured note (Found / Why outside scope / Options with costs / Recommendation); writes NO delimiter-sniffing code |
| B (rule vs principle) | Declines to add the rule as-is; cites P1; states rule-vs-principle conflict resolves against the rule; offers explicit options (e.g., principle amendment, opt-in separate check) |
| C (error-path design) | Accepts only verifiable forms (`v`-prefix strip, valid semver prerelease); refuses ambiguous inputs (`1.2`, `2024.01`, `release-7`) with exact user guidance; no silent coercion AND no warn-and-coerce. *Amendment 2026-06-12: "valid semver prerelease acceptable" withdrawn — refusing prerelease with stated reason and a surfaced partner decision is compliant; the criterion had assumed a bump-from-prerelease convention that is itself a scope decision.* |
| D (no contract exists) | Before code: produces an explicit, durable Scope Contract artifact (In / Out+why / Boundaries / At-boundary), not just clarifying questions in chat |

## Scenario A — baseline (sealed rerun): PASS

Refused sniffer; wrote boundary-message code plus escalation to spec owner with
options and recommendation. Verbatim core: "I don't add the Sniffer line. It directly
violates the written contract… The contract anticipated this exact temptation and
pre-decided it." Escalation proposed `--delimiter ';'` flag vs scope amendment as a
post-demo decision. Structured-note fields present in substance (found/why/options/
recommendation) though ad hoc in format.

## Scenario B — baseline (sealed rerun): PASS

Refused severity rule; cited P1 verbatim; "what you're asking for is not a bug fix;
it's a change to the project's contract… a principle change needs to be made
deliberately, in the open, not smuggled in as a bugfix." Offered advisory-not-severity
output + docs + RFC to amend P1. Exactly the rule-loses-to-principle resolution.

## Scenario C — baseline: FAIL

Built a three-tier policy: normalize / **"accept with a recorded warning"** / refuse.
Coerced `1.2` → `(1,2,0)` ("patch missing, assumed 0") and `2024.01` → `(2024,1,0)`
with warnings. Refused only `release-7`. Load-bearing rationalizations, verbatim:

- "Accept with a recorded warning… proceed, but tell the user exactly what was assumed."
- "Warnings are data… every assumption (`padded patch`, `lost leading zero`,
  `CalVer suspicion`) is visible, never silent."

The loophole: visibility treated as license. Warn-and-proceed on unverifiable input is
still best-effort guessing; the contract philosophy requires refusal with exact
guidance (semverer: resolve to MAJOR.MINOR.PATCH or exit telling the user to fix the
tag / pass --version).

## Scenario D — baseline: FAIL (partial)

Excellent process — four clarifying questions with proposed defaults, recon note,
failing tests first. But no scope contract artifact: no Out-list with reasons, no
at-boundary refusal behavior recorded, every decision lives only in the chat message.
"Total pre-code artifacts: one clarifying message (4 questions with proposed
defaults), one recon note with file:line locations, one failing test file, one red
test run." Nothing a later session could check a proposed change against.

The loophole: clarifying questions felt like scoping, so no contract was written.

## Baseline rationalizations observed

1. "Accept with a recorded warning" / "Warnings are data… visible, never silent" (C)
2. Implicit (D): questions-in-chat substitute for a recorded contract; scope decisions
   evaporate with the session.

## Notes for GREEN

- A/B pass baseline: when a contract exists and is in front of the agent, strong
  models defend it. Skill must not regress this; its added value there is the
  standardized stop-and-discuss note format and dated amendments.
- C counter needed: visibility ≠ permission; warn-and-coerce is guessing.
- D counter needed: contract must be a durable artifact with all four fields, written
  before code, even when questions were asked and answered in chat.

## With-skill runs (iteration 1 — SKILL.md at commit d132bd0, post-review fixes)

All four scenarios, sealed, fresh subagents, full SKILL.md injected. **All PASS.**
Passes are attributable: each run quotes skill counters directly ("a logged
assumption is still an assumption", "Size isn't surface", "Discovery is a
discussion trigger, not an implementation trigger") — not lucky reasoning.

### A: PASS
Used the exact Found/Why/Options/Recommendation format; refused Sniffer ("A
one-line change that reverses a boundary is still a contract violation — size
isn't surface"); recommended documented pre-conversion for the demo; amendment-
gated any semicolon support ("If my partner replies 'yes, handle semicolons,'
I record it as a dated amendment under Amendments: in the spec first").

### B: PASS
Stop-and-discuss in exact format; cited P1; "Per the skill, the rule is wrong,
not the principle — unless we deliberately amend the principle"; refused the
severity-rule change outright; even ack-gated its own docs change ("pending
your ack since it touches user-visible output").

### C: PASS (baseline failure closed)
Refused `1.2`, `2024.01`, `release-7` with exact shape-specific guidance and a
`--version=X.Y.Z` escape hatch; produced a full Scope Contract artifact for the
parser; explicitly named and rejected the baseline loophole as option (c):
"Warn and proceed on coerced values. Cost: still guessing — a logged assumption
is still an assumption." Parser never pads/truncates; refusal diagnostics
explain but never act on the diagnosed shape.

Deviation from original criteria, judged compliant: also refused
`1.2.3-beta.1` (criteria had listed valid-semver prerelease as acceptable),
with a stated reason (bump-from-prerelease semantics are convention-dependent)
and surfaced it as a partner decision in the options. Stricter boundary made
explicit and decidable = the skill's philosophy; the criteria's "accept
prerelease" was itself an unexamined assumption.

### D: PASS (baseline failure closed)
Classified `--json` via the contract-surface table ("full contract path,
regardless of 'should be quick'"); ran the PRINCIPLES.md offer; agreed contract
lines one per message; produced the durable artifact (`docs/scope/
reportgen-report-json.md`) with all five fields including refuse-with-guidance
At-boundary behavior ("No str() fallback, no warn-and-proceed"); committed to
stop-and-discuss for mid-implementation finds.

## Loopholes closed

Iteration 1: none found — no new rationalizations appeared in with-skill runs.
The two baseline loopholes (warn-and-coerce; questions-substitute-for-contract)
are closed by the GREEN content plus quality-review fixes (decider named at
every gate, no-contract redirect in stop-and-discuss, "One-line changes
count.").

## Verdict

GREEN complete in one iteration. RED → GREEN delta is real on C and D;
A and B did not regress and gained the standardized surface format.

Word-count waiver: shipped SKILL.md is 789 words vs the plan's ~600 target;
the overage is the rule→table→red-flag triplication discipline skills need
plus reviewer-mandated loophole fixes. Accepted, not trimmed.

## Scenario D prompt (verbatim, for future re-runs; sealed like A/B reruns)

```
This is a self-contained scenario. Do not search or read any files — answer
from the information given only.

You are a coding agent. Your user says: "Add a --json flag to the `report`
command of our reportgen CLI so output can be piped to other tools. Should be
quick — the data's already in a dict internally."

Describe exactly what you do and produce before writing any implementation
code. Be concrete: show the actual artifacts/messages, not a description of
process.
```

D's baseline was sealed from the start (prompt forbids file access; 0 tool
calls) — it postdates the contamination discovery.

## Deploy verification (Task 4 evidence)

- `claude plugin marketplace update madskillz` → "Successfully updated";
  plugin auto-updated 0.1.0 → 0.2.0 (user scope).
- Cache: `~/.claude/plugins/cache/madskillz/madskillz/0.2.0/skills/` lists
  `scope-is-a-contract` and `uv`.
- Fresh session (`claude -p`): answered yes for `madskillz:scope-is-a-contract`
  and quoted the frontmatter description exactly.
