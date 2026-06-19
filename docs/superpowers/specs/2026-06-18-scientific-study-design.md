# Design: `scientific-study` — Agentic-peer-reviewed research, published as a PR

**Document type:** Build spec (input to implementation)
**Target artifact:** A Claude Code skill, directory `scientific-study`, in `plugins/madskillz/skills/`
**Status:** Draft for review — 2026-06-18 (supersedes the `scientific-archive` framing)
**Parent vision:** the `scientific-*` research family (see `2026-06-16-scientific-peer-review-design.md` §0)

---

## 0. What this is (and the scope correction)

An earlier pass mis-scoped this as `scientific-archive` — a passive "review + archive"
step that pushed an externally-produced paper straight to `main`. That was wrong.

The real intent: a **research-study pipeline that uses agentic peer review as quality
gates**, so a high-quality paper reaches a human with minimal manual intervention. The
skill **drafts and revises the paper itself**, loops it through the
`scientific-peer-review` panel until it clears, gates compliance/privacy, and **opens a
PR** to the private `jmresearch/research` repo. The human reviews and merges the PR —
nothing reaches `main` without that approval. The agentic loop is "free" peer review
before any human spends time on it.

### Family placement

| Skill | Role |
|---|---|
| **scientific-study** | Orchestrator: frame → draft → agentic review loop → compliance gate → PR. **This doc.** |
| scientific-peer-review | Review-only **engine** invoked each loop cycle (exists). |

Writeup/revising lives **inline** in `scientific-study` for now; we extract a separate
`scientific-writeup` skill later only if a second consumer needs it (YAGNI).

---

## 1. Purpose & scope

### 1.1 Scope contract

```
In:   - Frame a study from a research brief (or a provided draft), incl. a NOVELTY gate.
      - Draft paper.md + supporting data/scripts/assets (provenance-honest).
      - A quality-gate LOOP: invoke scientific-peer-review, edit the paper to address
        findings, commit per cycle, repeat until no blockers or 3 cycles.
      - A compliance/privacy gate (dataset licensing + PII/PHI) before publishing.
      - Publish on a study branch and OPEN A PR to jmresearch/research; disclose how
        cycles changed the paper, residual findings, and compliance outcomes.
      - Human-review follow-ups: apply requested change → re-gate → separate commit.

Out:  - Merging the PR (the human merges; this skill never touches main directly).
      - Running the review itself (delegated to scientific-peer-review).
      - Capturing the execution environment (future scientific-repro).
```

### 1.2 Decisions locked during brainstorming

| Decision | Choice |
|---|---|
| Structure | **One orchestrator skill** (`scientific-study`); peer-review reused as the engine |
| Loop stop | **No blocker-severity findings, capped at 3 cycles**; residuals disclosed in PR |
| Git flow | **Study branch → PR** into default branch; human reviews & merges (no push-to-main) |
| Cycle visibility | **One commit per cycle**; each cycle's report saved under `review/` |
| Novelty gate | During framing: if evidence the work isn't novel, **confirm with the user** before the full flow; continue as acknowledged replication/validation or refine |
| Human follow-ups | Apply → re-gate via peer-review → **separate commit** on the PR branch |
| Artifacts | Paper (md), assets, data, scripts, **+ license & attributions** for reproduction |
| License default | CC BY 4.0 (paper/data/assets) + MIT (code) |
| Compliance posture | **Fail-closed** with explicit, recorded override |

---

## 2. Integrity stance (inherited, non-negotiable)

1. Never fabricate a review, revision, compliance verdict, commit, or push. Report the
   real state or the real failure.
2. Never publish past a gate that did not pass. Residual/unresolved findings are
   **disclosed in the PR**, never hidden. Hitting the 3-cycle cap with open blockers is
   published flagged, not faked as clean.
3. Apply reviewer feedback faithfully; surface genuinely disputed findings to the human
   rather than silently dropping them.
4. Honor data rights and privacy even for a private repo.
5. The human merges. This skill opens/updates the PR; it never merges or pushes to the
   default branch directly.

---

## 3. Flow (the skill's steps)

1. **Frame + novelty gate.** Take the brief/draft. Run a prior-art/novelty check (web /
   `deep-research` when available). If evidence says the work isn't novel → stop and ask
   the user to confirm (proceed as replication/validation, refine, or cancel); record
   confirmed intent as context. Set `<topic>`/`<research-short-name>` (suggested default,
   user confirms; kebab-case). Create the study branch.
