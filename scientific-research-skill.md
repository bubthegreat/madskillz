# Specification: `scientific-method` — A Claude Code Skill for Rigorous Research & Paper Generation

**Document type:** Build specification (input to skill-creator or to a Claude agent that will author the skill)
**Target artifact:** A Claude Code skill, directory name `scientific-method`
**Version:** 1.0 (draft for review)

---

> **Status update (2026-06-16) — decomposed into a family.** This document is too large to
> build as one skill (bigger than the rest of the plugin combined) and mixes LLM-native
> judgment with risky bespoke statistics code. Decision: build a composable family of
> `scientific-*` skills instead, highest-value self-contained slice first. This doc is now
> the **family roadmap / north-star vision**, not the next build target.
>
> Family: **scientific-peer-review** (build first), scientific-writeup, scientific-design,
> scientific-analysis, scientific-repro, with a shared `research-integrity` reference
> extracted when a second skill needs it.
>
> The first skill's focused, buildable spec lives at
> `docs/superpowers/specs/2026-06-16-scientific-peer-review-design.md`.

---

## 0. How to read this spec

This document tells a skill author *what to build* and *why each piece matters*. It is intentionally prescriptive about the non-negotiable rigor mechanisms (integrity, claim provenance, statistical correctness, peer-review subagents) and deliberately leaves room for judgment on cosmetic choices (exact citation style, template wording). Sections marked **[GATE]** are hard quality gates the skill must enforce and must not let a draft pass without satisfying. Sections marked **[DECIDE]** flag choices the user/author should make before generation.

The single most important property of this skill is **epistemic honesty**: it must never invent data, results, citations, or authors. A scientific-paper generator that fabricates is worse than useless — it produces convincing fraud. Every other requirement is downstream of that one.

---

## 1. Purpose & scope of the skill

The skill enables Claude to take a research idea from a raw premise through to a **draft-ready, reproducible scientific paper** that is genuinely ready for real external peer review. It covers the full lifecycle:

1. Validating that the premise is sound and the scope is bounded.
2. Designing an experiment (or analysis) with pre-specified hypotheses and analysis plan.
3. Actually running the experiment (executing code, capturing data and environment) when the study is computational/empirical, or structuring data collection when it is not.
4. Performing statistically correct analysis.
5. Writing the paper in a recognized structure with correct formatting and citations.
6. Subjecting the draft to a panel of adversarial peer-review subagents.
7. Revising against the reviews and producing a reproducibility package.

**In scope:** Computational experiments, simulations, data-analysis studies, reproductions/replications, and the write-up of empirical results the user supplies. Theory/methods papers where the "experiment" is a proof or derivation.

**Out of scope (the skill should refuse or flag, not fake):** Human-subjects or animal studies requiring real IRB/IACUC approval and real participants — the skill can help *design and document* these but must not pretend data was collected. Wet-lab results it cannot actually produce. Any request to "make the results come out a certain way."

---

## 2. Goals and non-goals

**Goals**
- Produce papers where every claim is traceable to evidence, a citation, or an explicitly-flagged speculation.
- Bake in the practices that prevent the most common forms of bad science (HARKing, p-hacking, selective reporting, citation padding, overclaiming, irreproducibility).
- Make the peer-review step real and adversarial, not a rubber stamp.
- Make every result reproducible by a stranger from the package alone.

**Non-goals**
- Not a citation-manager replacement (it integrates with one, see §10.4).
- Not a substitute for genuine domain expertise or real IRB review.
- Not a tool for generating volume; it optimizes for one defensible paper, not many plausible ones.

---

## 3. Prime directive — research integrity **[GATE]**

The skill body must open with these rules, stated plainly, and the gates must enforce them:

1. **No fabricated data.** Results come only from a real execution, a user-supplied dataset, or a clearly-labeled simulation whose synthetic nature is disclosed in-text. Never invent numbers to fill a table.
2. **No fabricated or hallucinated citations.** Every reference must resolve to a real work with a verifiable identifier (DOI, arXiv ID, ISBN, or stable URL). A citation that cannot be verified is removed, not guessed. (Enforced by the Citation-Integrity reviewer, §11.6.)
3. **No invented co-authors or contributions.** Author lists and contribution statements come from the user. The skill does not add names.
4. **No selective reporting.** All pre-registered outcomes are reported, including null and negative results. Dropping an analysis requires a stated, defensible reason.
5. **Provenance on every claim** (see §9). A sentence is either supported, derived from this study's data, or marked speculation with caveats. There is no fourth category.
6. **Disclose the assistant's role.** The methods or acknowledgments must state that an AI system assisted with drafting/analysis, per current journal norms. The skill does not hide its own involvement.

If a user instruction conflicts with any of these, the skill surfaces the conflict and declines the fabricating part while still helping with the legitimate remainder.

