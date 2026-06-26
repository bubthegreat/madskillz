# 10th-Grade Reading Level for the Scientific-Research Family — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recalibrate the `scientific-*` research family's reader-facing prose from "adjacent-field researcher / educated-generalist floor" to a ~10th-grade general reader by default (overridable for explicitly specialist studies), without weakening correctness or integrity.

**Architecture:** One new canonical reference — `scientific-peer-review/references/expected-reader.md` — defines the reading level, craft rules, and specialist override. Every reader-facing surface (the writer in `scientific-study`, the readability-tier reviewers in `scientific-peer-review`, and `ask-an-expert`'s direct-answer path) points at it, so the prose and the bar that judges it cannot drift apart. This mirrors the family's existing shared-contract pattern (every reviewer is already dispatched with `review-report-format.md`).

**Tech Stack:** Markdown skill files (Claude Code plugin). No code/build/test runner; verification is grep/read assertions and `json.tool` validity checks. Evals are skill-creator JSON specs.

## Global Constraints

- Working dir / branch: this worktree `.claude/worktrees/scientific-research-10th-grade-reading-level`, branch `worktree-scientific-research-10th-grade-reading-level`, off `origin/main`. Run all commands from the worktree root.
- House default audience: **~10th-grade general reader** (age ~15–16, no specialist background).
- **Never trade correctness for plainness** — define the precise term, never delete it. Readability defers to correctness in every conflict.
- **Invariants — do NOT change:** the readability severity model (normally `minor`, `major` only for the enumerated completeness/abstract cases, **never `blocker`**); the integrity stance; expert **persona internals** (`experts/*.md`); the expert **panel-reviewer report shape**.
- Cross-skill reference paths are written skill-name-rooted, **no `../`** (family convention), e.g. `scientific-peer-review/references/expected-reader.md`.
- Version: bump `plugins/madskillz/.claude-plugin/plugin.json` `0.13.0 → 0.14.0` (last task).
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Do **not** push or open the PR until all tasks pass and the finishing step runs.

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `plugins/madskillz/skills/scientific-peer-review/references/expected-reader.md` | **Create** | Canonical reading-level standard: band + craft rules + override + defer-to-correctness |
| `plugins/madskillz/skills/scientific-peer-review/SKILL.md` | Modify | Dispatch readability tier with `expected-reader.md`; note calibration at tier intro |
| `plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md` | Modify | Point "expected reader" at shared file; delete the p-value/CI "needs no explanation" assumption |
| `plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md` | Modify | Point "expected reader" at shared file |
| `plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md` | Modify | "accessibly" now resolves to the shared band |
| `plugins/madskillz/skills/scientific-study/SKILL.md` | Modify | Writer targets shared standard; record specialist-audience override in framing (Step 1) |
| `plugins/madskillz/skills/scientific-study/references/repo-layout.md` | Modify | Manuscript-audience paragraph points at shared standard |
| `plugins/madskillz/skills/ask-an-expert/SKILL.md` | Modify | Direct-answer path defaults to ~10th grade with specialist override |
| `plugins/madskillz/commands/research.md` | Modify | One line stating the house default |
| `plugins/madskillz/skills/scientific-peer-review/evals/evals.json` | Modify | New eval: undefined standard concept flagged for default-audience draft |
| `plugins/madskillz/skills/scientific-study/evals/evals.json` | Modify | New eval: abstract followable by general reader; standard concepts defined |
| `plugins/madskillz/.claude-plugin/plugin.json` | Modify | Version `0.13.0 → 0.14.0` |
| `~/.claude/projects/-home-bub-Development-madskillz/memory/user-background.md` + `MEMORY.md` | Modify (non-repo) | Decouple owner profile from the research family's "expected reader" |

---

### Task 1: Create the canonical `expected-reader.md`

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/expected-reader.md`

**Interfaces:**
- Produces: a reference file at the exact path above. Tasks 2–4 reference it by the skill-name-rooted path `scientific-peer-review/references/expected-reader.md`; the readability rubrics receive it as "provided with this rubric."

- [ ] **Step 1: Write the file** with exactly this content:

```markdown
# The expected reader (reading-level standard)

The single source of truth for **who the research family writes for** and **how plainly**. The
writer (`scientific-study`), the readability-tier reviewers, and `ask-an-expert`'s direct answers
all calibrate to this file, so the prose and the bar that judges it never drift apart.

## House default — a ~10th-grade general reader

Write so a motivated **general reader at about a 10th-grade reading level** (age ~15–16, no
specialist background) can follow **what was asked, what was done, what was found, and why it
matters** — from the paper alone.

This **never trades correctness for plainness.** Where a plain word would lose real meaning, keep
the precise term and **define it on first use; never delete it.** Plainness is about *framing* a
hard idea so it lands, not about removing it.

## What this changes versus writing for a peer

Do **not** assume general scientific literacy. Concepts a working scientist knows cold —
**p-value, confidence interval, control group, statistical significance, regression, effect
size**, and the like — are themselves **defined in plain language on first use** and carried in the
**Glossary**. The 10th-grade reader has not met them; "standard scientific concepts" are not
exempt.

Craft rules:

- **Short sentences; one idea each.** Prefer common words over rare ones; active voice.
- **Define before you lean on it.** Every acronym is spelled out on first use; every symbol is
  named in words.
- **The abstract is the true plain-language summary.** A reader at this level gets the whole story
  from the abstract alone — there is no separate lay summary.
- **Ground abstractions in the concrete.** Use a short everyday example or analogy for each
  genuinely abstract idea, then connect it back to the precise term.

## Override — a deliberately specialist audience

A study written **on purpose** for a specialist audience may calibrate up — but only when it
**says so explicitly in its framing**, using the same honest-context discipline that marks a
replication/validation study. When the manuscript declares a specialist intended audience, the
writer **and** the reviewers calibrate to that declared audience instead of the default.

Absent an explicit declaration, **the 10th-grade default applies.** The override **raises the
assumed-knowledge bar only — it never lowers the correctness or integrity bar**, and the
Acronyms/Glossary machinery still applies in full.

## Defer to correctness (unchanged)

A readability suggestion must never reduce precision or override a correctness finding. When
plainness and precision conflict, reframe as "**define the term**," and surface the disagreement to
the meta-editor rather than overriding a correctness reviewer.
```

- [ ] **Step 2: Verify the file exists with the key content**

Run: `grep -c "10th-grade" plugins/madskillz/skills/scientific-peer-review/references/expected-reader.md`
Expected: `≥ 3`

Run: `grep -l "Override — a deliberately specialist audience" plugins/madskillz/skills/scientific-peer-review/references/expected-reader.md`
Expected: the path prints (override section present)

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/expected-reader.md
git commit -m "feat(scientific-peer-review): add expected-reader.md reading-level standard (~10th grade default)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Recalibrate the peer-review readability tier

Wires the readability tier to the shared standard: dispatch the file, point the three rubrics at it, and delete the obsolete "reader already knows what a p-value is" assumption.

**Files:**
- Modify: `plugins/madskillz/skills/scientific-peer-review/SKILL.md`
- Modify: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md`
- Modify: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md`
- Modify: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md`

**Interfaces:**
- Consumes: `scientific-peer-review/references/expected-reader.md` (Task 1).

- [ ] **Step 1: SKILL.md — note the calibration at the readability-tier intro.** Replace:

```
**Readability tier (always, for reader-facing drafts):**
```

with:

```
**Readability tier (always, for reader-facing drafts; calibrated to `references/expected-reader.md`):**
```

- [ ] **Step 2: SKILL.md — dispatch the readability tier with the standard.** Replace:

```
Dispatch each reviewer with its own rubric file **and** `references/review-report-format.md`, and
have it return that shape — listing the inputs it had and any checks it skipped. The rubrics carry
only their unique checks and severity rules; this shared output contract is stated once here rather
than repeated in each.
```

with:

```
Dispatch each reviewer with its own rubric file **and** `references/review-report-format.md`, and
have it return that shape — listing the inputs it had and any checks it skipped. Dispatch the
**readability-tier** reviewers (plain-language, terminology & acronym, accessibility / background)
with `references/expected-reader.md` as well — it defines the reading level they judge against. The
rubrics carry only their unique checks and severity rules; these shared contracts are stated once
here rather than repeated in each.
```

- [ ] **Step 3: plain-language.md — point at the standard and drop the p-value assumption.** Replace the whole block:

```
## The expected reader
Calibrate to an **adjacent-field researcher** reading the body, with an **educated-generalist
floor**: general scientific literacy (reads a methods section, knows what a p-value and a
confidence interval are, understands basic experimental design) but NOT a specialist in this
subfield. Standard scientific concepts need no explanation; subfield-specific jargon must be
defined or replaced.
```

with:

```
## The expected reader
Calibrate to the reading-level standard in `expected-reader.md` (provided with this rubric): the
**house default is a ~10th-grade general reader** with no specialist background, unless the
manuscript explicitly declares a specialist intended audience — then calibrate to that declared
audience. Do **not** assume general scientific literacy: standard concepts (p-value, confidence
interval, basic experimental design) must themselves be defined in plain language on first use, not
presumed. Where plainness and precision conflict, ask the authors to *define* the term, never to
delete it.
```

- [ ] **Step 4: accessibility-background.md — point at the standard.** Replace the whole block:

```
## The expected reader
An adjacent-field researcher with an educated-generalist floor (general scientific literacy, not a
subfield specialist). The reader navigates the body with the help of the abstract, the Glossary,
the Acronyms index, and any Background / further-reading pointers.
```

with:

```
## The expected reader
The reading-level standard in `expected-reader.md` (provided with this rubric): by default a
~10th-grade general reader with no specialist background, unless the manuscript explicitly declares
a specialist intended audience. The reader navigates the body with the help of the abstract, the
Glossary, the Acronyms index, and any Background / further-reading pointers — so more concepts need
a definition or a pointer here than a specialist draft would require.
```

- [ ] **Step 5: terminology-acronyms.md — resolve "accessibly" to the band.** Replace:

```
- **Glossary (both directions):** every specialized term used in the body is present in the
  **Glossary**, defined accessibly for the expected reader; every glossary entry is actually used.
```

with:

```
- **Glossary (both directions):** every specialized term used in the body is present in the
  **Glossary**, defined accessibly for the expected reader — the ~10th-grade default in
  `expected-reader.md` (provided with this rubric) unless the manuscript declares a specialist
  audience; every glossary entry is actually used.
```

- [ ] **Step 6: Verify the recalibration landed and the stale assumption is gone**

Run: `grep -rn "knows what a p-value\|educated-generalist floor\|adjacent-field researcher" plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md`
Expected: **no matches** (exit code 1)

Run: `grep -rln "expected-reader.md" plugins/madskillz/skills/scientific-peer-review/SKILL.md plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md`
Expected: all four paths print

- [ ] **Step 7: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/SKILL.md plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md
git commit -m "feat(scientific-peer-review): readability tier calibrates to ~10th-grade expected-reader.md

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Recalibrate the writer (`scientific-study`)

The writer now targets the shared standard, and Step 1 records a specialist-audience override when one is intended (same honest-context discipline as a replication study).

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/SKILL.md`
- Modify: `plugins/madskillz/skills/scientific-study/references/repo-layout.md`

**Interfaces:**
- Consumes: `scientific-peer-review/references/expected-reader.md` (Task 1), referenced by skill-name-rooted path.

- [ ] **Step 1: SKILL.md — add the audience/override note to Step 1 (framing).** Find this line (end of the novelty bullets, just before topic/slug setup):

```
Then establish the `<topic>` and a slugified `<research-short-name>` (propose a
```

Insert this paragraph immediately **before** that line:

```
**Audience.** The study is written for a **~10th-grade general reader** by default (see Step 2 and
`scientific-peer-review/references/expected-reader.md`). If it is deliberately aimed at a specialist
audience, record that intended audience as explicit context in the brief and the paper's framing —
the same honest-context discipline as a replication/validation study — so the drafting and the
review panel both calibrate to it.

```

- [ ] **Step 2: SKILL.md — point the Step 2 writing instruction at the standard.** Note this text wraps across two lines in the file; match it exactly (newline included). Replace:

```
Write for the expected reader (adjacent-field body,
educated-generalist floor): the abstract doubles as the plain-language summary,
```

with:

```
Write for the expected reader defined in `scientific-peer-review/references/expected-reader.md` — by default a **~10th-grade general reader** (no specialist background; standard concepts such as p-values are defined, not presumed), unless this study is deliberately framed for a specialist audience (see Step 1): the abstract doubles as the plain-language summary,
```

- [ ] **Step 3: repo-layout.md — point the manuscript-audience paragraph at the standard.** Replace:

```
The manuscript is written for an **adjacent-field researcher** with an **educated-generalist
floor** (general scientific literacy, not a subfield specialist). The **abstract** doubles as the
plain-language summary — a reader at that level grasps what was done and found from it alone. There
is no separate lay-summary section.
```

with:

```
The manuscript is written for the expected reader defined in
`scientific-peer-review/references/expected-reader.md` — by default a **~10th-grade general reader**
with no specialist background (standard concepts such as p-values are defined in plain language, not
presumed), unless the study explicitly declares a specialist intended audience. The **abstract**
doubles as the plain-language summary — a reader at that level grasps what was done and found from
it alone. There is no separate lay-summary section.
```

- [ ] **Step 4: Verify**

Run: `grep -rn "educated-generalist floor\|adjacent-field researcher\|adjacent-field body" plugins/madskillz/skills/scientific-study/`
Expected: **no matches** (exit code 1)

Run: `grep -c "expected-reader.md" plugins/madskillz/skills/scientific-study/SKILL.md plugins/madskillz/skills/scientific-study/references/repo-layout.md`
Expected: each file ≥ 1; and `grep -c "Audience\." .../SKILL.md` ≥ 1

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/SKILL.md plugins/madskillz/skills/scientific-study/references/repo-layout.md
git commit -m "feat(scientific-study): write for ~10th-grade reader by default; record specialist-audience override in framing

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: ask-an-expert direct answers + research command

**Files:**
- Modify: `plugins/madskillz/skills/ask-an-expert/SKILL.md`
- Modify: `plugins/madskillz/commands/research.md`

**Interfaces:**
- Consumes: `scientific-peer-review/references/expected-reader.md` (Task 1). Persona internals and the panel-reviewer report shape are untouched.

- [ ] **Step 1: ask-an-expert/SKILL.md — set the direct-answer reading level (Step 3 only).** Replace:

```
- **Answering directly:** a clear, sourced answer with stated confidence and any caveats.
```

with:

```
- **Answering directly:** a clear, sourced answer with stated confidence and any caveats, written for a **~10th-grade general reader** by default — define specialist terms in plain language (see `scientific-peer-review/references/expected-reader.md`) — unless the user is clearly asking at a specialist level or requests specialist depth, in which case match their level.
```

- [ ] **Step 2: research.md — state the house default.** Replace:

```
Study design, analysis, and reproducibility packaging will be routed from here as
they are added.
```

with:

```
Study design, analysis, and reproducibility packaging will be routed from here as
they are added.

Across the family, reader-facing output is written for a **~10th-grade general reader** by default —
broadly understandable without sacrificing correctness — and calibrates up only when a study is
deliberately framed for a specialist audience (see
`scientific-peer-review/references/expected-reader.md`).
```

- [ ] **Step 3: Verify**

Run: `grep -c "10th-grade general reader" plugins/madskillz/skills/ask-an-expert/SKILL.md plugins/madskillz/commands/research.md`
Expected: each ≥ 1

Run: `git diff --stat plugins/madskillz/skills/ask-an-expert/SKILL.md`
Expected: only the Step 3 answer line changed (persona internals / panel path untouched)

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/ask-an-expert/SKILL.md plugins/madskillz/commands/research.md
git commit -m "feat(ask-an-expert,research): direct answers default to ~10th-grade reader; state family house default

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Lock the recalibration with evals

Adds one eval on each side so the change can't silently regress. Match the existing object shape; do not invent a harness.

**Files:**
- Modify: `plugins/madskillz/skills/scientific-peer-review/evals/evals.json`
- Modify: `plugins/madskillz/skills/scientific-study/evals/evals.json`

- [ ] **Step 1: peer-review evals.json — add a test after the `readability-tier` test.** Insert this object immediately after the closing `}` of the `readability-tier` test object and before the `out-of-scope-rewrite` test object (mind the comma between objects):

```json
    {
      "id": "readability-10th-grade-default",
      "prompt": "Review this paper for readability. [draft attached: a general-audience study that uses \"p-value\", \"confidence interval\", and \"regression\" without ever defining them, and makes no specialist-audience declaration]",
      "should_trigger": true,
      "grading_criteria": [
        "Plain-language reviewer calibrates to the ~10th-grade general-reader default (per expected-reader.md), since no specialist audience is declared",
        "Flags the undefined standard concepts (p-value, confidence interval, regression) as needing a plain-language definition — does NOT treat them as presumable",
        "Findings stay no higher than major and defer to correctness; never blocker"
      ]
    },
```

- [ ] **Step 2: study evals.json — add a test after the `citation-provenance-conventions` test.** Insert this object immediately after the closing `}` of the `citation-provenance-conventions` test object and before the `no-trigger-control` test object (mind the comma):

```json
    {
      "id": "readability-10th-grade-default",
      "prompt": "Draft a paper on <topic> and get it ready to publish (general audience).",
      "should_trigger": true,
      "grading_criteria": [
        "Writes for a ~10th-grade general reader by default (per scientific-peer-review/references/expected-reader.md), without sacrificing correctness",
        "The abstract works as a plain-language summary a general reader can follow on its own",
        "Standard concepts (e.g. p-value, confidence interval) are defined in plain language on first use and carried in the Glossary, not presumed",
        "Calibrates up only if the study explicitly declares a specialist intended audience"
      ]
    },
