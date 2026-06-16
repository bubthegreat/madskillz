# Design: `scientific-peer-review` — Adversarial multi-reviewer panel for research drafts

**Document type:** Build spec (input to writing-plans → implementation)
**Target artifact:** A Claude Code skill, directory `scientific-peer-review`, in `plugins/madskillz/skills/`
**Status:** Draft for review — 2026-06-16
**Parent vision:** `scientific-research-skill.md` (the full research-lifecycle north-star, now decomposed into a family — see §0)

---

## 0. Decomposition decision (why this doc exists)

The original spec (`scientific-research-skill.md`) packed the entire research lifecycle —
premise validation, experimental design, execution, statistics, drafting, peer review, and
reproducibility packaging — into one `scientific-method` skill. That is larger than every
other skill in this plugin combined, mixes LLM-native judgment work with risky bespoke
statistics code, and would rarely fire all at once.

**Decision:** decompose into a composable family of `scientific-*` skills and build the
highest-value, most self-contained slice first. The family:

| Skill | Owns | Status |
|---|---|---|
| **scientific-peer-review** | Adversarial panel + meta-editor adjudication | **This doc — build first** |
| scientific-writeup | Drafting, provenance tagging (`[CITED]/[DATA]/[SPECULATION]`), required sections, citations | Future |
| scientific-design | FINER/PICO, hypotheses, pre-registration, power analysis | Future |
| scientific-analysis | Statistics reference + (reference-guided) analysis | Future |
| scientific-repro | Env capture + reproducibility package | Future |

A shared `research-integrity` reference (the original §3 prime directive) may be extracted
once a second skill needs it. For v1, peer-review carries its integrity stance inline (§3),
because the Ethics-integrity and Citation-integrity reviewers already embody it.

The parent doc is retained as the family roadmap. This doc is what we build next.

---

## 1. Purpose & scope

Take a draft scientific paper or study and run it through an **adversarial,
multi-reviewer peer-review panel**, then synthesize the panel into **one adjudicated,
severity-ranked revision plan**. The goal: tell an author exactly what a tough,
fair external reviewer would say — *before* they submit.

This is the heart of the parent spec's "make peer review real and adversarial, not a
rubber stamp," carved out as a self-contained skill because its only required input is a
draft, it is pure LLM judgment (no bespoke statistics engine to get wrong), and it
exercises the subagent-orchestration the rest of the family will reuse.

### 1.1 Scope Contract

```
In:   - Reviewing a provided draft + whatever supporting artifacts exist
        (prereg, analysis outputs, code/repro package, reference list).
      - Producing per-reviewer structured reports.
      - Adjudicating them into ONE ranked revision plan with surfaced disagreements.
      - Honest disclosure of which checks could not run for lack of inputs.

Out:  - Writing or revising the paper. The deliverable is a plan; the human (or a
        future scientific-writeup skill) applies it. (Re-review = run this skill again.)
      - The full convergence LOOP (revise → re-run → repeat until no blockers).
        v1 is a single review pass.
      - Running experiments, doing the statistics, or generating citations/data.
      - Premise validation, pre-registration, power analysis (→ scientific-design).
      - The provenance-tagging lint, check_claims.py (→ scientific-writeup).

Boundaries:
      - One pass, one revision plan, then STOP and hand back to the human.
      - Reviewers read and judge; they never edit the manuscript.
      - The panel never fabricates a verification it could not perform.

At boundary (refuse with guidance, never best-effort guess):
      - No draft supplied → ask for the draft; do not review a description from memory.
      - A reviewer's required inputs are missing → run the checks it CAN, and report the
        rest as "not assessable: <missing input>" instead of guessing a verdict.
      - Asked to also revise/rewrite → state that's out of scope here and point to
        applying the plan manually (or the future scientific-writeup skill).

Amendments: <dated, partner-approved scope changes>
```

---

## 2. Skill metadata

```yaml
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
```

The description is deliberately pushy and lists trigger phrases, per the parent spec's
intent: this should fire whenever publication-grade scrutiny is wanted.

---

## 3. Integrity stance (condensed prime directive)

The skill body opens with these, and the reviewers enforce them:

1. **Never fabricate a verdict or a verification.** If a check can't be performed
   (missing input, no network to resolve a DOI), say so — never report it as passed.
2. **No silent citation pass.** An unverifiable reference is flagged
   "verification pending / could not resolve," not asserted as verified (§7).
