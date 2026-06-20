# Readability Tier (Subsystem A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-reviewer "readability tier" to the scientific peer-review panel and give the study paper the reader-facing back-matter (acronym index, glossary, optional background) those reviewers enforce.

**Architecture:** These skills are markdown prompt/persona files, not code. We add three reviewer persona files that follow the existing reviewer skeleton, wire them into the peer-review orchestrator as a second "readability" tier (the existing six become the "correctness" tier), document the required `paper.md` back-matter in the study templates, and instruct the study's drafting step to produce it. Verification is deterministic `grep`/`jq` structural checks plus LLM-graded eval cases — there is no unit-test runner for prompt files.

**Tech Stack:** Markdown (skill + reference files), JSON (evals), `grep`/`jq` for structural verification.

## Global Constraints

Copied verbatim from the spec (`docs/superpowers/specs/2026-06-20-research-readability-experts-and-review-loop-design.md`). Every task implicitly includes these.

- **Reading standard:** "adjacent-field body, generalist-accessible by design." Body = adjacent-field researcher (general scientific literacy, not a subfield specialist; do not explain standard concepts, do define/replace subfield jargon). Floor = educated generalist, served by scaffolding outside the body (abstract, Acronyms, Glossary, optional Background).
- **Earned-jargon rule:** a specialized term is allowed only when a plain phrase would lose real precision; when allowed it must be defined on first use AND glossed; when it needs background beyond the floor it gets a pointer, not an inline lecture; otherwise it is replaced.
- **Abstract is the plain-language summary** — there is NO separate lay-summary section.
- **Severity ceiling:** readability findings are normally `minor`; may rise to `major` only for a completeness failure (term/acronym used-but-undefined or missing from its index; a missing required reader-facing section; a missing/badly-misleading abstract); **never `blocker`**.
- **Defer to correctness:** readability never outranks correctness; on conflict, reframe as "define the term" and surface the disagreement to the meta-editor — never average it away.
- **Anti-fabrication:** suggested background reading must be a verified, resolvable source (DOI / arXiv / ISBN / stable URL) OR a clearly-marked topic/keyword suggestion — NEVER a fabricated citation.
- **Integrity stance (peer-review SKILL.md):** never fabricate a verdict/verification; state coverage; surface disagreement; integrity and correctness outrank presentation.
- **Reviewer-file convention (match exactly):** `# <Reviewer name>` → opening "You are the … reviewer. Read ONLY this rubric, the manuscript, and any supplied inputs. <mission>." → `## Required inputs` → `## What to check` → `## If inputs are missing` → `## Output` ("Return the report shape in `references/review-report-format.md`. List inputs available and any checks you could not perform.").
- **Paths:** peer-review skill at `plugins/madskillz/skills/scientific-peer-review/`; study skill at `plugins/madskillz/skills/scientific-study/`.

---

