# scientific-peer-review Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `scientific-peer-review` Claude Code skill — an adversarial multi-reviewer panel that takes a draft scientific paper and returns one adjudicated, severity-ranked revision plan.

**Architecture:** A lean `SKILL.md` orchestrator fans out 6 reviewer subagents (each loading only its own rubric file) in parallel, then a meta-editor synthesizes their reports into one ranked revision plan. Review-only: it never edits the paper. Citation resolution reuses the existing `deep-research` skill rather than shipping new code. Progressive disclosure keeps `SKILL.md` small with detail in `references/`.

**Tech Stack:** Markdown skill files (SKILL.md + references), JSON evals. No application code. Authoring conventions follow `superpowers:writing-skills`. Verification is structural (file presence, JSON validity, required-section greps) plus an end-to-end eval pass.

**Spec:** `docs/superpowers/specs/2026-06-16-scientific-peer-review-design.md`

**Note on TDD for a content build:** the "test written first" is the eval set (Task 1) — it defines success and cannot pass until the skill exists. Per-file tasks use content-presence checks as their unit test. The end-to-end eval (Task 9) is the integration test.

---

## File Structure

All paths under `plugins/madskillz/skills/scientific-peer-review/`:

| File | Responsibility |
|---|---|
| `SKILL.md` | Orchestrator: integrity stance, input gathering, parallel dispatch, meta-editor synthesis, output, edge cases |
| `references/review-report-format.md` | The per-reviewer report shape + meta-editor deliverable + coverage statement |
| `references/reviewers/adversarial.md` | Adversary ("Reviewer 2") rubric |
| `references/reviewers/reproducibility.md` | Reproducibility rubric |
| `references/reviewers/consistency.md` | Internal-consistency rubric |
| `references/reviewers/statistical.md` | Statistical/methodological rubric |
| `references/reviewers/ethics-integrity.md` | Ethics & integrity rubric (can veto) |
| `references/reviewers/citation-integrity.md` | Citation-integrity rubric |
| `references/reviewers/meta-editor.md` | Meta-editor adjudication rubric |
| `evals/evals.json` | Trigger + behavior eval prompts and grading criteria |

Plus files outside the skill dir:
- `plugins/madskillz/commands/research.md` — `/research` umbrella command (thin launcher → invokes the skill)
- `plugins/madskillz/.claude-plugin/plugin.json` — version bump `0.4.0` → `0.5.0`

Skills are auto-discovered; no registration entry is needed. Minimal skills in this plugin ship just their content files (no LICENSE/README/VERSION), so this skill does the same.

---

## Task 1: Scaffold directory + evals (acceptance criteria first)

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/evals/evals.json`

- [ ] **Step 1: Create the directory tree**

```bash
mkdir -p plugins/madskillz/skills/scientific-peer-review/references/reviewers \
         plugins/madskillz/skills/scientific-peer-review/evals
