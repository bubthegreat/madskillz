# Research skills: readability tier, expert system, incremental review, and cycle snapshots

**Date:** 2026-06-20
**Status:** Design approved (brainstorming) — pending written-spec review
**Branch:** scientific-peer-review

## 1. Context

The research family lives under `plugins/madskillz/`:

- `commands/research.md` — entry point; routes to *produce a study* or *review a draft*.
- `skills/scientific-study/` — produces a publication-ready study and opens a PR; runs an
  agentic peer-review quality-gate loop (`references/review-loop.md`), a compliance gate
  (`references/compliance-gate.md`), and uses repo templates (`references/repo-layout.md`).
- `skills/scientific-peer-review/` — the review engine: an orchestrator (`SKILL.md`), one
  persona file per reviewer under `references/reviewers/` (adversarial, reproducibility,
  consistency, statistical, ethics-integrity, citation-integrity) plus `meta-editor.md`, and a
  shared output spec `references/review-report-format.md`. Findings are ranked
  `blocker | major | minor`.

Two existing constraints shape everything below:

- **Integrity stance** (`scientific-peer-review/SKILL.md`): never fabricate a verdict or
  verification; no silent citation pass; surface disagreement rather than averaging it away;
  state your own coverage (which reviewers ran, which inputs were present, which checks were
  skipped); **integrity and correctness outrank presentation in every conflict.**
- The original spec deliberately **deferred a "communication tier"** (clarity editor,
  plain-language reviewer, domain/novelty reviewer) to keep v1 correctness-focused. This design
  implements and extends that deferred tier, and adds three adjacent capabilities the user
  surfaced while specifying it.

## 2. The reading standard (foundational decision)

All readability work calibrates to one standard: **"adjacent-field body, generalist-accessible
by design"** (two registers in one paper).

- **Body register = adjacent-field researcher.** The main text assumes general scientific
  literacy — a reader who can read a methods section, knows what a p-value and a confidence
  interval are, understands basic experimental design — but is **not** a specialist in this
  subfield. Consequence: do **not** spend words explaining standard scientific concepts (this is
  the "not overly verbose" requirement); **do** define or replace subfield-specific jargon.
- **Accessibility floor = educated generalist,** served by scaffolding that lives **outside** the
  body so it does not bloat the prose: the **abstract** (which doubles as the plain-language
  summary), an **Acronyms** index, a **Glossary**, and optional **Background / further reading**
  pointers.
- **Earned-jargon rule** (the operative test between the two levels): a specialized term is
  allowed in the body only when a plain phrase would lose real precision. When allowed, it must
  be defined on first use **and** glossed. When it needs background beyond the floor, it gets a
  background pointer rather than an inline lecture. Otherwise it is replaced with plain language.

**Calibration target (the "expected reader").** A strong quantitative/technical generalist —
concretely, the project owner: biomechanical engineer by training, systems/business analyst,
data-analytics and software leadership, MBA (data analytics) — comfortable with stats, methods,
software, and data, but not an arbitrary-subfield specialist. The **meta-editor makes a
best-presumption call** on the expected reader from this standard; it does not try to nail it
perfectly.

## 3. Scope and decomposition

Four related but independent subsystems. **One unifying design doc (this), implemented as
sequenced sub-projects, each with its own implementation plan.** Order: **A → D → B → C.**

| # | Subsystem | Touches | Depends on |
|---|-----------|---------|------------|
| A | Readability tier (3 reviewers + abstract criteria + template + severity) | peer-review skill, study template | — |
| D | Cycle snapshots | study skill | — |
| B | Incremental re-engagement (meta-editor empathy + loop change) | peer-review skill, study review-loop | snapshots (D) |
| C | Expert system (new `ask-an-expert` skill + research hooks) | new skill, peer-review, study | adversarial reviewer |

Rationale for order: A is the original ask; D is tiny and produces the diff B needs; B optimizes
the loop; C is the largest (a whole new skill) and is built last on a stable base.

---

## 4. Subsystem A — Readability tier

Three new reviewers added to the peer-review panel, each a persona file under
`references/reviewers/` following the existing convention (role header → required inputs → what
to check → missing-input handling → output via `review-report-format.md`). They are a tier:
the skill states when the readability tier ran.

### 4.1 Plain-language / clarity reviewer (`reviewers/plain-language.md`)

Owns body prose **and the abstract**. Checks:

- **Abstract as plain-language summary.** A reader at the expected-reader level grasps what was
  done and what was found from the abstract alone. (There is **no** separate plain-language
  summary section — the abstract *is* that, and is reviewed against this bar.)
- **Earned-jargon test** on the body: each specialized term carries precision a plain phrase
  would lose; otherwise flag for replacement.
- **Verbosity / redundancy:** sentences and paragraphs that could be shorter without losing
  meaning.
- **Structure & flow:** logical ordering, signposting, topic sentences; dense passages that lock
  out the adjacent-field reader.

### 4.2 Terminology & acronym reviewer (`reviewers/terminology-acronyms.md`)