---

## 4. Skill metadata

```yaml
name: scientific-method
description: >
  Design, run, analyze, and write up rigorous, reproducible scientific studies,
  and put the draft through an adversarial multi-reviewer peer-review process.
  Use this whenever the user wants to produce a research paper, run an experiment,
  validate a hypothesis, do a statistical analysis intended for publication,
  write up empirical or computational results, reproduce a prior study, or get a
  draft "peer-review ready." Trigger even if the user only says things like
  "write up these results," "design an experiment to test X," "is this study
  sound," "run a power analysis," or "draft a methods section" — anything that
  should meet scientific publication standards rather than casual analysis.
```

The description is deliberately "pushy" and lists trigger phrases, because this skill should fire whenever publication-grade rigor is wanted, not only when the user says the word "paper."

**[DECIDE]** Default reporting target: pick whether the skill defaults to a journal-article format or a conference/preprint (arXiv) format when the user doesn't specify. Recommend defaulting to a generic IMRaD journal article and asking once.

---

## 5. Skill file & directory structure

The skill uses progressive disclosure: a lean `SKILL.md` body that orchestrates, with the heavy detail in `references/` loaded only when each phase runs.

```
scientific-method/
├── SKILL.md                      # Orchestrator: the 8 phases, the gates, when to read what
├── references/
│   ├── premise-and-scope.md      # FINER/PICO, scoping, lit-grounding, operationalization
│   ├── experimental-design.md    # study types, power analysis, randomization, blinding
│   ├── preregistration.md        # the pre-reg template + how to fill it
│   ├── statistics.md             # test selection tree, assumptions, effect sizes, corrections
│   ├── claim-provenance.md       # the tagging system + speculation caveat rules
│   ├── paper-structure.md        # IMRaD section-by-section, what belongs where
│   ├── reporting-guidelines.md   # CONSORT/PRISMA/ARRIVE/STROBE/TRIPOD selector
│   ├── citations.md              # APA7/Vancouver/IEEE/Chicago formats, references page, CRediT
│   ├── reviewers/                # one rubric file per reviewer role (see §11)
│   │   ├── adversarial.md
│   │   ├── reproducibility.md
│   │   ├── consistency.md
│   │   ├── statistical.md
│   │   ├── ethics-integrity.md
│   │   ├── domain-novelty.md
│   │   ├── citation-integrity.md
│   │   ├── clarity-editor.md
│   │   ├── plain-language.md
│   │   └── meta-editor.md
│   └── reproducibility-package.md # what ships, README-to-reproduce contract
├── scripts/
│   ├── capture_env.py            # records OS, lib versions, seeds, hardware, git hash
│   ├── run_experiment.py         # seeded harness wrapper + structured logging
│   ├── analyze.py                # assumption checks, tests, effect sizes, CIs, corrections
│   ├── power_analysis.py         # a-priori sample-size / MDE calculator
│   ├── verify_citations.py       # resolves DOIs/arXiv IDs, flags unverifiable refs
│   ├── check_claims.py           # lints the manuscript for untagged assertions
│   └── make_package.py           # assembles the reproducibility bundle
├── assets/
│   ├── preregistration.template.md
│   ├── paper.template.md         # IMRaD skeleton with all required statements
│   ├── response-to-reviewers.template.md
│   ├── data-availability.snippet.md
│   ├── credit-statement.snippet.md
│   ├── decision-log.template.md     # human-decision audit trail (see §7.5.5)
│   └── reference-styles/         # .csl files for the supported citation styles
└── evals/
    └── evals.json                # test prompts (see §16)
```

`SKILL.md` stays under ~500 lines and points into `references/` per phase. The reviewer rubrics live in their own files so a reviewer subagent loads only its own role.

---

## 6. The workflow — eight phases

`SKILL.md` drives these in order, with gates between them. Each phase says which reference file to read first.

### Phase 1 — Premise & scope validation **[GATE]**
*Read `references/premise-and-scope.md`.*
- Force the research question through **FINER** (Feasible, Interesting, Novel, Ethical, Relevant) and frame it as **PICO/PECO** (Population, Intervention/Exposure, Comparator, Outcome) where applicable.
- Ground in literature: search for whether the question is already answered; capture the gap the study fills. If the gap can't be articulated, stop and tell the user.
- **Operationalize** every construct: each abstract variable gets a concrete, measurable definition and unit.
- State the scope boundaries explicitly — what populations, conditions, and claims are *in* and what is deliberately *out*. The "out" list is what keeps later sections from overreaching.
- Gate: cannot proceed without a one-paragraph problem statement, a stated gap, operational definitions, and an explicit scope boundary.