```

- [ ] **Step 2: Write the eval set (the failing acceptance test)**

Write `plugins/madskillz/skills/scientific-peer-review/evals/evals.json`:

```json
{
  "skill": "scientific-peer-review",
  "description": "Trigger and behavior evals for the adversarial peer-review panel.",
  "tests": [
    {
      "id": "trigger-basic",
      "prompt": "Here's a draft — run it through peer review and tell me what a tough reviewer would say. [draft attached]",
      "should_trigger": true,
      "grading_criteria": [
        "Skill triggers",
        "Asks for the draft if not actually provided",
        "Produces all six reviewer reports (adversarial, reproducibility, consistency, statistical, ethics-integrity, citation-integrity)",
        "Each finding has severity + location + required change",
        "Emits one ranked meta-editor revision plan",
        "Includes a coverage statement listing which checks ran"
      ]
    },
    {
      "id": "stats-focus",
      "prompt": "Review this study for statistical problems; are the effect sizes and corrections right? [study attached]",
      "should_trigger": true,
      "grading_criteria": [
        "Statistical reviewer checks test selection, assumptions, effect sizes + CIs, multiple-comparison correction, power",
        "Flags reported numbers as untraceable when no analysis outputs are supplied"
      ]
    },
    {
      "id": "citation-no-network",
      "prompt": "Are the citations in this paper real and do they support the claims? [paper attached, assume no network]",
      "should_trigger": true,
      "grading_criteria": [
        "Citation-integrity reviewer runs internal both-direction orphan checks",
        "Unresolvable references are flagged 'verification pending', never reported as a silent pass"
      ]
    },
    {
      "id": "planted-flaw",
      "prompt": "Is this ready to submit? What would block it? [draft contains a hallucinated citation, an uncorrected multiple-comparison family, and a conclusion outside the stated scope]",
      "should_trigger": true,
      "grading_criteria": [
        "Citation-integrity catches the hallucinated citation as a blocker",
        "Statistical catches the uncorrected multiple-comparison family",
        "Consistency catches the out-of-scope conclusion",
        "Meta-editor ranks blockers above minors"
      ]
    },
    {
      "id": "out-of-scope-rewrite",
      "prompt": "Review this and then rewrite it to fix everything. [draft attached]",
      "should_trigger": true,
      "grading_criteria": [
        "Performs the review",
        "States that rewriting/revising is out of scope and points to applying the plan or a future writeup skill"
      ]
    },
    {
      "id": "no-trigger-control",
      "prompt": "What's the capital of France?",
      "should_trigger": false,
      "grading_criteria": ["Skill does not trigger"]
    }
  ]
}
```

- [ ] **Step 3: Verify the JSON is valid**

Run: `python3 -c "import json; json.load(open('plugins/madskillz/skills/scientific-peer-review/evals/evals.json')); print('valid JSON')"`
Expected: `valid JSON`

(The evals cannot pass yet — the skill does not exist. That is the red state. Task 9 turns it green.)

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/evals/evals.json
git commit -m "test: add scientific-peer-review eval set (acceptance criteria)"
```

---

## Task 2: Shared report-format reference

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/review-report-format.md`

- [ ] **Step 1: Write the report-format reference**

Write `plugins/madskillz/skills/scientific-peer-review/references/review-report-format.md`:

```markdown
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
```

- [ ] **Step 2: Verify the file exists and contains both shapes**

Run:
```bash
f=plugins/madskillz/skills/scientific-peer-review/references/review-report-format.md
grep -q "Per-reviewer report" "$f" && grep -q "Meta-editor deliverable" "$f" \
  && grep -q "Coverage" "$f" && echo PASS || echo FAIL
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/review-report-format.md
git commit -m "feat: add review report format reference for scientific-peer-review"
```

---

## Task 3: Adversarial + Reproducibility rubrics

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/adversarial.md`
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/reproducibility.md`

- [ ] **Step 1: Write `adversarial.md`**

```markdown
# Adversarial reviewer ("Reviewer 2")

You are the adversarial peer reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Be the toughest *fair* reviewer the paper will ever face — attack its
weakest points, but only with defensible objections.

## Required inputs
- The draft manuscript (required).

## What to check
- Premise & framing: is the question well-posed and worth answering? Is the framing slanted?
- Alternative explanations: for every result, what else could explain it? Confounds,
  selection effects, leakage, regression to the mean.
- Overclaiming: gaps between what was shown and what is concluded; causal language from
  designs that can only support association.
- Baselines & comparisons: cherry-picked, weak, or missing baselines; unfair comparisons.
- The "what would have to be true for this to be wrong?" test — name those conditions and
  whether the paper rules them out.

## If inputs are missing
- You only need the draft; you can always run. Where a claim depends on data you cannot see,
  flag the claim as unverifiable rather than assuming it holds.

## Output
Return the report shape in `references/review-report-format.md`. List inputs available and
any checks you could not perform.
```

- [ ] **Step 2: Write `reproducibility.md`**

```markdown
# Reproducibility reviewer

You are the reproducibility reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Try to reproduce the work as a stranger who has only what was provided.

## Required inputs
- The draft manuscript (required).
- Helpful: code, data, environment capture (versions/seeds/hardware), the reproducibility
  package, exact commands.