```

- [ ] **Step 3: Verify both files are still valid JSON and contain the new test**

Run: `python3 -m json.tool plugins/madskillz/skills/scientific-peer-review/evals/evals.json > /dev/null && echo PEER_OK`
Expected: `PEER_OK`

Run: `python3 -m json.tool plugins/madskillz/skills/scientific-study/evals/evals.json > /dev/null && echo STUDY_OK`
Expected: `STUDY_OK`

Run: `grep -c "readability-10th-grade-default" plugins/madskillz/skills/scientific-peer-review/evals/evals.json plugins/madskillz/skills/scientific-study/evals/evals.json`
Expected: each `1`

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/evals/evals.json plugins/madskillz/skills/scientific-study/evals/evals.json
git commit -m "test(scientific-research): evals lock ~10th-grade default (undefined standard concepts flagged; abstract reader-followable)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Version bump

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json`

- [ ] **Step 1: Bump the version.** Replace:

```json
  "version": "0.13.0",
```

with:

```json
  "version": "0.14.0",
```

- [ ] **Step 2: Verify**

Run: `grep '"version"' plugins/madskillz/.claude-plugin/plugin.json`
Expected: `"version": "0.14.0",`

- [ ] **Step 3: Final straggler sweep — confirm no stale audience phrasing remains anywhere in scope**