### Phase 2 — Hypotheses & pre-registration **[GATE]**
*Read `references/preregistration.md`; fill `assets/preregistration.template.md`.*
- State H₀ and H₁ for each question, directional where justified.
- Pre-specify the **analysis plan** before any data is seen: primary vs. secondary outcomes, the exact statistical test for each, the alpha, the multiple-comparison correction, and stopping rules.
- Mark which analyses are **confirmatory** (locked) vs. **exploratory** (allowed but labeled as such forever after). This is the single biggest defense against p-hacking and HARKing.
- Gate: a frozen pre-registration document exists before Phase 4 runs.

### Phase 3 — Experimental design
*Read `references/experimental-design.md`.*
- Select study type (RCT, factorial, observational/cohort, simulation, benchmark, computational ablation, replication, etc.).
- Run an **a-priori power analysis** (`scripts/power_analysis.py`): determine sample size / minimum detectable effect for the chosen alpha and target power (default 0.8). Underpowered designs are flagged, not silently run.
- Specify randomization, blinding, controls, confounder handling, inclusion/exclusion criteria, and a missing-data plan.
- For computational work, specify seeds, configurations, and the metric definitions up front.

### Phase 4 — Execution
*Use `scripts/run_experiment.py` + `scripts/capture_env.py`.*
- Run the experiment under a fixed seed with structured logging of every run.
- Capture the full environment: OS, language and library versions, hardware, git commit hash, and all seeds. This artifact is non-negotiable for reproducibility.
- Preserve raw outputs untouched; analysis reads copies, never mutates the raw record.
- If the study is not computational, this phase instead structures and validates user-supplied data and records its provenance.

### Phase 5 — Statistical analysis **[GATE]**
*Read `references/statistics.md`; use `scripts/analyze.py`.*
- Select tests via the decision tree in the reference (by data type, design, and number of groups), then **check the assumptions** of each test (normality, homoscedasticity, independence, etc.) and switch to nonparametric/robust alternatives when violated — documenting the switch.
- Report, for every result: the **effect size with its confidence interval**, not just a p-value. Distinguish statistical from practical significance.
- Apply the pre-registered **multiple-comparison correction** (e.g., Benjamini–Hochberg FDR or Bonferroni) across the family of tests.
- Run the pre-registered sensitivity / robustness checks.
- Never "accept the null"; report inconclusive results as inconclusive.
- Gate: every reported number traces to a line in the analysis output; exploratory results are labeled exploratory.

### Phase 6 — Drafting
*Read `references/paper-structure.md`, `references/reporting-guidelines.md`, `references/citations.md`; fill `assets/paper.template.md`.*
- Write in IMRaD (see §10) with all required statements (limitations, future work, data availability, conflicts, funding, ethics, AI-assistance disclosure, CRediT contributions).
- Apply the **claim-provenance tagging system** (§9) to every assertion as it is written.
- Select and follow the appropriate **reporting guideline checklist** for the study type.

### Phase 7 — Adversarial peer review
*Spawn the reviewer panel (§11), each reading only its own rubric in `references/reviewers/`.*
- Each reviewer produces a structured report: severity-ranked findings, specific line/section references, and a recommendation (accept / minor revision / major revision / reject).
- The **meta-editor** synthesizes the panel into a single adjudicated revision plan (§11.10).

### Phase 8 — Revision & packaging
*Use `assets/response-to-reviewers.template.md`; `scripts/make_package.py`.*
- Address each reviewer finding with a specific response (changed text, or a reasoned rebuttal). Iterate Phases 7–8 until the convergence criteria (§12) are met.
- Assemble the reproducibility package (§13) and present it.

---

## 7. Orchestration note: subagents vs. single-agent

The reviewer "panel" is implemented as **subagents** in Claude Code / Cowork (parallel, independent context — which is what makes the adversarial reviews genuinely independent). In Claude.ai (no subagents), the skill runs each reviewer role **sequentially in a fresh framing**, explicitly adopting one rubric at a time and *not* looking at its own author-side reasoning. The independence is weaker there, so the skill should say so honestly. `SKILL.md` must branch on environment.

---

## 7.5 Human-in-the-loop checkpoints & workflow

The skill runs autonomously *between* checkpoints but stops at points where one of three things is true: **only the human has the information**, **proceeding wrong is costly or irreversible**, or **integrity is at stake**. Everywhere else it should keep moving rather than nagging — over-checkpointing trains the user to rubber-stamp, which defeats the purpose.

### 7.5.1 Human-only inputs (the skill never generates these)
The research premise itself; real experimental data (or explicit approval of clearly-labeled synthetic/simulated data *as* synthetic); the author list, author order, corresponding author, and per-person CRediT roles; funding sources and conflicts of interest; ethics/IRB/IACUC status; and any private datasets or credentials. The skill collects these; it does not invent them (ties to the prime directive, §3).