### Task 1: Plain-language / clarity reviewer persona

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md`

**Interfaces:**
- Consumes: the shared report shape at `references/review-report-format.md` (already exists).
- Produces: a rubric file named `plain-language.md` that Task 4 wires into the panel table.

- [ ] **Step 1: Write the reviewer file**

Create `plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md` with exactly this content:

````markdown
# Plain-language / clarity reviewer

You are the plain-language / clarity reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Judge whether the paper is readable by its intended reader without sacrificing
correctness. You never trade precision for plainness — where they conflict you ask the authors to
*define* a term, not delete it, and you defer to the correctness reviewers.

## The expected reader
Calibrate to an **adjacent-field researcher** reading the body, with an **educated-generalist
floor**: general scientific literacy (reads a methods section, knows what a p-value and a
confidence interval are, understands basic experimental design) but NOT a specialist in this
subfield. Standard scientific concepts need no explanation; subfield-specific jargon must be
defined or replaced.

## Required inputs
- The draft manuscript (required), including its abstract.

## What to check
- **Abstract as plain-language summary:** can the expected reader grasp what was done and what was
  found from the abstract alone? There is no separate lay summary — the abstract carries that role.
- **Earned-jargon test:** for each specialized term, would a plain phrase lose real precision? If
  not, flag it for replacement. If yes it is allowed, but must be defined on first use (the
  terminology reviewer enforces the index/glossary).
- **Verbosity & redundancy:** sentences and paragraphs that can be shortened without losing
  meaning; padding; repetition.
- **Structure & flow:** logical ordering, signposting, topic sentences; dense passages that lock
  out the expected reader.

## If inputs are missing
- You only need the draft; you can always run. Judge what is present; do not invent missing
  sections.

## Defer to correctness
- A clarity suggestion must never reduce precision or correctness. When plainness and precision
  conflict, reframe as "define the term," and surface the disagreement to the meta-editor rather
  than overriding a correctness reviewer.

## Output
Return the report shape in `references/review-report-format.md`. Readability findings are normally
`minor`; a missing or badly misleading abstract may rise to `major`, never `blocker`. List inputs
available and any checks you could not perform.
````

- [ ] **Step 2: Verify the file exists with the required skeleton**

Run:
```bash
cd /home/bub/Development/madskillz
f=plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md
grep -c -E '^## (Required inputs|What to check|If inputs are missing|Output)$' "$f"
```
Expected: `4`

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/reviewers/plain-language.md
git commit -m "feat(peer-review): add plain-language / clarity reviewer"
```

---

### Task 2: Terminology & acronym reviewer persona

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md`

**Interfaces:**
- Consumes: the report shape at `references/review-report-format.md`; the `paper.md` back-matter sections (`Acronyms`, `Glossary`) that Task 5 documents — this reviewer enforces them.
- Produces: a rubric file named `terminology-acronyms.md` that Task 4 wires into the panel table.

- [ ] **Step 1: Write the reviewer file**

Create `plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md` with exactly this content:

````markdown
# Terminology & acronym reviewer

You are the terminology & acronym reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Enforce that every acronym and specialized term the paper uses is defined and
indexed — in both directions — so the expected reader is never blocked by an unexplained term.

## Required inputs
- The draft manuscript (required). Extract every acronym and specialized term, the Acronyms index,
  and the Glossary from it.

## What to check
- **Acronyms (both directions):** every acronym is expanded on first use in the body AND present in
  the **Acronyms** index; every index entry is actually used. Flag orphans either way.
- **Glossary (both directions):** every specialized term used in the body is present in the
  **Glossary**, defined accessibly for the expected reader; every glossary entry is actually used.
- **Section presence:** the Acronyms index and Glossary sections exist. If the paper uses acronyms
  or specialized terms but lacks the corresponding section, that is a completeness failure.
- **Consistency:** no synonym drift (one canonical name per concept throughout); one canonical
  expansion per acronym, applied wherever it is first introduced.

## If inputs are missing
- You only need the draft; you can always run. If the paper genuinely uses no acronyms or
  specialized terms, say so — do not manufacture findings.

## Output
Return the report shape in `references/review-report-format.md`. A term/acronym used but never
defined or missing from its index, or a missing required section (Acronyms / Glossary) when the
paper needs one, is a `major`; orphan entries and synonym drift are `minor`; never `blocker`. List
inputs available and any checks you could not perform.
````

- [ ] **Step 2: Verify the file exists with the required skeleton**

Run:
```bash
cd /home/bub/Development/madskillz
f=plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md
grep -c -E '^## (Required inputs|What to check|If inputs are missing|Output)$' "$f"
```
Expected: `4`

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/reviewers/terminology-acronyms.md
git commit -m "feat(peer-review): add terminology & acronym reviewer"
```

---

### Task 3: Accessibility / background reviewer persona