Run: `grep -rn "educated-generalist\|adjacent-field\|knows what a p-value" plugins/madskillz/skills/scientific-study plugins/madskillz/skills/scientific-peer-review plugins/madskillz/skills/ask-an-expert plugins/madskillz/commands/research.md`
Expected: **no matches** (exit code 1). (`review-report-format.md`'s level-agnostic severity ceiling is fine and contains none of these strings.)

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore: bump madskillz to 0.14.0 (scientific-research writes for ~10th-grade reader by default)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Update the `user-background` memory (non-repo)

Decouple the owner's profile from the research family's "expected reader." These files live outside the repo — **this is a filesystem write, not a git commit.**

**Files:**
- Modify: `/home/bub/.claude/projects/-home-bub-Development-madskillz/memory/user-background.md`
- Modify: `/home/bub/.claude/projects/-home-bub-Development-madskillz/memory/MEMORY.md`

- [ ] **Step 1: user-background.md — update the frontmatter `description`.** Replace:

```
description: "The user's professional/educational background — the calibration target for \"expected reader\" in the research skills"
```

with:

```
description: "The user's professional/educational background. (As of 2026-06-25 the scientific-research skills default to a ~10th-grade reader, NOT this profile.)"
```

- [ ] **Step 2: user-background.md — replace the second (calibration) paragraph.** Replace:

```
This profile is the concrete stand-in for the "expected reader" the research skills' meta-editor calibrates against: a strong quantitative/technical generalist who is comfortable with stats, methods sections, and software/data, but is NOT a subfield specialist in arbitrary domains (physics, biology, etc.). Confirms the chosen reading standard — "adjacent-field body, generalist-accessible by design" — see [[research-readability-design]].
```

with:

```
Historically this profile was the concrete stand-in for the "expected reader" the scientific-research skills calibrated against. As of 2026-06-25 that family writes for a **~10th-grade general reader by default** (overridable only when a study explicitly declares a specialist audience) — see `scientific-peer-review/references/expected-reader.md` and [[research-readability-design]] — so the owner's profile is **no longer** that family's calibration target. It remains a useful description of who the owner is and how to pitch explanations to them directly.
```

- [ ] **Step 3: MEMORY.md — update the hook line.** Replace:

```
- [User background](user-background.md) — biomechanical engineer / systems+business analyst / MBA(data analytics); the "expected reader" calibration target
```

with:

```
- [User background](user-background.md) — biomechanical engineer / systems+business analyst / MBA(data analytics); research family now defaults to ~10th-grade reader (no longer calibrated to this profile)
```

- [ ] **Step 4: Verify**

Run: `grep -c "no longer" /home/bub/.claude/projects/-home-bub-Development-madskillz/memory/user-background.md`
Expected: `≥ 1`

(No git commit — memory files are outside the repo.)

---

## Closing — verify & open the PR

After Task 7, all in-repo work is committed on the worktree branch. Then:

1. **REQUIRED SUB-SKILL:** `superpowers:verification-before-completion` — run the full straggler sweep (Task 6 Step 3) and both `json.tool` checks, and confirm `git status` is clean and the branch contains the expected commits.
2. **REQUIRED SUB-SKILL:** `superpowers:finishing-a-development-branch` — push the branch and open the PR to `bubthegreat/madskillz` for human review. PR body summarizes: the recalibration to a ~10th-grade default, the single-source `expected-reader.md`, the specialist override, the untouched invariants, the evals, and the `0.14.0` bump. End the PR body with the 🤖 Generated-with line.

## Self-Review (completed during planning)

- **Spec coverage:** expected-reader.md (Task 1); study writer + override (Task 3); readability tier dispatch + 3 rubrics incl. p-value-assumption deletion (Task 2); ask-an-expert + research command (Task 4); invariants preserved (Global Constraints, not edited); evals (Task 5); version bump + PR + memory (Tasks 6–7, Closing). All 7 acceptance criteria mapped.
- **Placeholder scan:** every edit step carries exact old/new strings and exact verify commands; no TBD/TODO.
- **Type/string consistency:** the shared path `scientific-peer-review/references/expected-reader.md` (no `../`) is used identically in Tasks 3–4; rubrics use the local form `expected-reader.md` ("provided with this rubric"); the new eval id `readability-10th-grade-default` matches across the two grep checks.