### 7.5.2 Hard checkpoints — blocking, require explicit human approval
| # | Checkpoint | Phase | What the human decides | Why it blocks |
|---|---|---|---|---|
| H1 | **Scope sign-off** | end of P1 | Approve the problem statement + in/out scope boundary; or **kill/pivot** if the lit review shows it's already answered | Cheapest place to stop a doomed study; the boundary governs every later overreach check |
| H2 | **Pre-registration freeze** | end of P2 | Lock H₀/H₁ + the analysis plan *before any data is seen* | The keystone anti-p-hacking / anti-HARKing gate. After freeze the plan is immutable except via a logged, approved amendment |
| H3 | **Plan-deviation approval** | P5+ | Approve any departure from the frozen plan (different test, dropped/added outcome, new exploratory analysis) | Silent deviation is how honest studies become p-hacked ones; exploratory additions get labeled exploratory *permanently* |
| H4 | **Revision-plan approval** | P7→P8 | Approve, or veto individual items in, the meta-editor's revision plan before auto-revision | Lets the human reject a reviewer suggestion they know is wrong, with logged rationale, instead of the skill blindly complying |
| H5 | **Release sign-off** | end of P8 | Explicitly confirm "peer-review ready" | Nothing is represented as ready or sent anywhere external without a human saying so |

### 7.5.3 Soft checkpoints — notify-and-pause, proceed on the documented default
Underpowered design detected (P3 → proceed only with ack, claims downgraded to exploratory); a statistical assumption violation forcing a test swap (P5 → proceed with the swap documented); an unverifiable citation (P6/P7 → human chooses flag-and-keep vs. remove); a null, negative, or surprising result (P5 → surfaced so the human isn't blindsided and can sanity-check); borderline speculation the provenance system can't cleanly classify (P6); and a reviewer loop that hasn't converged by the cap (P8 → hand the human a candid open-items status, §12).

### 7.5.4 Escalations — always stop, regardless of oversight level
Any detected pressure to **fabricate data, invent citations, or force a predetermined conclusion**, and any **ethics red flag** (human subjects without approval, dual-use/harm potential), halts the run and surfaces to the human. The skill neither silently complies nor silently abandons the whole job — it names the conflict and continues with the legitimate remainder once the human responds.

### 7.5.5 Workflow conveniences
- **Decision log / lab notebook** (`assets/decision-log.template.md`): every human decision — approval, veto, deviation, override, escalation response — is recorded with timestamp and rationale, and ships in the reproducibility package (§13). It is simultaneously good provenance and the audit trail a real reviewer (and future-you) can read.
- **Diff-based revision review:** when revising after peer review, present a **diff** (changed text + which reviewer finding each change addresses), not a fresh wall of prose, so the human can catch silent scope or claim drift.
- **Checkpointed, resumable runs:** long phases (execution, the reviewer panel) save state so the human can step away and resume; the skill reports progress rather than going dark.

### 7.5.6 Configurable oversight level **[DECIDE]**
Let the user choose how much the skill pauses:
- **Guided** — stop at every hard *and* soft checkpoint.
- **Standard** (recommended default) — stop at hard checkpoints + escalations; soft checkpoints notify but proceed on default.
- **Autonomous-draft** — run straight through to a draft, pausing only at H2 (pre-reg freeze), H5 (release sign-off), and escalations.

Non-negotiable across *all* levels: the pre-registration freeze (H2), the final release sign-off (H5), and the fabrication/ethics escalations (§7.5.4) can never be auto-skipped. Autonomy is allowed to remove convenience pauses, never integrity ones.

### 7.5.7 Additional checkpoints & workflows worth adding
These extend the taxonomy above rather than replace it; each notes where it slots.

- **Data-rights & provenance confirmation** *(new hard checkpoint, H6, at P4 intake).* Before any supplied dataset is incorporated, the human confirms they actually have the right to use it — license, consent, privacy/PII status, and source. Cheap to ask now, expensive to discover at submission. Pairs with the human-only inputs in §7.5.1.

- **Raw-data integrity gate, before analysis** *(soft, P4→P5).* An automated data-quality report — run completeness, missingness, value ranges, instrument/pipeline sanity — reviewed by the human *before* outcomes are analyzed. The question it answers is "is this data trustworthy," not "did it come out the way I wanted." Design rule: keep this strictly separate from and prior to outcome inspection so it can never double as outcome-driven data cleaning. A failed sensor or broken pipeline caught here saves analyzing garbage; caught later it looks like p-hacking.

- **Blinded analysis with controlled unblinding** *(workflow + soft gate, P5).* Where feasible, run the locked analysis pipeline with group/condition labels masked, so neither the skill nor the author can steer toward a preferred result, and have the human approve *unblinding only after the pipeline is frozen.* For computational studies this is nearly mechanical and is one of the strongest cheap defenses against unconscious result-shaping.

- **Design pre-mortem + pre-committed kill/withdraw criteria** *(workflow, end of P3; feeds H1/H2).* Before running, answer "assume this study finds nothing or fails to replicate — why?", and write down in advance the conditions under which the study would be abandoned or a claim withdrawn. Pre-committing to kill criteria removes the later temptation to rationalize a weak result into a publishable one.

- **Inter-reviewer disagreement surfacing** *(extends H4).* When reviewers materially conflict — e.g., the Adversary says reject while Domain says accept — the meta-editor must surface the split to the human rather than silently averaging it away. Genuine disagreement is signal; the human adjudicates it explicitly.

- **Make release sign-off an explicit author attestation** *(strengthens H5).* Rather than only "confirm peer-review ready," the named author attests in the first person to what the skill cannot vouch for: no fabricated data, every citation verified and supporting its claim, the contributor list and CRediT roles accurate, and "I stand behind these claims." The skill drafts; only a person can be the accountable author. This is the natural home for the integrity items the prime directive (§3) protects.

- **Adaptive checkpointing** *(extends the oversight levels, §7.5.6)* **[DECIDE]**. On top of the global Guided/Standard/Autonomous setting, let soft checkpoints fire *by stakes and confidence*: pause more when the model is uncertain (low-confidence test selection, borderline speculation, surprising effect sizes), less when everything is well-supported. This catches the risky cases without training the user to rubber-stamp the routine ones — the exact failure mode that flat, frequent checkpoints create.

---

## 8. Statistical rigor — required content of `references/statistics.md`

The reference must give the model enough to choose and run the right analysis, including:
- A **test-selection decision tree** keyed on: outcome type (continuous/ordinal/count/binary/time-to-event), number and pairing of groups, and design.
- For each test, its **assumptions and how to check them**, plus the robust/nonparametric fallback.
- **Effect-size catalog** (Cohen's d, Hedges' g, odds/risk ratios, η²/ω², r, etc.) with which goes with which test, and how to compute the CI.
- **Multiple-comparison** methods and when to use family-wise (Bonferroni/Holm) vs. FDR (Benjamini–Hochberg).
- **Power analysis** guidance feeding `scripts/power_analysis.py`.
- A "**common fallacies**" list to actively avoid: accepting the null, p-hacking, optional stopping, HARKing, base-rate neglect, confusing significance with magnitude, pseudoreplication, garden-of-forking-paths.
- Guidance on when **Bayesian** reporting (credible intervals, Bayes factors) is the better frame, offered as an option.

---

## 9. Claim-provenance system — required content of `references/claim-provenance.md` **[GATE]**

This is the mechanism behind the user's core requirement: *every statement is grounded, or flagged as speculation with caveats.* The skill tags each assertion in the draft as exactly one of three kinds. Tags are an inline, machine-checkable **drafting** mechanism (`scripts/check_claims.py`); in the **published** manuscript they are rendered to standard scholarly form — never shown as raw tags or a `[C]/[D]/[A]` legend (see the citation, cross-reference & provenance conventions in `scientific-study`'s `references/repo-layout.md`).