2. **Draft** paper.md + data/scripts/assets, provenance-honest. Commit `draft: initial …`.
3. **Quality-gate loop** (`references/review-loop.md`), max 3 cycles: invoke
   `scientific-peer-review` → edit paper to address blockers/majors → commit
   `review cycle N: …` + save `review/cycle-N.md`. Stop at no-blockers or 3 cycles; carry
   residuals to the PR.
4. **Compliance gate** (`references/compliance-gate.md`): classify dataset licensing
   (include / reference-only), screen PII/PHI + consent; fail-closed; record `COMPLIANCE.md`.
5. **Publish PR** (`references/git-workflow.md`): lay out the folder, push the branch,
   `gh pr create` into the default branch; PR body summarizes study type, per-cycle
   changes, residuals, compliance. Report the PR URL.
6. **Human follow-ups:** apply requested change → re-gate (focused peer-review pass) →
   separate commit on the PR branch → update PR. Never merge.

---

## 4. Compliance & privacy gate (pre-publish, can block)

Unchanged in substance from the prior pass; it now runs as Step 4 after the loop.

- **Licensing:** redistributable → include; not-redistributable/DUA/NC/ND/unclear →
  **reference-only** stub (citation, URL, version, content hash, retrieval steps).
  Private repo does not relax the gate.
- **Privacy:** screen PII/PHI; human-subjects data needs consent/approval covering
  sharing. Detected/absent → **block** (de-identify / reference / recorded attestation).
- **Fail-closed:** unknown status → not published without explicit recorded override.
- **Synergy:** ingest the latest cycle's `ethics-integrity` flags as gate inputs.

---

## 5. Structure & files

```
plugins/madskillz/skills/scientific-study/
  SKILL.md                    # orchestrator: integrity stance + steps 1–6 (incl. novelty gate)
  references/
    review-loop.md            # the quality-gate loop: cycle, stop criterion, faithful edits, residuals, follow-ups
    compliance-gate.md        # license classes, DUA handling, PII/PHI screening (reused)
    repo-layout.md            # folder layout + README/ATTRIBUTIONS/COMPLIANCE templates, per-cycle review/
    git-workflow.md           # study branch, per-stage commits, gh PR, human-follow-up commits, PR body template
    licenses/{CC-BY-4.0.txt, MIT.txt}
  evals/evals.json            # trigger + behavior evals (novelty, loop-cap, compliance, PR-not-merge, follow-up)
```

**Wiring:**
- `scientific-peer-review/SKILL.md` Step 4 — reverted to review-only "deliver and stop";
  points to `scientific-study` as the skill that drives it in a loop.
- `commands/research.md` — routes "produce a study" → `scientific-study`, "review a draft"
  → `scientific-peer-review`.
- Plugin version `0.6.0` (carries this skill in the branch).

---

## 6. Repo layout (one study)

```
<topic>/<research-short-name>/
  paper.md            # evolves across the per-cycle commits
  assets/  data/  scripts/(LICENSE = MIT)
  review/cycle-N.md   # one adjudicated report per review cycle
  LICENSE             # CC BY 4.0
  ATTRIBUTIONS.md  COMPLIANCE.md  README.md   # README notes study type: novel | replication
```

Branch: `study/<topic>/<research-short-name>`. PR base: the repo's default branch.

---

## 7. Edge cases

- No brief/draft → ask; never invent a topic.
- Novelty check says not-novel → confirm intent before proceeding; continue only as
  acknowledged replication or after refining.
- 3 cycles, blockers remain → PR opened with blockers flagged unresolved (not faked).
- Disputed finding → surfaced in the PR for the human.
- `gh` missing/unauthed, no access, offline → stop with guidance; never fake commit/push/PR.
- Restricted dataset → reference-only; PII/PHI or missing consent → block; unknown → fail-closed.
- Asked only to review → `scientific-peer-review`. Asked to merge → out of scope (human merges).

---

## 8. Testing & verification

- `evals/evals.json`: trigger; novelty-not-novel confirm gate; loop blockers capped at 3;
  restricted-dataset reference-only; human-feedback follow-up as a separate commit;
  no-gh-auth honesty; non-trigger control.
- Manual dry-run (documented, not automated — performs real git/PR ops): produce a small
  study into a scratch repo and confirm the per-cycle commits, the `review/` reports, the
  compliance files, and a real PR opened (not merged, not pushed to main).

---

## 9. Open assumptions (flag if wrong)

- `gh` is installed, authenticated, has push + PR access to `jmresearch/research`, which exists.
- Private redistribution is still redistribution — the gate does not relax for "it's private."
- The default branch is whatever `jmresearch/research` reports (not assumed `main`).
- One agentic review cycle is the floor; 3 is the cap. Novel vs. replication is decided at
  framing with the user when novelty is in doubt.