**Files:**
- Create: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md`

**Interfaces:**
- Consumes: the report shape at `references/review-report-format.md`; the optional `Background / further reading` section Task 5 documents.
- Produces: a rubric file named `accessibility-background.md` that Task 4 wires into the panel table.

- [ ] **Step 1: Write the reviewer file**

Create `plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md` with exactly this content:

````markdown
# Accessibility / background reviewer

You are the accessibility / background reviewer. Read ONLY this rubric, the manuscript, and any
supplied inputs. Judge whether the expected reader can navigate the paper, and where they would
need background, point them to it honestly. You are the reader-facing twin of the panel's own
"consult an expert" gate: that gate finds the expertise the *panel* lacks; you find the background
the *reader* lacks.

## The expected reader
An adjacent-field researcher with an educated-generalist floor (general scientific literacy, not a
subfield specialist). The reader navigates the body with the help of the abstract, the Glossary,
the Acronyms index, and any Background / further-reading pointers.

## Required inputs
- The draft manuscript (required), including its abstract, Glossary, Acronyms index, and any
  Background section.

## What to check
- **Navigability:** can the expected reader follow the paper using the abstract + glossary +
  background pointers? Identify passages where required background is assumed but not provided.
- **Background needs:** list each concept needing prior grounding beyond the reader's level. For
  each, supply a **verified, resolvable source** (real DOI / arXiv ID / ISBN / stable URL) when one
  can be confirmed, OR — when none can be verified — a clearly-marked **topic / keyword
  suggestion** to read up on. NEVER present an unverified source as a citation; a fabricated
  reading is worse than an honest "read up on X."
- **Background section:** if a Background / further-reading section exists, check its coverage and
  that its sources are verifiable or marked as topic suggestions.

## If inputs are missing
- You only need the draft; you can always run. Where you cannot verify a source (no network), mark
  every suggested reading as an unverified topic suggestion, not a citation, and note it in
  coverage.

## Defer to correctness
- Background pointers and accessibility suggestions never override a correctness finding; surface
  any conflict to the meta-editor.

## Output
Return the report shape in `references/review-report-format.md`. Findings are normally `minor`; a
concept essential to the central claim that the expected reader cannot follow and has no pointer
for may rise to `major`, never `blocker`. List inputs available and any checks you could not
perform.
````

- [ ] **Step 2: Verify the file exists with the required skeleton**

Run:
```bash
cd /home/bub/Development/madskillz
f=plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md
grep -c -E '^## (Required inputs|What to check|If inputs are missing|Output)$' "$f"
```
Expected: `4`

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/references/reviewers/accessibility-background.md
git commit -m "feat(peer-review): add accessibility / background reviewer"
```

---

### Task 4: Wire the readability tier into the panel

**Files:**
- Modify: `plugins/madskillz/skills/scientific-peer-review/SKILL.md` (Step 2 panel, Step 3 count, edge case)
- Modify: `plugins/madskillz/skills/scientific-peer-review/references/reviewers/meta-editor.md` (inputs line)
- Modify: `plugins/madskillz/skills/scientific-peer-review/references/review-report-format.md` (coverage + severity)

**Interfaces:**
- Consumes: the three rubric filenames produced by Tasks 1–3 (`plain-language.md`, `terminology-acronyms.md`, `accessibility-background.md`).
- Produces: a panel that runs nine reviewers in two named tiers; a coverage statement that names the tiers; a documented readability severity ceiling.

- [ ] **Step 1: Replace the Step 2 panel in SKILL.md**

In `plugins/madskillz/skills/scientific-peer-review/SKILL.md`, replace this block:

```
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
```

with:

```
Run these reviewers, each reading ONLY its own rubric plus the manuscript and
available inputs. The panel has two tiers; the coverage statement names which ran.

**Correctness tier (always):**

| Reviewer | Rubric |
|---|---|
| Adversarial ("Reviewer 2") | `references/reviewers/adversarial.md` |
| Reproducibility | `references/reviewers/reproducibility.md` |
| Internal consistency | `references/reviewers/consistency.md` |
| Statistical / methodological | `references/reviewers/statistical.md` |
| Ethics & integrity (can veto) | `references/reviewers/ethics-integrity.md` |
| Citation-integrity | `references/reviewers/citation-integrity.md` |

**Readability tier (always, for reader-facing drafts):**

| Reviewer | Rubric |
|---|---|
| Plain-language / clarity | `references/reviewers/plain-language.md` |
| Terminology & acronym | `references/reviewers/terminology-acronyms.md` |
| Accessibility / background | `references/reviewers/accessibility-background.md` |

The readability tier defers to the correctness tier in every conflict (presentation
never outranks correctness); its findings are normally `minor` and never `blocker`.
```

- [ ] **Step 2: Update the two "six" references in SKILL.md**

In the same file, change Step 3's opening from:

```
After all six return, run the meta-editor (`references/reviewers/meta-editor.md`)
```

to:

```
After all reviewers return, run the meta-editor (`references/reviewers/meta-editor.md`)
```

And in the Edge cases section change:

```
- Draft only, nothing else → run all six on what's there; the coverage statement
```

to:

```
- Draft only, nothing else → run all reviewers on what's there; the coverage statement
```

- [ ] **Step 3: Update the meta-editor inputs line**

In `plugins/madskillz/skills/scientific-peer-review/references/reviewers/meta-editor.md`, change:

```
- All six reviewer reports.
```

to:

```
- Every reviewer's report (the correctness tier, and the readability tier when it ran).
```

- [ ] **Step 4: Update the coverage block and severity scale in review-report-format.md**

In `plugins/madskillz/skills/scientific-peer-review/references/review-report-format.md`, change the coverage line:

```
Reviewers run: <list> (v1 tier: correctness-only)
```

to these two lines:

```
Reviewers run: <list>
Tiers run: <correctness | correctness + readability>
```

Then, immediately after the `minor` bullet of the severity scale (the line beginning `- **minor** — improvable but not disqualifying; may be deferred with a note.`), add this paragraph:

```

**Readability tier severity ceiling:** readability findings (plain-language, terminology &
acronym, accessibility / background) are normally `minor` and may rise to `major` only for a
completeness failure — a term/acronym used but never defined or missing from its index, a missing
required reader-facing section (Acronyms / Glossary), or a missing/badly-misleading abstract. They
are **never `blocker`**; the correctness tier owns blockers, and readability defers to correctness
in every conflict.
```

- [ ] **Step 5: Verify the wiring**

Run:
```bash
cd /home/bub/Development/madskillz
sp=plugins/madskillz/skills/scientific-peer-review
grep -c -E 'reviewers/(plain-language|terminology-acronyms|accessibility-background)\.md' "$sp/SKILL.md"   # expect 3
grep -c -E 'all six' "$sp/SKILL.md"                                                                        # expect 0
grep -c 'All six reviewer reports' "$sp/references/reviewers/meta-editor.md"                                # expect 0
grep -c 'Tiers run:' "$sp/references/review-report-format.md"                                               # expect 1
grep -c 'Readability tier severity ceiling' "$sp/references/review-report-format.md"                        # expect 1
```
Expected output, in order: `3`, `0`, `0`, `1`, `1`.

- [ ] **Step 6: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/SKILL.md \
        plugins/madskillz/skills/scientific-peer-review/references/reviewers/meta-editor.md \
        plugins/madskillz/skills/scientific-peer-review/references/review-report-format.md
git commit -m "feat(peer-review): run readability tier alongside correctness tier"
```

---

### Task 5: Document and draft the paper back-matter

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/references/repo-layout.md` (add paper back-matter spec; update README Contents bullet)
- Modify: `plugins/madskillz/skills/scientific-study/SKILL.md` (Step 2 drafting instruction)