| Tag (drafting) | Meaning | Requirement | Published rendering |
|---|---|---|---|
| `[CITED: ref-key]` | Supported by external prior work | Must point to a verified reference (§11.6). | A numbered `[N]` citation (default house style; the citation-integrity reviewer may switch to author–date by field). |
| `[DATA: result-ref]` | A finding from *this* study's analysis | Must trace to a specific table/figure/line in the analysis output. | A pointer to the **Figure/Table** that shows the value, e.g. "(Figure 3)". |
| `[SPECULATION: …]` | Interpretation, conjecture, or inference not provable from the data | Must carry the caveat block below. | **Hedged prose in the Discussion**, still carrying its caveat reasoning (feeds Future Work). |

A modelling/analysis **assumption** (not one of the three tags above) renders as explicit **prose** in Methods, paired with a sensitivity analysis where possible.

**Speculation caveat block — required fields whenever `[SPECULATION]` is used:**
1. **Why it matters in this study's context** — what question or result motivates raising it.
2. **Why we have crossed into conjecture** — the specific reason the data can't confirm or refute it (e.g., "the design lacks a control for X," "sample can't distinguish these mechanisms," "this is an inferred result we could neither prove nor disprove here").
3. **What would settle it** — the observation, experiment, or data that would move the claim from speculation to supported. (This feeds directly into the Future Work section, §10.3.)

Rule of placement: confirmatory claims live in Results; interpretation and speculation live in Discussion, never in Results. The skill enforces this separation. `scripts/check_claims.py` fails the gate if any declarative sentence in Results/Discussion lacks a tag, or if a `[SPECULATION]` lacks its three caveat fields.