Owns the index machinery. Checks (bidirectional enforcement, mirroring the citation reviewer):

- Every acronym is **defined on first use** in the body **and** present in the **Acronyms**
  index.
- Every specialized term is present in the **Glossary**, defined accessibly.
- **Nothing used-but-undefined; nothing defined-but-unused** (orphan entries flagged).
- **Consistency:** no synonym drift; acronyms expanded consistently.
- The Acronyms index and Glossary sections **exist** (absence is a `major` — see §4.5).

### 4.3 Accessibility / background reviewer (`reviewers/accessibility-background.md`)

Owns the generalist floor — the reader-facing twin of the expertise gate (§7). Checks:

- Can the expected reader **navigate** via abstract + glossary + background pointers?
- Identify concepts that require prior background **beyond** the reader's level.
- For each, supply a **verified, resolvable source**, **or** a clearly-marked **topic / keyword
  suggestion when none can be verified** — **never fabricate a citation.** (Anti-fabrication: a
  suggested reading that cannot be verified is downgraded to "a topic to read up on," not
  presented as a citation. This keeps the citation-integrity reviewer from rightly flagging it.)
- Quality/coverage of the optional Background section, if present.

### 4.4 Earned-jargon and defer-to-correctness

All three reviewers **defer to correctness** when they cannot reach consensus with the
correctness reviewers. A readability suggestion must never reduce precision or correctness; when
plainness and precision conflict, the suggestion is reframed as *"define the term"* rather than
*"remove the term,"* and any genuine disagreement is surfaced to the meta-editor (not averaged
away), per the integrity stance.

### 4.5 Severity policy

- Readability findings are normally **`minor`** (deferrable).
- They may rise to **`major`** for **completeness failures only**:
  - an acronym/term used but **never defined** or **missing from the index**, or
  - the paper **lacks a required reader-facing section** (Acronyms index / Glossary), or an
    abstract that fails the plain-language bar badly enough to mislead.
- **Never `blocker`** — correctness/integrity reviewers own blockers.

### 4.6 Paper template additions (`scientific-study/references/repo-layout.md`)

To `paper.md`, **at the bottom**, add: an **Acronyms** index, a **Glossary**, and an optional
**Background / further reading** section. The **abstract** stays where it is and carries the
plain-language summary role. Update the README `Contents` list accordingly. Note in the template
that suggested readings must be verified sources or explicitly-marked topic suggestions.

### 4.7 A's file-change map

- New: `reviewers/plain-language.md`, `reviewers/terminology-acronyms.md`,
  `reviewers/accessibility-background.md`.
- `scientific-peer-review/SKILL.md` — add the three reviewers as the readability tier; state when
  the tier runs.
- `review-report-format.md` — note the readability severity policy.
- `scientific-study/references/repo-layout.md` — `paper.md` template additions + README contents.

---

## 5. Subsystem D — Cycle snapshots

**Goal:** let a reader compare the iterations the reviewers produced — diff cycle-to-cycle and
against the final — **without git**. Git stays as-is (per-cycle commits) for the rare case of
tracing back to code/asset changes; that is the exception, not the optimized path.

- After each review cycle, copy the exact reviewed `paper.md` to **`review/cycle-N-paper.md`**,
  beside the existing report **`review/cycle-N.md`**.
- `review-loop.md` — add the snapshot step to each cycle.
- `repo-layout.md` — document `review/cycle-N-paper.md`; update README `Contents`.

**Synergy with B:** these snapshots are the diff the meta-editor reasons over for incremental
re-engagement.

---

## 6. Subsystem B — Incremental re-engagement

**Problem:** today the study loop re-invokes the full panel "fresh each cycle," so a reviewer who
found nothing still re-reviews everything next cycle — wasteful.

**Mechanism (meta-editor-driven, empathy-based):**

1. Each reviewer file gains a short **`Interests`** line — what that reviewer cares about — so the
   meta-editor can model their tendencies. (Explicit and cheap beats inferred.)
2. From cycle 2 on, for each reviewer with **no open findings**, the meta-editor:
   - looks at the **diff since that reviewer's last pass** (using the cycle snapshots, §5),
   - judges via the `Interests` profile whether the changes plausibly touch that reviewer's
     concerns,
   - poses a **specific** question to the reviewer: *"Given these changes [diff summary], and that
     you care about X, do you need a full re-review?"*,
   - **re-engages fully only on "yes."**
3. Reviewers **with open findings** are re-engaged normally to verify resolution.
4. **Coverage disclosure** (integrity stance §4): the meta-editor records, per reviewer per
   cycle, one of `full re-review | consulted, declined (prior verdict carried forward) |
   re-engaged due to changes`. A carried-forward verdict is a real prior verdict plus an explicit
   "no re-review needed" consult — **not** a fabricated check.

**Scope:** this applies in the multi-cycle study loop, where prior-cycle state exists. A
standalone `scientific-peer-review` invocation (no prior state) runs the full panel as today.

**B's file-change map:**