**Interfaces:**
- Consumes: the reading standard (Global Constraints).
- Produces: the `Acronyms` / `Glossary` / optional `Background` sections that the Task 2 and Task 3 reviewers enforce; a drafting step that actually writes them.

- [ ] **Step 1: Add the paper back-matter section to repo-layout.md**

In `plugins/madskillz/skills/scientific-study/references/repo-layout.md`, immediately before the line `## README.md template`, insert this new section:

`````markdown
## paper.md structure (required back-matter)

The manuscript is written for an **adjacent-field researcher** with an **educated-generalist
floor** (general scientific literacy, not a subfield specialist). The **abstract** doubles as the
plain-language summary — a reader at that level grasps what was done and found from it alone. There
is no separate lay-summary section.

End the manuscript with this back-matter, in this order:

```markdown
## Acronyms
| Acronym | Expansion |
|---|---|
| <ABC> | <full expansion> |

## Glossary
| Term | Plain-language definition |
|---|---|
| <term> | <definition the expected reader can follow> |

## Background / further reading   <!-- optional; omit if nothing needs it -->
- <concept> — <verified source: DOI / arXiv ID / ISBN / stable URL>, OR a clearly-marked
  topic/keyword suggestion when no source can be verified. Never present an unverified reading as a
  citation.
```

- Every acronym used in the body is expanded on first use AND listed in **Acronyms**; every
  specialized term used in the body is in the **Glossary**. Both directions — no orphan entries.
- Omit **Background / further reading** if nothing needs it; never pad it to imply coverage.

`````

- [ ] **Step 2: Update the README Contents bullet in repo-layout.md**

In the same file's README.md template, change:

```
- `paper.md` — manuscript
```

to:

```
- `paper.md` — manuscript (ends with Acronyms, Glossary, and optional Background / further reading)
```

- [ ] **Step 3: Add the drafting instruction to scientific-study Step 2**

In `plugins/madskillz/skills/scientific-study/SKILL.md`, in `## Step 2 — Draft the paper and artifacts`, immediately after the sentence ending `do not invent data or citations.`, add this sentence:

```
Write for the expected reader (adjacent-field body, educated-generalist floor): the abstract
doubles as the plain-language summary, define every acronym on first use and every specialized term
in the glossary, and end the manuscript with the required back-matter — an **Acronyms** index, a
**Glossary**, and an optional **Background / further reading** section (see
`references/repo-layout.md`). Background readings must be verified sources or clearly-marked topic
suggestions, never fabricated citations.
```

- [ ] **Step 4: Verify**

Run:
```bash
cd /home/bub/Development/madskillz
ss=plugins/madskillz/skills/scientific-study
grep -c 'paper.md structure (required back-matter)' "$ss/references/repo-layout.md"          # expect 1
grep -c -E '^## (Acronyms|Glossary)$' "$ss/references/repo-layout.md"                         # expect 2
grep -c 'optional Background / further reading' "$ss/references/repo-layout.md"               # expect 1
grep -c 'adjacent-field body, educated-generalist floor' "$ss/SKILL.md"                       # expect 1
```
Expected output, in order: `1`, `2`, `1`, `1`.

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/references/repo-layout.md \
        plugins/madskillz/skills/scientific-study/SKILL.md