---

## 10. Paper structure, formatting & attribution — `references/paper-structure.md`, `references/citations.md`, `assets/paper.template.md`

### 10.1 Structure (IMRaD + required statements)
Title · Structured abstract · Keywords · **Introduction** (background → gap → question → hypothesis) · **Methods** (reproducible detail: design, materials, procedure, analysis plan, environment) · **Results** (findings + statistics only, no interpretation) · **Discussion** (interpretation, comparison to literature, mechanisms) · **Limitations** (its own labeled section, §10.2) · **Future research / recommendations** (§10.3) · **Conclusion** · then the required statements:
- **CRediT author-contribution statement** (§10.5)
- **Acknowledgments** (incl. non-author collaborators)
- **Funding statement**
- **Conflict-of-interest / competing-interests statement**
- **Ethics statement** (IRB/IACUC status or "not applicable" with reason)
- **Data & code availability statement** (§13)
- **AI-assistance disclosure** (per §3.6)
- **References** (§10.4)

### 10.2 Limitations **[GATE]**
A dedicated section is mandatory and must honestly cover: internal validity threats, external validity / generalizability bounds, construct validity, statistical-power limits, sample/scope constraints, and known confounders left unaddressed. A paper with no stated limitations fails the gate — every real study has them.

### 10.3 Future research / recommendations **[GATE]**
A required section that turns the open questions and the "what would settle it" fields from every `[SPECULATION]` (§9) into concrete, prioritized next studies. Each recommendation states what it would resolve and roughly how.

### 10.4 Citations & references page — `references/citations.md`
- **[DECIDE]** Supported styles to ship as `.csl`: at minimum APA 7th, Vancouver (numeric), IEEE, and Chicago. Ask the user which; default APA 7.
- Every in-text citation has a matching references entry and vice-versa (the Citation-Integrity reviewer checks both directions).
- Each reference carries a resolvable identifier (DOI/arXiv/ISBN/stable URL).
- The references page is generated, not hand-typed, and validated by `scripts/verify_citations.py`.

### 10.5 Crediting collaborators — `assets/credit-statement.snippet.md`
Use the **CRediT taxonomy** (14 roles: Conceptualization, Data curation, Formal analysis, Funding acquisition, Investigation, Methodology, Project administration, Resources, Software, Supervision, Validation, Visualization, Writing – original draft, Writing – review & editing). The skill collects from the user, per collaborator, which roles they held, and renders the statement. **It never invents contributors or roles.** Non-author helpers go in Acknowledgments. Author *order* and corresponding-author designation are confirmed with the user, not assumed.

### 10.6 Reporting-guideline checklist — `references/reporting-guidelines.md`
Select and attach the right community checklist by study type: **CONSORT** (RCTs), **STROBE** (observational), **PRISMA** (systematic reviews/meta-analyses), **ARRIVE** (animal), **TRIPOD** (prediction models), and a generic computational-reproducibility checklist for ML/simulation work. The completed checklist ships as supplementary material.

---

## 11. The peer-review subagent panel — `references/reviewers/*`

Each reviewer runs independently with **only its own rubric in context** and the manuscript + analysis outputs + pre-registration as inputs. Each returns the same structured report shape:

```
Reviewer: <role>
Recommendation: accept | minor | major | reject
Findings (severity-ranked):
  - [severity: blocker|major|minor] [location: §/line/table]
    Issue: …
    Why it matters: …
    Required change: …
Questions for authors: …
```

The three the user explicitly asked for are the **Adversary**, the **Reproducer**, and the **Consistency** reviewer. The rest are the additional roles needed for a draft to actually survive real external review.

### 11.1 Adversarial reviewer ("Reviewer 2") — `adversarial.md`
Mandate: attack the paper at its weakest points. Challenge the premise and framing; hunt for **alternative explanations** of every result; probe for overclaiming, unsupported causal language, cherry-picked baselines, and gaps between what was shown and what was concluded. Ask "what would have to be true for this to be wrong?" Its job is to be the toughest fair reviewer the paper will ever face.

### 11.2 Reproducibility reviewer — `reproducibility.md`
Mandate: try to *actually reproduce* it from the package alone, as a stranger. Flag every missing seed, version, parameter, dataset, or undocumented step. Verify the environment capture is complete and the README-to-reproduce contract (§13) is honest. Rate reproducibility on a concrete scale (e.g., conceptual / runnable / bit-for-bit) and list exactly what blocks the next level.

### 11.3 Internal-consistency reviewer — `consistency.md`
Mandate: check the paper against *itself*. Do the abstract's claims match the results? Do numbers agree across text, tables, and figures? Does every hypothesis get answered? Does the conclusion follow from the data shown and stay inside the Phase-1 scope boundary? Are confirmatory vs. exploratory labels preserved from the pre-registration? Flag any internal contradiction.