- `reviewers/*.md` — add an `Interests` line to each.
- `meta-editor.md` — incremental triage logic + the interest-driven consult + coverage recording.
- `scientific-study/references/review-loop.md` — make the loop **stateful**: pass prior findings +
  the snapshot diff into the review so the meta-editor can triage instead of always re-running all.
- `review-report-format.md` — per-reviewer coverage line.

---

## 7. Subsystem C — Expert system

Two parts: a **new standalone skill** that owns reusable experts, and **research-side hooks** that
let the review flow request and use experts.

### 7.1 New skill: `ask-an-expert`

`plugins/madskillz/skills/ask-an-expert/`. Purpose: define, maintain, and **query** reusable
domain-expert personas — usable **directly**, with no study or review involved ("I just want to
ask an expert a question").

Owns:

- **`experts/<concise-name>.md`** — the reusable expert library (e.g.,
  `experts/condensed-matter-physics.md`, `experts/survival-analysis.md`). Filename = the
  expertise. Each persona: role header, **credentials/scope** (what they're qualified to judge),
  **boundaries** (what's outside their expertise), how to engage (inputs, question types), output
  format.
- **`references/find-the-right-expert.md`** — the **finder** ("Find the right expert"): reads a
  request, critically derives the *actual* expertise required (looks past the surface ask),
  checks `experts/` to **avoid duplication** (reuse if covered), and if genuinely missing,
  **defines** a new `experts/<name>.md` (or **updates** an existing one).
- **`references/expert-format.md`** — the expert persona format spec.

### 7.2 Request artifact: `requested-expert.md`

Transient. Written when a domain gap is detected. Contains: the domain/topic, **why** it's needed
(which claims/sections), and the specific questions the panel needs answered. It is the finder's
input.

### 7.3 Research-side integration (peer-review + study)

- **Lightweight domain-coverage triage** at review start (in the peer-review orchestrator /
  meta-editor): does the panel cover the paper's domain(s)? If not → write `requested-expert.md`.
- **Escalation:** any reviewer may flag "out of my depth on X," feeding `requested-expert.md`.
- **Gate:** if `requested-expert.md` exists, the flow invokes `ask-an-expert`'s finder to resolve
  it — reuse or mint — then adds the expert to the panel as an additional reviewer for that
  domain and proceeds. Minting is **auto-continue** (no human checkpoint).
- **Disclosure:** the report notes which experts were consulted/minted and any residual gap/halt.

### 7.4 Adversarial gate on minted/updated experts (one shot, no loop)

To stop a model from waving a fabricated "expert" past the panel — and to avoid an
adversarial↔finder ping-pong:

1. The **adversarial reviewer challenges** the minted/updated expert's claimed credentials/scope.
2. If a gap is found, the **finder gets exactly one** update to close it.
3. Adversarial **re-checks once**:
   - satisfied → proceed;
   - gap remains → adversarial **notes** the residual gap (**no further rounds**);
   - gap is **egregious and blocks the study** → **stop and note the issue** (fail-closed halt,
     recorded like a compliance halt).

### 7.5 C's file-change map

- New skill `ask-an-expert/`: `SKILL.md`, `references/expert-format.md`,
  `references/find-the-right-expert.md`, `experts/` (library; seeded empty or with one example),
  and the `requested-expert.md` format (documented in the skill).
- `scientific-peer-review/SKILL.md` — domain-coverage triage; reviewer escalation; invoke finder;
  add minted expert to the panel; run the adversarial expert challenge; halt-if-egregious.
- `reviewers/adversarial.md` — add "challenge a minted expert's credentials" capability.
- `scientific-study/references/review-loop.md` (and/or `SKILL.md`) — the `requested-expert.md`
  gate: resolve via `ask-an-expert`, then resume; disclosure in the PR body.
- Possibly `commands/research.md` — mention the expert capability.

---

## 8. Cross-cutting integrity

Every new agent obeys the existing integrity stance: no fabricated verdicts/verifications/
citations; state coverage; surface disagreement; correctness outranks presentation. The two new
fabrication risks are explicitly guarded:

- **Suggested reading** (accessibility reviewer) → verify, or mark as a topic suggestion, never a
  citation.
- **Minted-expert credibility** (expert system) → adversarial challenge + one-shot repair +
  fail-closed halt on egregious gaps.

## 9. Open questions / residual risks

- **Reviewer `Interests` lines:** authored explicitly per reviewer (chosen) vs meta-editor
  inference. Explicit is cheaper and more reliable.
- **Diff granularity for B:** raw snapshot diff vs a meta-editor-produced summary. Lean: the
  meta-editor summarizes the snapshot diff for the consult.
- **Hallucinated expertise:** the adversarial gate mitigates but cannot fully eliminate the risk
  that an auto-minted expert is shallow. Accepted residual risk; surfaced in disclosure.
- **`ask-an-expert` standalone UX:** a `/ask-expert` command could come later; out of scope for
  the first pass.

## 10. Implementation sequencing

A (readability tier) → D (cycle snapshots) → B (incremental re-engagement) → C (expert system).
Each subsystem becomes its own implementation plan via the writing-plans skill, starting with A.