3. **Surface, don't smooth.** Genuine reviewer disagreement is signal; the meta-editor
   reports the split for the human to adjudicate — it never averages it away.
4. **The review is honest about its own coverage.** Every run states which reviewers ran,
   which inputs were present, and which checks were therefore skipped (§8.3).
5. **Integrity and correctness outrank presentation** in every adjudication conflict.

---

## 4. Inputs & graceful degradation

The skill collects whatever the user has. Only the draft is required.

| Input | Required? | If absent |
|---|---|---|
| Draft manuscript | **Yes** | Refuse: ask for the draft (Scope Contract boundary) |
| Pre-registration | No | Consistency can't verify confirmatory/exploratory labels → reports that gap |
| Analysis outputs / results tables | No | Statistical reviews as-reported; flags numbers as untraceable |
| Code / reproducibility package | No | Reproducibility assesses described methods only; rates "conceptual" ceiling |
| Reference list / bibliography | No (extract from draft) | Citation works from in-text cites; resolution may be limited |
| Network / web tools | Auto-detect | Citation flags identifiers "verification pending" instead of resolving |

**Rule:** every reviewer declares its required inputs in its rubric and degrades by
*narrowing what it claims*, never by guessing. Missing inputs become explicit limitations
in that reviewer's report and roll up into the coverage statement (§8.3).

---

## 5. The reviewer roster (v1: 6 + meta-editor)

These are exactly the blocker-bearing reviewers from the parent spec's convergence gate.
Each runs with **only its own rubric in context** plus the manuscript and available inputs,
and returns the standard report shape (§8.1).

| Reviewer | File | Mandate (one line) |
|---|---|---|
| **Adversarial** ("Reviewer 2") | `reviewers/adversarial.md` | Attack the weakest points: alternative explanations, overclaiming, unsupported causal language, cherry-picked baselines, premise/framing gaps. |
| **Reproducibility** | `reviewers/reproducibility.md` | Try to reproduce it as a stranger from what's given; flag every missing seed/version/parameter/step; rate conceptual / runnable / bit-for-bit and name what blocks the next level. |
| **Internal consistency** | `reviewers/consistency.md` | Check the paper against itself: abstract vs. results, numbers across text/tables/figures, every hypothesis answered, conclusion within scope, confirmatory/exploratory labels preserved. |
| **Statistical / methodological** | `reviewers/statistical.md` | Right test for the design? Assumptions checked? Effect sizes + CIs? Multiple comparisons corrected? Power adequate? p-hacking / optional stopping / garden-of-forking-paths? Matches the prereg plan? |
| **Ethics & integrity** | `reviewers/ethics-integrity.md` | IRB/IACUC status, privacy/consent, dual-use/harm, conflicts; any sign of fabricated data, plagiarism, or hallucinated content. **Can issue a hard veto.** |
| **Citation-integrity** | `reviewers/citation-integrity.md` | Every reference resolves to a real identifier, is correctly attributed, and actually supports its specific claim. Both directions: no orphan cites, no orphan entries. Unverifiable = blocker, never silent pass (§7). |
| **Meta-editor** (handling editor) | `reviewers/meta-editor.md` | Synthesize all reports into one adjudicated, deduplicated, severity-ranked revision plan; surface genuine disagreements; hold the accept/revise/reject call. Does not write the paper. |

**Deferred — the communication tier (opt-in, future):** Clarity/communication editor,
Plain-language reviewer, Domain/novelty reviewer. These produce deferrable `minor` findings
(and Domain/novelty needs literature search). They add back cheaply when a draft is nearly
done; v1 leaves them out to stay focused on correctness. The skill states which tier ran.

---

## 6. Orchestration

`SKILL.md` drives the panel; it does not implement a workflow script.

1. **Gather inputs** (§4); detect environment (subagents available?) and tool availability
   (network for citation resolution?).
2. **Fan out the 6 reviewers as parallel subagents** (reuse
   `superpowers:dispatching-parallel-agents`). Each subagent is told to read only its own
   rubric file and is handed the manuscript + available inputs. Independent context is what
   makes the reviews genuinely independent.
   - **Environment branch:** where subagents aren't available (e.g. claude.ai), run each
     reviewer sequentially in a fresh framing, adopting one rubric at a time and not looking
     at prior reviewers' reasoning. Disclose the weaker independence in the output.
3. **Meta-editor synthesis** runs after all reviewers return, reading every report:
   dedupe, resolve conflicts (integrity/correctness wins), rank by severity, surface
   genuine disagreements, emit one ordered revision plan + the accept/revise/reject call.