### 11.4 Statistical / methodological reviewer — `statistical.md`
Mandate: validate the stats independently. Right test for the design? Assumptions checked? Effect sizes and CIs reported? Multiple comparisons corrected? Power adequate? Any p-hacking, optional stopping, or garden-of-forking-paths? Confirm the analysis matches the pre-registered plan and that deviations are disclosed.

### 11.5 Ethics & integrity reviewer — `ethics-integrity.md`
Mandate: research-ethics and integrity scan. IRB/IACUC status correct? Data privacy and consent handled? Dual-use / harm potential considered? Conflicts disclosed? **Any sign of fabricated data, plagiarism, or hallucinated content** (cross-checks against the prime directive, §3). This reviewer can issue a hard veto.

### 11.6 Citation-integrity reviewer — `citation-integrity.md`
Mandate: verify *every* reference exists, resolves to a real identifier, is correctly attributed, and actually **supports the specific claim it's attached to** (not just topically related). Check both directions: no orphan in-text cites, no orphan reference entries. Run/confirm `scripts/verify_citations.py`. Any unverifiable citation is a blocker, not a warning.

### 11.7 Domain / novelty reviewer — `domain-novelty.md`
Mandate: situate the work in its field. Is the claimed contribution actually novel given prior work? Is domain terminology used correctly? Are established findings represented faithfully? Is the relevant prior literature cited (no conspicuous omissions)? This is the reviewer that catches "you reinvented a known result."

### 11.8 Clarity / communication editor — `clarity-editor.md`
Mandate: readability and presentation at the *structural* level. Section structure and flow, figure/table quality and self-containedness, defining necessary jargon on first use, and whether the abstract faithfully represents the paper. Improves communication without changing scientific content. (Owns structure and figures; register and wordiness belong to the Plain-language reviewer, §11.9.)

### 11.9 Plain-language reviewer — `plain-language.md`
Mandate: make the prose as plain and direct as the subject *honestly* allows. It exists to counter the academic-register habits an LLM absorbs from its training data — reflexive hedging, nominalizations ("performed an investigation of" → "investigated"), throat-clearing, padding, needlessly Latinate vocabulary, and sentences that are long for no reason. It rewrites toward common words, active voice, and shorter sentences so a competent non-specialist can follow the argument.

**Integrity ranks above readability — hard limits this reviewer never crosses:**
- It does not touch a genuine **term of art**; established field vocabulary stays even when a "simpler" word exists, because the simpler word would be wrong or ambiguous to specialists.
- It does not flatten a **distinction that actually carries meaning** in the domain. Where the nuance is load-bearing, the longer phrasing stays.
- It does not strip a **hedge that prevents an overclaim**. A qualifier that keeps a claim honest is precision, not padding; only reflexive hedging that adds no precision is cut.
- For every proposed change it must be able to assert "no precision or accuracy was lost." Where plainer wording *would* lose something, it leaves the text and notes why.

Conflict rule: when its suggestions collide with the Adversarial, Consistency, Statistical, or Citation-integrity reviewer (e.g., a qualifier those reviewers require, or exact wording that matches the cited literature), **those reviewers win** — the Plain-language reviewer never overrides correctness to gain readability. It works the same tier as the Clarity editor (§11.8): both produce deferrable `minor`-level findings, not blockers.

### 11.10 Meta-editor (handling editor) — `meta-editor.md`
Mandate: synthesize all reports into one adjudicated decision. Resolve conflicts between reviewers, deduplicate, rank findings by severity, and emit a single ordered **revision plan**. When reviewers conflict, integrity and correctness outrank readability and presentation. Holds the accept/revise/reject decision for the loop. Does not write the paper; directs the revision.

**[DECIDE]** Minimum panel for a given run. Recommended default: all ten for a paper headed to external review; a "lite" mode (Adversary + Reproducer + Consistency + Statistical + Citation-integrity + Meta-editor) for internal drafts — the communication tier (Clarity + Plain-language) is the cheapest to add back when a draft is nearly done. The user picks; the skill states which mode ran.

---

## 12. Review orchestration & convergence

- Phases 7–8 loop. Each iteration: run the panel → meta-editor revision plan → revise → log a response-to-reviewers entry.
- **Convergence criteria [GATE]:** no `blocker` findings remain; no `major` findings remain from the Adversary, Reproducibility, Consistency, Statistical, Ethics, or Citation-integrity reviewers; the claim-provenance lint passes; citations verify; the reproducibility package builds clean. Clarity/Domain/Plain-language `minor` items may be acknowledged-and-deferred with a note.
- Cap the loop (e.g., 3 rounds) and, if it hasn't converged, hand the user a candid status of what's still open rather than declaring victory.
- Keep a full audit trail: every reviewer report, every revision, every response. This *is* part of what makes the result trustworthy.