## What to check
- Every missing seed, library/version, hyperparameter, dataset, or undocumented step.
- Whether the environment capture is complete enough to re-run.
- Whether the methods section alone would let a stranger reproduce the headline result.
- Rate reproducibility: **conceptual** (idea is clear) / **runnable** (could re-execute from
  what's given) / **bit-for-bit** (would get identical numbers). Name exactly what blocks the
  next level up.

## If inputs are missing
- With no code/data/environment, assess the *described* methods only and cap the rating at
  **conceptual**. Say so explicitly; do not guess that it would run.

## Output
Return the report shape in `references/review-report-format.md`. List inputs available and
any checks you could not perform.
```

- [ ] **Step 3: Verify both files contain their required sections**

Run:
```bash
d=plugins/madskillz/skills/scientific-peer-review/references/reviewers
for f in adversarial reproducibility; do
  grep -q "## What to check" "$d/$f.md" && grep -q "review-report-format" "$d/$f.md" \
    && echo "$f PASS" || echo "$f FAIL"
done
```
Expected: `adversarial PASS` and `reproducibility PASS`

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/reviewers/adversarial.md \
        plugins/madskillz/skills/scientific-peer-review/references/reviewers/reproducibility.md
git commit -m "feat: add adversarial and reproducibility reviewer rubrics"
```

---

## Task 4: Consistency + Statistical rubrics

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/consistency.md`
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/statistical.md`

- [ ] **Step 1: Write `consistency.md`**

```markdown
# Internal-consistency reviewer

You are the internal-consistency reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Check the paper against *itself*.

## Required inputs
- The draft manuscript (required).
- Helpful: the pre-registration (to verify confirmatory vs. exploratory labels).

## What to check
- Do the abstract's claims match the results?
- Do numbers agree across text, tables, and figures?
- Does every stated hypothesis/question get answered?
- Does the conclusion follow from the data shown and stay inside the paper's stated scope?
- Are confirmatory vs. exploratory labels preserved from the pre-registration?
- Any internal contradiction anywhere.

## If inputs are missing
- With no pre-registration, you cannot verify confirmatory/exploratory labels — report that
  as a check you could not perform, do not assume the labels are correct.

## Output
Return the report shape in `references/review-report-format.md`. List inputs available and
any checks you could not perform.
```

- [ ] **Step 2: Write `statistical.md`**

```markdown
# Statistical / methodological reviewer

You are the statistical reviewer. Read ONLY this rubric, the manuscript, and any supplied
inputs. Validate the statistics independently.

## Required inputs
- The draft manuscript (required).
- Helpful: analysis outputs / results tables (to trace every reported number), the
  pre-registered analysis plan.

## What to check
- Right test for the design and data type? Are test assumptions checked (normality,
  homoscedasticity, independence), with appropriate robust/nonparametric fallbacks?
- Is an **effect size with a confidence interval** reported, not just a p-value?
- Are multiple comparisons corrected across the family of tests?
- Is the design adequately powered, or are claims appropriately downgraded?
- Signs of p-hacking, optional stopping, or garden-of-forking-paths?
- Does the analysis match the pre-registered plan, and are deviations disclosed?
- "Accepting the null" treated as inconclusive, not as proof of no effect.

## If inputs are missing
- With no analysis outputs, review the statistics *as reported* and flag every number you
  cannot trace to a source as untraceable. Do not assume the numbers are correct.

## Output
Return the report shape in `references/review-report-format.md`. List inputs available and
any checks you could not perform.
```

- [ ] **Step 3: Verify both files contain their required sections**

Run:
```bash
d=plugins/madskillz/skills/scientific-peer-review/references/reviewers
for f in consistency statistical; do
  grep -q "## What to check" "$d/$f.md" && grep -q "review-report-format" "$d/$f.md" \
    && echo "$f PASS" || echo "$f FAIL"
done
```
Expected: `consistency PASS` and `statistical PASS`

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/reviewers/consistency.md \
        plugins/madskillz/skills/scientific-peer-review/references/reviewers/statistical.md
git commit -m "feat: add consistency and statistical reviewer rubrics"
```

---

## Task 5: Ethics-integrity + Citation-integrity rubrics

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/ethics-integrity.md`
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/citation-integrity.md`

- [ ] **Step 1: Write `ethics-integrity.md`**

```markdown
# Ethics & integrity reviewer

You are the ethics & integrity reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Scan for research-ethics and integrity problems. **You can issue a hard
veto** (recommendation: reject, with a blocker finding).

## Required inputs
- The draft manuscript (required).
- Helpful: any context on data source, consent, approvals, funding, conflicts.

## What to check
- Human/animal subjects: is IRB/IACUC status stated and plausible for the work described?
- Data privacy and consent handled? Any PII exposure?
- Dual-use or harm potential considered where relevant?
- Conflicts of interest and funding disclosed?
- **Any sign of fabricated data, plagiarism, or hallucinated content.** Numbers too clean,
  results that contradict the supplied data, citations that look invented (these hand off to
  the citation-integrity reviewer for confirmation).

## If inputs are missing
- You can always run on the draft. Where you cannot confirm an ethics fact (e.g. no approval
  documentation), flag it as an open question, do not assume compliance.

## Output
Return the report shape in `references/review-report-format.md`. Any credible fabrication or
ethics red flag is a **blocker**. List inputs available and any checks you could not perform.
```

- [ ] **Step 2: Write `citation-integrity.md`**

```markdown
# Citation-integrity reviewer

You are the citation-integrity reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Verify that citations are real and support their claims.

## Required inputs
- The draft manuscript (required). Extract in-text citations and the reference list from it.
- Helpful: a separate bibliography file; network/web tools for identifier resolution.

## What to check (always, no network needed)
- Both directions: every in-text citation has a matching reference entry, and every reference
  entry is cited in text. Flag orphans either way.
- Each reference carries a well-formed identifier (DOI / arXiv ID / ISBN / stable URL).
- Each citation plausibly supports the *specific* claim it is attached to, not merely the
  same topic.

## Resolution (when tools/network are available)
- Verify that identifiers actually resolve to the cited work. Prefer reusing the
  `deep-research` skill's fetch/verify machinery (or web tools) rather than guessing.

## If tools are unavailable
- Flag each unresolved reference as **"verification pending — could not resolve"**. NEVER
  report a silent pass for a citation you could not verify. This goes in the coverage section.

## Output
Return the report shape in `references/review-report-format.md`. An unverifiable or
unsupported citation is a **blocker**, not a warning. List inputs available and any checks
you could not perform.
```

- [ ] **Step 3: Verify both files contain their required sections**

Run:
```bash
d=plugins/madskillz/skills/scientific-peer-review/references/reviewers
grep -q "## What to check" "$d/ethics-integrity.md" && grep -q "veto" "$d/ethics-integrity.md" \
  && echo "ethics PASS" || echo "ethics FAIL"
grep -q "verification pending" "$d/citation-integrity.md" \
  && grep -q "deep-research" "$d/citation-integrity.md" \
  && echo "citation PASS" || echo "citation FAIL"
```
Expected: `ethics PASS` and `citation PASS`

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/reviewers/ethics-integrity.md \
        plugins/madskillz/skills/scientific-peer-review/references/reviewers/citation-integrity.md
git commit -m "feat: add ethics-integrity and citation-integrity reviewer rubrics"
```

---

## Task 6: Meta-editor rubric

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/meta-editor.md`

- [ ] **Step 1: Write `meta-editor.md`**

```markdown
# Meta-editor (handling editor)

You are the handling editor. You receive every reviewer's report plus the manuscript. You do
NOT write or revise the paper — you direct the revision.

## Inputs
- All six reviewer reports.
- The manuscript and the coverage facts (which reviewers ran, which inputs were available,
  whether reviews were parallel or sequential).

## What to do
- Deduplicate findings that multiple reviewers raised; keep the clearest statement and credit
  all originating reviewers.
- Resolve conflicts. **Integrity and correctness outrank presentation.** If the Ethics or
  Citation-integrity reviewer raised a blocker, it stands.
- **Surface genuine disagreement** — when reviewers materially conflict (e.g. one says reject,
  another says accept on the same point), state the split for the human to adjudicate; do not
  average it away.
- Rank all findings blocker → major → minor.
- Emit ONE ordered revision plan, then the overall call. Stop there — revision is out of scope.

## Output
Return the **Meta-editor deliverable** shape in `references/review-report-format.md`,
including the coverage statement.
```

- [ ] **Step 2: Verify the file contains its key directives**

Run:
```bash
f=plugins/madskillz/skills/scientific-peer-review/references/reviewers/meta-editor.md
grep -q "Surface genuine disagreement" "$f" && grep -q "do NOT write or revise" "$f" \
  && grep -q "Meta-editor deliverable" "$f" && echo PASS || echo FAIL
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/reviewers/meta-editor.md
git commit -m "feat: add meta-editor adjudication rubric"
```

---

## Task 7: SKILL.md orchestrator

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/SKILL.md`

All reviewer files referenced below now exist (Tasks 2–6).

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: scientific-peer-review
description: >-
  Run a draft scientific paper or study through an adversarial multi-reviewer
  peer-review panel and return one adjudicated, severity-ranked revision plan.
  Use whenever the user wants to peer-review a paper or draft, find out what a
  tough reviewer would say, pressure-test a study for statistical,
  reproducibility, consistency, ethics, or citation problems, verify whether
  citations are real and support their claims, or get a draft "peer-review
  ready" before submission. Trigger on phrases like "review this paper," "what
  would Reviewer 2 say," "is this study sound," "check my stats," "are these
  citations real," or "is this ready to submit." Reviews only — it does not
  write or revise the paper.
---

# scientific-peer-review: adversarial peer-review panel

Take a draft scientific paper or study and run it through an adversarial,
multi-reviewer panel, then synthesize one adjudicated, severity-ranked revision
plan. This tells an author exactly what a tough, fair external reviewer would
say — before they submit.

**Review only.** The deliverable is a plan. This skill never edits the paper.
Re-review = run it again. Writing/revising belongs to the author (or a future
`scientific-writeup` skill).

## Integrity stance (non-negotiable)

1. Never fabricate a verdict or a verification. A check you cannot run is
   reported as skipped, never as passed.
2. No silent citation pass — an unverifiable reference is flagged "verification
   pending," never asserted as verified.
3. Surface, don't smooth — genuine reviewer disagreement is reported for the
   human to adjudicate, never averaged away.
4. The review states its own coverage: which reviewers ran, which inputs were
   present, which checks were skipped.
5. Integrity and correctness outrank presentation in every conflict.

## Step 1 — Gather inputs

Required: the **draft manuscript**. If it is not actually provided, ask for it —
do not review from a verbal description.

Optional (each strengthens specific reviewers; absence is handled, not faked):
pre-registration, analysis outputs/results tables, code/reproducibility package,
reference list/bibliography. Note what is present and what is missing.

Detect: are subagents available (Claude Code) or not (e.g. claude.ai)? Is there
network/web access for citation resolution?

## Step 2 — Fan out the reviewer panel

Run these six reviewers, each reading ONLY its own rubric plus the manuscript and
available inputs:

| Reviewer | Rubric |
|---|---|
| Adversarial ("Reviewer 2") | `references/reviewers/adversarial.md` |
| Reproducibility | `references/reviewers/reproducibility.md` |
| Internal consistency | `references/reviewers/consistency.md` |
| Statistical / methodological | `references/reviewers/statistical.md` |
| Ethics & integrity (can veto) | `references/reviewers/ethics-integrity.md` |
| Citation-integrity | `references/reviewers/citation-integrity.md` |

- **In Claude Code:** dispatch them as parallel subagents (use
  `superpowers:dispatching-parallel-agents`). Independent context is what makes
  the reviews genuinely independent.
- **Where subagents are unavailable:** run each reviewer sequentially in a fresh
  framing, adopting one rubric at a time and not reusing prior reviewers'
  reasoning. Disclose the weaker independence in the output.
- **Citation resolution:** when network/web tools exist, the citation-integrity
  reviewer verifies identifiers (reuse the `deep-research` skill or web tools).
  When they don't, it flags references "verification pending" — never a silent
  pass.

Each reviewer returns the report shape in `references/review-report-format.md`.

## Step 3 — Meta-editor synthesis

After all six return, run the meta-editor (`references/reviewers/meta-editor.md`)
over every report. It deduplicates, resolves conflicts (integrity/correctness
wins), ranks findings, surfaces genuine disagreements, and emits ONE ordered
revision plan plus the overall call and the coverage statement.

## Step 4 — Deliver and stop

Present the reviewer reports and the meta-editor deliverable. Stop. Do not revise
the paper. If asked to also rewrite, say that is out of scope here and point to
applying the plan manually (or the future `scientific-writeup` skill).

## Edge cases

- No draft → ask for it; never review from a description.
- Draft only, nothing else → run all six on what's there; the coverage statement
  makes the thinness explicit; Reproducibility/Statistical narrow their claims.
- No network → citation resolution flagged pending, not passed.
- Ethics red flag (human subjects without approval, dual-use, fabrication signs)
  → Ethics-integrity raises a blocker/veto, surfaced prominently.
- Reviewers disagree → meta-editor surfaces the split, does not average it.
- Asked to also rewrite → out of scope; point to applying the plan.
- No subagents (claude.ai) → sequential reviews, reduced independence disclosed.
```

- [ ] **Step 2: Verify the frontmatter and structure**

Run:
```bash
python3 - <<'PY'
import re, sys
p = "plugins/madskillz/skills/scientific-peer-review/SKILL.md"
s = open(p).read()
m = re.match(r"^---\n(.*?)\n---\n", s, re.S)
assert m, "missing frontmatter"
fm = m.group(1)
assert re.search(r"^name:\s*scientific-peer-review\s*$", fm, re.M), "name wrong/missing"
desc = re.search(r"description:\s*(.+)", fm, re.S)
assert desc, "description missing"
assert len(desc.group(1)) <= 1024, "description too long"
for needed in ["Integrity stance", "Fan out the reviewer panel",
               "Meta-editor synthesis", "Deliver and stop"]:
    assert needed in s, f"missing section: {needed}"
print("SKILL.md PASS")
PY
```
Expected: `SKILL.md PASS`

- [ ] **Step 3: Verify every referenced file exists**

Run:
```bash
d=plugins/madskillz/skills/scientific-peer-review
for f in references/review-report-format.md \
         references/reviewers/adversarial.md references/reviewers/reproducibility.md \
         references/reviewers/consistency.md references/reviewers/statistical.md \
         references/reviewers/ethics-integrity.md references/reviewers/citation-integrity.md \
         references/reviewers/meta-editor.md; do
  test -f "$d/$f" && echo "$f ok" || echo "$f MISSING"
done
```
Expected: every line ends in `ok`

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/SKILL.md
git commit -m "feat: add scientific-peer-review SKILL.md orchestrator"
```

---

## Task 8: Create the `/research` umbrella command

**Files:**
- Create: `plugins/madskillz/commands/research.md`

A plugin slash command (a thin launcher), not skill logic. It is the explicit, intentional
entry point to the `scientific-*` family; today it launches the only built member,
`scientific-peer-review`. The skill still auto-triggers as well. Build it after Task 7 so the
skill it launches exists.

- [ ] **Step 1: Write `plugins/madskillz/commands/research.md`**

````markdown
---
description: Entry point to the scientific research family — runs the adversarial peer-review panel on a draft (more research phases coming).
argument-hint: [path to draft, or what you want reviewed]
---

You are the entry point to the `scientific-*` research skill family. The built
capability today is **peer review**; study design, write-up, analysis, and
reproducibility packaging will be routed from here as they are added.

Invoke the `scientific-peer-review` skill to run the adversarial multi-reviewer
panel.

What to review: $ARGUMENTS

If no draft (or path to one) was provided above, ask the user for the draft
before proceeding — never review from memory or a verbal description.
````

- [ ] **Step 2: Verify the command file exists with valid frontmatter**

Run:
```bash
f=plugins/madskillz/commands/research.md
test -f "$f" && head -1 "$f" | grep -q '^---$' \
  && grep -q "scientific-peer-review" "$f" \
  && grep -q 'ARGUMENTS' "$f" && echo PASS || echo FAIL
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/commands/research.md
git commit -m "feat: add /research umbrella command launching scientific-peer-review"
```

---

## Task 9: Bump plugin version

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json`

- [ ] **Step 1: Bump the version 0.4.0 → 0.5.0**

Change the `"version"` line in `plugins/madskillz/.claude-plugin/plugin.json` from
`"version": "0.4.0",` to `"version": "0.5.0",`.

- [ ] **Step 2: Verify the JSON is still valid and shows the new version**

Run:
```bash
python3 -c "import json; d=json.load(open('plugins/madskillz/.claude-plugin/plugin.json')); assert d['version']=='0.5.0', d['version']; print('version', d['version'])"
```
Expected: `version 0.5.0`

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore: bump madskillz plugin to 0.5.0 (adds scientific-peer-review skill + /research command)"
```

---

## Task 10: End-to-end eval validation (turn the acceptance test green)

**Files:**
- Read: `plugins/madskillz/skills/scientific-peer-review/evals/evals.json`
- May modify: any skill file, to fix gaps found here.

- [ ] **Step 1: Trigger check**

In a fresh context, give the `trigger-basic` and `no-trigger-control` prompts from
`evals.json`. Confirm the skill triggers on the first and stays silent on the second. If
triggering is wrong, refine the `description:` in `SKILL.md` (follow
`superpowers:writing-skills` for description tuning) and re-test.

Expected: triggers on `trigger-basic`, does not trigger on `no-trigger-control`.

Also confirm `/research <draft>` (the umbrella command) launches the panel by invoking the
`scientific-peer-review` skill. Expected: the command runs the review on the given draft.

- [ ] **Step 2: Behavior check with a planted-flaw draft**

Create a short throwaway draft containing the three planted flaws from the `planted-flaw`
eval (a hallucinated citation, an uncorrected multiple-comparison family, a conclusion
outside the stated scope). Run the skill on it.

Expected:
- All six reviewer reports are produced.
- Citation-integrity flags the hallucinated citation as a **blocker**.
- Statistical flags the uncorrected multiple-comparison family.
- Consistency flags the out-of-scope conclusion.
- The meta-editor deliverable ranks blockers above minors and includes a coverage statement.

- [ ] **Step 3: Degradation + integrity checks**

Run the `citation-no-network` and `out-of-scope-rewrite` prompts.

Expected:
- Unresolvable citations are flagged "verification pending," never a silent pass.
- The rewrite request is performed as a review only, with an explicit out-of-scope note.

- [ ] **Step 4: Fix any gaps inline, then re-run the failing eval**

If any expectation failed, edit the relevant rubric or `SKILL.md`, commit with a
`fix:` message, and re-run that eval until it passes.

- [ ] **Step 5: Final commit (if fixes were made)**

```bash
git add plugins/madskillz/skills/scientific-peer-review/
git commit -m "fix: address scientific-peer-review eval gaps"
```

---

## Self-Review (completed by plan author)

**Spec coverage** — every In-scope item in spec §1.1 maps to a task:
- Reviewing a draft + supporting artifacts → Tasks 3–5 (rubrics), Task 7 (input gathering).
- Per-reviewer structured reports → Task 2 (format) + Tasks 3–6.
- Adjudicated single revision plan + surfaced disagreement → Task 6 (meta-editor).
- Honest coverage / degradation → report-format Coverage section (Task 2), each rubric's
  "If inputs are missing" (Tasks 3–5), SKILL.md integrity stance (Task 7).
- Integrity stance (§3) → SKILL.md (Task 7) + ethics/citation rubrics (Task 5).
- Inputs & degradation (§4) → SKILL.md Step 1 (Task 7) + per-rubric sections.
- Roster of 6 + meta-editor (§5) → Tasks 3–6.
- Orchestration + environment branch (§6) → SKILL.md Step 2 (Task 7).
- Citation reuse, no silent pass (§7) → citation-integrity rubric (Task 5) + SKILL.md.
- Output shapes + coverage statement (§8) → Task 2.
- File structure (§9) → all tasks; directory created in Task 1.
- Edge cases (§10) → SKILL.md Edge cases (Task 7).
- Evals (§11) → Task 1 + Task 10.
- Slash command /research umbrella (§13) → Task 8.
- Out-of-scope items (loop, revision, stats engine, provenance lint) → correctly absent.

**Placeholder scan** — no TBD/TODO; every file step contains the full file content; every
verification step has an exact command + expected output. The `<...>` tokens inside the
report-format and report-shape code blocks are intentional template fields, not plan gaps.

**Type/name consistency** — file paths, the six reviewer names, and the rubric filenames are
identical across the file-structure table, each creating task, the SKILL.md roster table, and
the Task 7 existence check. Plugin version target `0.5.0` consistent in Task 8.
```
