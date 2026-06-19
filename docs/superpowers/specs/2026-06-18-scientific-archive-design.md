# Design: `scientific-archive` — Compliance-gated archival of research to a private repo

**Document type:** Build spec (input to writing-plans → implementation)
**Target artifact:** A Claude Code skill, directory `scientific-archive`, in `plugins/madskillz/skills/`
**Status:** Draft for review — 2026-06-18
**Parent vision:** the `scientific-*` research family (see `2026-06-16-scientific-peer-review-design.md` §0)

---

## 0. Where this sits in the family

The `scientific-*` family decomposes the research lifecycle into composable skills. Today
the built capability is `scientific-peer-review`; the roadmap reserves `scientific-writeup`,
`scientific-design`, `scientific-analysis`, and `scientific-repro`.

`scientific-archive` is a **new, cross-cutting family step**: the point at which a research
item (paper + supporting data/scripts/assets) is **archived to the private `jmresearch/research`
repository** so it is preserved and reproducible. It is distinct from the planned
`scientific-repro` (which captures the *execution environment*); archive is about *publishing
the artifact set* to the shared repo under a stable layout, after a compliance gate.

It is invoked as the final step of the `/research` umbrella and handed off to from
`scientific-peer-review` (to archive the reviewed paper, its data, and the review report).
Future phases (writeup, analysis) reuse it unchanged.

---

## 1. Purpose & scope

Push a completed (or reviewed) research item — the paper plus its pertinent data, scripts,
and assets — to the private `jmresearch/research` repo under a stable
`<topic>/<research-short-name>/` layout, **only after** a compliance gate confirms that
dataset licensing permits redistribution and that no privacy obligations are violated.

The goal: make research durably archived and reproduction-ready for peer review, without
ever silently shipping data we have no right to redistribute or that carries PII/PHI.

### 1.1 Scope contract

```
In:   - Collecting the artifacts that actually exist for one research item
        (paper.md, assets, data, scripts) plus phase outputs (e.g. the peer-review report).
      - A pre-flight COMPLIANCE GATE: dataset/third-party license clearance + privacy screening.
      - Choosing <topic>/<research-short-name> (suggested default, user confirms).
      - Generating LICENSE / ATTRIBUTIONS / COMPLIANCE / README per item.
      - Committing and pushing straight to the default branch of jmresearch/research.
      - Honest reporting of what was pushed, what was referenced-not-redistributed,
        what was omitted, and any user overrides.

Out:  - Writing or revising the paper (that is the author / scientific-writeup).
      - Running the peer review (that is scientific-peer-review; archive consumes its output).
      - Capturing the execution environment (that is the future scientific-repro).
      - Opening PRs / review gates — the user chose commit-and-push-to-main.
      - De-identifying data automatically — archive blocks and asks; it does not scrub.
```

### 1.2 Decisions locked during brainstorming

| Decision | Choice |
|---|---|
| Placement | Shared `/research` family step, realized as a new `scientific-archive` skill |
| Git flow | Commit & **push straight to the default branch** of `jmresearch/research` |
| Artifacts | Paper (md), assets, data, scripts, **+ license & attributions for reproduction** |
| Review report | **Archived** alongside, in a `review/` subfolder, when run post-review |
| Naming | **Ask each time** with a suggested default derived from the paper |
| License default | **CC BY 4.0** (paper/data/assets) **+ MIT** (code) |
| Compliance posture | **Fail-closed** with explicit, recorded override |

---

## 2. Integrity stance (inherited from the family, non-negotiable)

1. Archive only artifacts that actually exist. A missing category is reported, never faked.
2. Never fabricate a compliance verdict. "License unverified" / "privacy unverified" is
   reported as such — never asserted as "cleared."
3. Never claim a push that did not happen. Report the real result (commit SHA + pushed path)
   or the real failure.
4. The deliverable states its own coverage: what was pushed, what was referenced instead of
   redistributed (and why), what was omitted, and any overrides the user authorized.
5. Compliance and privacy outrank convenience and completeness in every conflict.

---

## 3. Repo layout (one research item)

```
<topic>/<research-short-name>/
  paper.md            # manuscript in markdown
  assets/             # figures, plots, diagrams referenced by the paper
  data/               # datasets / results tables — OR reference stubs (see §4), or a mix
  scripts/            # analysis code / reproducibility scripts / notebooks
    LICENSE           # MIT — covers code
  review/             # adjudicated revision plan + reviewer reports (only when post-review)
  LICENSE             # CC BY 4.0 — covers paper, data, assets
  ATTRIBUTIONS.md     # third-party sources, their licenses, what reproduction requires
  COMPLIANCE.md       # gate outcome: cleared / referenced-only / consent basis / overrides
  README.md           # title, date, topic + slug, license summary, reproduction notes
```

- Topic and short-name are **kebab-case slugs**, validated (no spaces/uppercase/path chars).
- If `<topic>/<research-short-name>/` already exists, the run is an **update**: changed files
  are listed and overwrites confirmed before push.
- License/attribution/compliance/README files are generated from the templates in §6.

---

## 4. Compliance & privacy gate (pre-flight — can block)

Runs **before** naming/layout/push. Reference: `references/compliance-gate.md`.

**4.1 Dataset & third-party licensing.** For every dataset in `data/` and any third-party
asset/code, identify source + license/terms, then classify:

- **Redistributable** (license/terms permit copying to the repo, even a private one) →
  include the data; record the license + source in `ATTRIBUTIONS.md`.