git commit -m "feat(study): require reader-facing paper back-matter (acronyms, glossary, background)"
```

---

### Task 6: Eval coverage for the readability tier

**Files:**
- Modify: `plugins/madskillz/skills/scientific-peer-review/evals/evals.json` (add a case; update `trigger-basic`)

**Interfaces:**
- Consumes: the behaviors built in Tasks 1–5.
- Produces: behavioral eval coverage so the tier's regressions are caught by the eval harness.

- [ ] **Step 1: Update the `trigger-basic` grading criterion**

In `plugins/madskillz/skills/scientific-peer-review/evals/evals.json`, in the `trigger-basic` test, replace this grading-criteria string:

```
"Produces all six reviewer reports (adversarial, reproducibility, consistency, statistical, ethics-integrity, citation-integrity)",
```

with:

```
"Produces the correctness-tier reports (adversarial, reproducibility, consistency, statistical, ethics-integrity, citation-integrity) and the readability-tier reports (plain-language, terminology-acronym, accessibility-background)",
```

- [ ] **Step 2: Add a `readability-tier` test**

In the same file, add this object as a new element of the `tests` array, immediately after the `planted-flaw` test object (mind the comma before it):

```json
    {
      "id": "readability-tier",
      "prompt": "Review this paper — is it readable for a non-specialist? Check the jargon, acronyms, and whether a reasonably educated reader could follow it. [draft attached: several undefined acronyms, no glossary, dense subfield jargon]",
      "should_trigger": true,
      "grading_criteria": [
        "Plain-language reviewer applies the earned-jargon test and flags undefined subfield jargon",
        "Terminology & acronym reviewer flags acronyms used but never defined and the missing Acronyms index / Glossary as a completeness failure (major)",
        "Accessibility / background reviewer offers background reading as verified sources or clearly-marked topic suggestions, never fabricated citations",
        "Readability findings are ranked no higher than major and defer to correctness; never blocker",
        "Coverage statement names the readability tier as having run"
      ]
    }
```

- [ ] **Step 3: Verify the JSON is valid and the case is present**

Run:
```bash
cd /home/bub/Development/madskillz
f=plugins/madskillz/skills/scientific-peer-review/evals/evals.json
jq -e '.tests[] | select(.id=="readability-tier")' "$f" >/dev/null && echo OK
jq '.tests | length' "$f"
```
Expected: `OK`, then `7`.

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/evals/evals.json
git commit -m "test(peer-review): add readability-tier eval coverage"
```

---

## Self-Review

**1. Spec coverage (Subsystem A sections of the design doc):**
- §4.1 plain-language reviewer → Task 1. ✓
- §4.2 terminology & acronym reviewer (bidirectional) → Task 2. ✓
- §4.3 accessibility / background reviewer (anti-fabrication) → Task 3. ✓
- §4.4 earned-jargon + defer-to-correctness → embedded in Tasks 1 & 3 files + Global Constraints. ✓
- §4.5 severity policy (minor; major for completeness; never blocker) → Task 4 Step 4 + stated in each reviewer's Output. ✓
- §4.6 paper template additions (Acronyms, Glossary, optional Background at bottom; abstract-as-summary; README contents) → Task 5. ✓
- §4.7 file-change map (3 new reviewers; SKILL.md tier; report-format; repo-layout) → Tasks 1–5; plus meta-editor "six" fix (found during file reads) → Task 4 Step 3. ✓
- "The skill states which tier ran" → Task 4 Step 4 coverage `Tiers run:`. ✓
- Drafting actually produces the sections (gap not in the design's file-map, caught here) → Task 5 Step 3 (`scientific-study` SKILL.md). ✓
- Eval coverage → Task 6. ✓

**2. Placeholder scan:** No "TBD/TODO/handle edge cases". All file contents are given verbatim; all verifications are concrete commands with expected output. ✓

**3. Type consistency:** Reviewer filenames are identical everywhere they appear — `plain-language.md`, `terminology-acronyms.md`, `accessibility-background.md` (Tasks 1–4, Task 6 criteria). Section names `Acronyms` / `Glossary` / `Background / further reading` match between the reviewer files (Tasks 2–3), the template (Task 5), and the drafting instruction (Task 5). Tier names `correctness` / `readability` match between SKILL.md (Task 4 Step 1) and the coverage line (Task 4 Step 4). ✓

**Note on B/D overlap:** Subsystem B will later add an `Interests` line to every reviewer (including these three) and update `meta-editor.md`; Subsystem D adds cycle snapshots. This plan deliberately does not touch those, to keep A independently shippable.