4. **Emit the deliverable** (§8) and stop.

Cost note: v1 is one pass = 6 reviewers + 1 meta-editor = 7 subagent runs. No loop.

---

## 7. Citation verification (reuse, don't rebuild)

The Citation-integrity reviewer does **not** ship a `verify_citations.py`. Instead:

- **Internal checks (always):** every in-text citation has a matching reference entry and
  vice-versa; each reference carries a well-formed identifier (DOI/arXiv/ISBN/URL); the
  cited work plausibly supports the specific claim it's attached to (not just topically).
- **Resolution (when tools exist):** verify identifiers actually resolve, via web tools or
  by delegating to the existing `deep-research` skill's fetch/verify machinery.
- **When tools are unavailable:** flag each unresolved reference as
  "verification pending — could not resolve" and say so in the coverage statement. The
  citation check **never reports a silent pass** (§3.2). This is the parent spec's
  "no internet to verify citations" edge case, honored.

---

## 8. Output

### 8.1 Per-reviewer report shape
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

### 8.2 Meta-editor deliverable
- Per-reviewer recommendation summary.
- **Surfaced disagreements:** where reviewers materially conflict (e.g. Adversary says
  reject, another says accept), state the split and let the human adjudicate.
- **One ordered revision plan:** deduplicated findings, ranked blocker → major → minor,
  each tagged with the originating reviewer(s) and the required change.
- Overall call: accept / minor / major / reject.

### 8.3 Coverage statement (the honesty mechanism)
A short header on the deliverable: which reviewers ran (and which tier), which inputs were
present, which checks could not be performed and why, and whether reviews were independent
(parallel subagents) or sequential (weaker independence disclosed).

---

## 9. Skill file & directory structure

Progressive disclosure: lean `SKILL.md` orchestrator; each reviewer rubric in its own file
so a reviewer subagent loads only its own role.

```
scientific-peer-review/
├── SKILL.md                       # integrity stance, inputs, dispatch, meta-editor, output
├── references/
│   ├── review-report-format.md    # the §8.1 report shape + §8.2 meta-editor deliverable
│   └── reviewers/
│       ├── adversarial.md
│       ├── reproducibility.md
│       ├── consistency.md
│       ├── statistical.md
│       ├── ethics-integrity.md
│       ├── citation-integrity.md
│       └── meta-editor.md
└── evals/
    └── evals.json
```

`SKILL.md` stays lean and points into `references/` per step.

---

## 10. Edge cases the skill must handle

- **No draft** → ask for it; never review from a verbal description.
- **Draft only, nothing else** → run all six on what's there; coverage statement makes the
  thinness explicit; Reproducibility/Statistical narrow their claims accordingly.
- **No network** → citation resolution flagged pending, not passed.
- **Ethics red flag** (human subjects without approval, dual-use, fabrication signs) →
  Ethics-integrity raises a blocker/veto; surfaced prominently in the deliverable.
- **Reviewers disagree** → meta-editor surfaces the split, does not average it.
- **User asks to also rewrite** → out of scope; point to applying the plan / future writeup skill.
- **claude.ai (no subagents)** → sequential reviews, reduced independence disclosed.

---

## 11. Evals (`evals/evals.json`)

Seed with prompts substantive enough to actually trigger and exercise the panel:
1. "Here's a draft — run it through peer review and tell me what a tough reviewer would say."
2. "Review this study for statistical problems; are the effect sizes and corrections right?"
3. "Are the citations in this paper real and do they support the claims?"
4. "Is this ready to submit? What would block it?"
5. A draft with a *planted* flaw (e.g. a hallucinated citation, an uncorrected multiple-
   comparison family, a conclusion outside the stated scope) — grade on whether the right
   reviewer catches it.

Grade on: all six reviewer reports produced; each finding has severity + location +
required change; planted flaws caught by the correct reviewer; unverifiable citations
flagged not passed; a single ranked revision plan emitted; coverage statement honest about
skipped checks; no fabricated verdicts.

---

## 12. Open items for the build (carry into writing-plans)

- Exact rubric content for each of the 7 reviewer files (the heavy authoring work).
- Precise wording of the `deep-research` hand-off for citation resolution.
- Whether `research-integrity` is extracted to a shared reference now or when skill #2 lands
  (recommendation: defer until skill #2 needs it).

---

*End of focused spec. Everything not listed in §1.1 In/Out is deferred to a later family
member or to v2.*