- **Not redistributable / unclear / DUA / click-through / non-commercial / no-derivatives** →
  do **not** archive the raw data. Archive a **data reference** instead: citation, access
  URL, dataset version, content hash, and retrieval steps — enough to reproduce without
  violating terms. Record in `ATTRIBUTIONS.md` + `COMPLIANCE.md`.

**4.2 Privacy screening.** Screen data and assets for PII/PHI: names, emails, IDs, dates of
birth, precise geolocation, free-text that may carry identifiers, identifiable faces in
images. For human-subjects data, require evidence of consent/approval that covers
archival/sharing.

- PII/PHI present, or consent/approval basis absent → **block**. The user must de-identify,
  supply a compliant reference, or record an explicit attestation that it is cleared.

**4.3 Posture — fail-closed.** If licensing or privacy status is unknown or unverifiable, the
affected data is **not** pushed. The skill surfaces the gap; the user must supply a compliant
reference, de-identify, or **explicitly override with a recorded rationale** (captured in
`COMPLIANCE.md`). Verdicts are never fabricated (§2.2).

**4.4 Synergy with peer review.** When archive runs right after a peer review, it pulls the
`ethics-integrity` reviewer's flags into the gate rather than re-deriving them.

---

## 5. Archive flow (the skill's steps)

0. **Compliance gate (§4).** Classify every dataset/third-party artifact; screen for privacy.
   Resolve each to: include / reference-only / blocked-pending-action. Fail-closed on unknowns.
1. **Collect artifacts** that actually exist (paper / assets / data / scripts) + phase outputs
   (the review report when post-review). Nothing fabricated.
2. **Name.** Propose `<topic>` + slugified `<research-short-name>` from the paper title;
   user confirms or overrides. Validate slugs.
3. **License.** Default CC BY 4.0 + MIT; confirm/override. Fold §4 findings into `ATTRIBUTIONS.md`.
4. **Resolve repo.** Verify `gh` is installed, authenticated, and has push access to
   `jmresearch/research`. Clone it to a cache dir (`${XDG_CACHE_HOME:-$HOME/.cache}/jmresearch-research`)
   or `git pull --ff-only` an existing checkout.
5. **Lay out** `<topic>/<research-short-name>/` per §3 (real data, reference stubs, or a mix
   per the gate); generate LICENSE / ATTRIBUTIONS / COMPLIANCE / README.
6. **Pre-push summary + confirm.** Show the file manifest, target path, compliance outcomes
   (cleared / referenced-only / overrides), and the commit message. Confirm before pushing —
   pushing to a shared private repo's main is outward-facing, and this is the user's last
   chance to catch anything sensitive.
7. **Commit & push** to the default branch. Report commit SHA, pushed path, and exactly what
   was included vs. referenced vs. omitted.

---

## 6. Structure & files to build

```
plugins/madskillz/skills/scientific-archive/
  SKILL.md                    # orchestrator: integrity stance + steps 0–7
  references/
    compliance-gate.md        # license classes, DUA handling, PII/PHI screening checklist
    repo-layout.md            # folder layout + README / ATTRIBUTIONS / COMPLIANCE templates
    git-workflow.md           # gh auth check, clone/pull cache, commit, push, failure handling
    licenses/
      CC-BY-4.0.txt           # verbatim license text — paper/data/assets
      MIT.txt                 # verbatim license text — code
  evals/evals.json            # triggering evals (mirrors peer-review's)
```

**Wiring:**
- `plugins/madskillz/skills/scientific-peer-review/SKILL.md` Step 4 — add a hand-off: after
  delivering the review, offer to archive paper + data + the review report via `scientific-archive`.
- `plugins/madskillz/commands/research.md` — mention archival as the family's final phase.
- `plugins/madskillz/.claude-plugin/plugin.json` — bump `0.5.0 → 0.6.0` (adds a skill).

---

## 7. Error handling & edge cases

- `gh` missing/unauthed → stop with `gh auth login` guidance; suggest the `!`-prefix to run it inline.
- Push rejected / no access / offline → report honestly; optionally leave a local commit and
  tell the user to push later. Never claim success (§2.3).
- `<topic>/<short-name>/` already exists → update mode; list changed files; confirm overwrites.
- Missing artifact categories → archive what exists, note gaps; never fabricate data/scripts.
- Dataset license forbids redistribution → reference-only stub, not raw data (§4.1).
- PII/PHI present or consent basis missing → block; de-identify / reference / attest (§4.2).
- Licensing or privacy status unknown → fail-closed; not pushed without recorded override (§4.3).
- Invalid slug → re-prompt / sanitize before any filesystem write.
- No paper provided → ask for it; archive needs at least the manuscript.

---

## 8. Testing & verification

- `evals/evals.json` covering trigger phrasing — "archive this research," "push the paper to
  the research repo," "save this study to jmresearch" — and non-triggers (a pure review request).
- **Manual dry-run** (documented in the spec, not automated, because the skill performs real
  git pushes): archive a throwaway item into a scratch repo and confirm the §3 layout, the
  generated license/attribution/compliance files, the compliance gate's reference-only and
  block paths, and a clean commit + push. No automated push test against the real repo.

---

## 9. Open assumptions (flag if wrong)

- The user has `gh` installed and authenticated with push access to `jmresearch/research`,
  and the repo already exists.
- Private redistribution is still redistribution: a dataset's terms are honored even though
  the destination repo is private (the gate does not relax for "it's private").
- The default branch is whatever `jmresearch/research` reports (not assumed to be `main`).