---

## 13. Reproducibility package — `references/reproducibility-package.md`, `scripts/make_package.py`

The final deliverable is not just the PDF/markdown paper but a bundle a stranger can re-run:

```
study-package/
├── paper.md (+ rendered .pdf/.docx)
├── preregistration.md            # frozen, timestamped
├── data/
│   ├── raw/                       # untouched, with provenance manifest
│   └── processed/
├── code/                          # analysis + experiment scripts
├── environment/                   # capture_env.py output: versions, seeds, hardware, git hash
├── results/                       # analysis outputs the paper's numbers trace to
├── reviews/                       # all reviewer reports + response-to-reviewers
├── reporting-checklist.*          # CONSORT/STROBE/etc., completed
└── README.md                      # the reproduce-it contract
```

The **README contract** must let someone reproduce the headline results with documented commands and the captured environment. The Reproducibility reviewer (§11.2) literally tests this. Include a data-availability statement and license.

---

## 14. Quality gates summary **[GATE]**

A draft cannot be called "peer-review ready" until **all** hold:
1. Prime-directive integrity checks pass (§3) — no fabrication anywhere.
2. Pre-registration exists and was frozen before analysis (§6.2).
3. Power analysis was run; underpowered designs are disclosed (§6.3).
4. Every statistical result reports effect size + CI; corrections applied; assumptions checked (§8).
5. Claim-provenance lint passes; every speculation carries its three caveat fields (§9).
6. Limitations and Future-Research sections exist and are substantive (§10.2–10.3).
7. All required statements present, incl. CRediT, ethics, AI-disclosure, data availability (§10.1).
8. Every citation verifies and supports its claim; references page is complete both directions (§10.4, §11.6).
9. Reporting-guideline checklist completed for the study type (§10.6).
10. Reviewer panel ran; convergence criteria met or open items honestly disclosed (§12).
11. Reproducibility package builds and the README contract is honest (§13).

---

## 15. Edge cases & failure modes the skill must handle

- **User asks for a predetermined conclusion** → refuse the fabrication, offer to design a study that could fairly test it.
- **Results are null/negative** → write them up as a valid finding; do not bury them. Null results are publishable and honest.
- **Underpowered or tiny-N study** → run anyway if the user insists, but foreground the limitation and downgrade claims to exploratory.
- **No internet to verify citations** → mark unverifiable refs explicitly and do not let the citation gate "pass" silently; tell the user verification is pending.
- **Human-subjects request without ethics approval** → help design and document; refuse to claim data was collected (§1).
- **Single-author "collaborators"** → don't pad the author list; route helpers to Acknowledgments.
- **Speculation creeping into Results** → the provenance system relocates it to Discussion.
- **Claude.ai (no subagents)** → run reviewers sequentially and disclose the reduced independence (§7).

---

## 16. Test prompts for skill validation (`evals/evals.json`)

Seed the eval set with realistic, substantive prompts (each should be complex enough to actually trigger the skill):
1. "I ran a benchmark comparing two caching strategies, here's the data — write it up as a paper that's ready for peer review."
2. "Design an experiment to test whether code-review latency affects defect escape rate, including the power analysis and pre-registration."
3. "Reproduce the finding in this paper and write a replication report that flags what I couldn't reproduce."
4. "Here's a draft — run it through peer review and tell me what a tough reviewer would say."
5. "Help me write the methods and limitations for a simulation study with these parameters."

Grade on: presence of all required sections, every claim tagged, no unverifiable citations, effect sizes + CIs present, a real limitations section, reviewer reports produced, and a buildable reproducibility package.

---

## 17. Decisions to confirm before generation **[DECIDE]**

1. Default reporting format — journal IMRaD vs. preprint/conference (§4).
2. Citation style: **pinned** — numbered `[N]` is the default house style; the citation-integrity reviewer (citation specialist) switches a paper to author–date by field/target journal (§9, §10.4, and that reviewer's rubric). Confirm only the target field/journal and which `.csl` files to ship.
3. Default reviewer panel — full ten vs. lite mode, and the loop cap (§11.10, §12).
4. Target execution environment — Claude Code/Cowork (subagents) vs. Claude.ai (sequential), since §7 branches on it.
5. Stats stack for the scripts (e.g., Python + `scipy`/`statsmodels`/`pingouin`), and whether to include Bayesian tooling.
6. Whether citation verification should hard-block or warn when offline (§15).

---

*End of specification. The sections marked **[GATE]** are the load-bearing ones; the sections marked **[DECIDE]** are where I need your call before this becomes a generated skill.*
