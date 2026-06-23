# Mint experts back into madskillz via PR

**Date:** 2026-06-22
**Status:** approved → implementing
**Plugin version:** 0.12.0 → **0.13.0** (ships this feature; separate from the per-mint patch bumps below)

## Problem

`ask-an-expert` mints a new (or extends an existing) expert by writing a **bare relative**
`experts/<concise-name>.md` (`references/find-the-right-expert.md:36`, `expert-format.md:3`). It owns
the shared library and is the only skill that writes it. But it is most often invoked **from inside a
research run**, and a research run executes inside a **worktree of the external `jmresearch/research`
repo** (`scientific-study/references/git-workflow.md` §2). With no anchor to the madskillz repo, a
minted expert lands either:

- **in the research project** (the `jmresearch/research` worktree) — "stored in the projects they're
  used in", which is exactly what must not happen; or
- **in the throwaway plugin cache** (`~/.claude/plugins/cache/.../ask-an-expert/experts/`) — which the
  user's global rule flags as temporary: reverted on the next plugin update, never reviewed.

Either way the minted expert never lands durably in the canonical madskillz repo and is never opened
for human review. The research PR to `jmresearch/research` only *names* the expert in its "Domain
experts" section (`git-workflow.md:284–286`); the expert **file** never travels back to madskillz.

This violates the user's standing rule: a tool change (a new/updated expert persona is one) must be
**propagated to its canonical source and pushed up for human review — a branch + commit/PR, with a
version bump**.

## Decision

When `ask-an-expert` persists a **new or updated** expert, it writes it into a **dedicated madskillz
clone** and opens a **PR to `bubthegreat/madskillz`** (base `main`). This fires **whenever it mints**
— in-study or standalone — because `ask-an-expert` owns the library; there is one code path, not a
study special case.

Settled design choices (each chosen explicitly):

| Choice | Decision |
|---|---|
| Reach the madskillz repo | **Dedicated sync clone** under `~/.madskillz/` (mirrors the voice `madskillz-sync` precedent), not the dev checkout or a checkout-less `gh` API path. |
| When it fires | **Any time `ask-an-expert` mints/updates** an expert — standalone and in-study alike. |
| PR grouping | **One bundled PR per run**, opened at **study end**, with all experts minted/updated that run. Standalone minting (no run) → one PR per expert. |
| Staging during the run | **Per-run worktrees off a bare clone** (mirrors the `jmresearch/research` cache layout), so the expert is usable immediately, kept out of the research project, and concurrency-safe. |
| Version bump | **Patch bump of `plugin.json` per expert PR** (e.g. `0.12.0 → 0.12.1`), honoring the propagate-with-a-bump rule. Accepted cost: two concurrent open expert PRs both touch `plugin.json`, so the human resolves a trivial version conflict when merging the second. |

## Architecture — the experts sync clone (`~/.madskillz/experts/`)

A **bare** clone of `bubthegreat/madskillz` at `~/.madskillz/experts/repo.git`, with **one worktree per
run** under `~/.madskillz/experts/worktrees/<run-slug>` on a branch `experts/<run-slug>`. This is
structurally identical to the `jmresearch/research` cache (`git-workflow.md` §2) and a **sibling of the
existing voice `madskillz-sync` clone** under `~/.madskillz`.

- **Why `~/.madskillz/` and not `~/.claude/`:** the unattended headless agent runs least-privilege; the
  harness sensitive-file guard **blocks every write under `~/.claude/`** but `~/.madskillz/` is
  validated-writable (established in `2026-06-21-voice-storage-relocation-design.md`). The expert
  write-back must work headless, so it lives under `~/.madskillz/`.
- **Why a separate clone from voice's:** the voice gate does `reset --hard origin/main` on its clone;
  pointing experts at the same clone would let a voice sync wipe an in-flight expert branch. Separate
  bare clone, separate purpose.
- **Created once, atomically, on first need** — same clone-to-temp-then-`mv -T --no-clobber` dance as
  `git-workflow.md` §2, so two concurrent first-minters cannot clobber each other.
- **Shared-infra safety:** the "never clobber shared infrastructure" rules (`git-workflow.md:22–31`)
  apply verbatim — a run owns only its own `experts/<run-slug>` branch and its own worktree; it never
  recreates/`reset`s the bare repo or touches another run's branch/worktree. If a shared path looks
  broken, stop and surface it; never `rm -rf` it.

## Flow

### Inside `ask-an-expert`

1. **Refresh canonical first.** `git -C <bare> fetch origin` and run the *reuse-before-create* check
   (`SKILL.md:29–32`, `find-the-right-expert.md:21–33`) against **`origin/main`** — so it sees the real
   current library, not a stale plugin cache. (Side benefit: fixes the stale-read too.)
2. **Resolve a worktree for this run.** Reuse `~/.madskillz/experts/worktrees/<run-slug>` if present,
   else add one off `origin/main` on branch `experts/<run-slug>` (resume chain identical to
   `git-workflow.md` §2).
3. **Mint/update into the worktree.** Write/edit `plugins/madskillz/skills/ask-an-expert/experts/<name>.md`
   per `expert-format.md` (Scope/Boundaries/How to engage/Integrity/Output/**Provenance**, the
   Provenance dated for today's run), and **commit** it. The path returned to the caller/panel points
   here — usable immediately, out of the research project.
4. **Adversarial gate** runs as today (`find-the-right-expert.md:42–57`): one revision allowed; the
   committed file reflects the final accepted state.

### Publish (opens the PR)

- **In-study:** the caller passes a **run-id** and a **defer-publish** signal. Experts accumulate on
  `experts/<run-slug>`; at **study end** a single **publish** step bumps `plugin.json` (patch), commits
  the bump, pushes the branch, and opens **one bundled PR**.
- **Standalone:** no run-id → **publish immediately** after the gate resolves: one expert, one PR
  (run-slug derived from the expert name + date).
- **PR:** `gh pr create -R bubthegreat/madskillz --base main`, title
  `experts: mint <names> (<source>)`. Body lists each expert with its **Scope/Boundaries/Provenance**
  and any residual adversarial-gap note, plus (for in-study) the originating study/topic.
- **Gate interaction:** a PR opens for **accepted** and **accept-with-residual-gap** experts (the gap is
  surfaced in the body). On a **fail-closed halt** (adequate expertise could not be established) **no
  expert was minted and no PR opens** — the caller's existing halt handling is unchanged.

### Handoff between skills

`scientific-peer-review`'s domain-coverage triage (`SKILL.md:84–95`) and `scientific-study` pass the
**run-id + defer-publish** when they invoke `ask-an-expert`. `scientific-study`'s publish
(`git-workflow.md` §4) gains a sibling step: if the run staged any experts, open the bundled madskillz
PR and **link it from the research PR's "Domain experts" section** (`git-workflow.md:284–286`). Result:
two cleanly separated PRs — the paper to `jmresearch/research`, the expert(s) to `madskillz`.

## Error handling (mirrors `git-workflow.md` §7)

- `gh` missing / unauthenticated → **stop**, tell the user to `gh auth login` (suggest the `!` prefix);
  **never fake a PR URL**. (Same `gh`/push capability the study flow already relies on for the research
  PR.)
- `git push` / `gh pr create` failure (incl. transient) → retry 2–3×; the commits already live on the
  run branch in the bare repo, so report honestly and offer manual push. Never claim a PR that did not
  open.
- Run branch/worktree vanished (a misbehaving concurrent run) → recover per `git-workflow.md` §2.2; do
  not restart. Committed expert work survives in git objects.
- Shared path looks broken → surface it; never delete/reset it.

## Changes (skill/docs only — no executable code)

### Canonical (this repo → PR, version bump **0.13.0**)

- **New:** `plugins/madskillz/skills/ask-an-expert/references/expert-writeback.md` — the bare-clone +
  per-run-worktree + publish + PR procedure (the experts analogue of `scientific-study`'s
  `git-workflow.md`), including the shared-infra safety rules and failure handling above.
- **Edit:** `plugins/madskillz/skills/ask-an-expert/SKILL.md` — Steps 2–3 now persist to the sync clone
  and publish; document the run-id/defer-publish input and the standalone vs in-study publish split.
- **Edit:** `plugins/madskillz/skills/ask-an-expert/references/find-the-right-expert.md` — anchor the
  write and the reuse-check to the canonical clone (`origin/main`), not a bare relative path; reference
  `expert-writeback.md` for the persist/publish mechanics.
- **Edit:** `plugins/madskillz/skills/ask-an-expert/experts/README.md` — note that adding a file here
  happens via the write-back PR flow, not a direct edit, when minting through a run.
- **Edit:** `plugins/madskillz/skills/scientific-peer-review/SKILL.md` — domain-coverage triage passes
  run-id + defer-publish to `ask-an-expert`.
- **Edit:** `plugins/madskillz/skills/scientific-study/references/git-workflow.md` and
  `references/review-loop.md` — add the end-of-run "publish staged experts" step and link the expert PR
  from the research PR's "Domain experts" section.
- **Bump:** `plugins/madskillz/.claude-plugin/plugin.json` — `0.12.0` → `0.13.0`.

### Per-mint runtime behavior (what the above skills now do at run time)

Each minted/updated expert produces a commit on `experts/<run-slug>`; each published PR carries a
**patch** bump of `plugin.json`. These bumps are made by the running skill at publish time, not part of
the 0.13.0 feature commit.

### Local machine

No manual setup: the bare clone at `~/.madskillz/experts/repo.git` is created on demand on the first
mint (same as the `jmresearch` cache). Only requirement is an authenticated `gh` with push access to
`bubthegreat/madskillz` — already present for the voice sync and the research-PR flow.

## Validation

- **Standalone mint, end-to-end:** ask `ask-an-expert` to mint a throwaway expert standalone; confirm
  (a) the bare clone is created under `~/.madskillz/experts/`, (b) the file is committed on an
  `experts/<slug>` branch, (c) a PR opens against `bubthegreat/madskillz` base `main` with the patch
  bump, and (d) **nothing** is written into the current project. Close the PR / delete the test branch
  after.
- **In-study mint, bundled:** drive a small study that triggers domain-coverage triage to mint two
  experts; confirm both land on **one** run branch and **one** bundled PR opens at study end, linked
  from the research PR's "Domain experts" section, with the research PR still targeting
  `jmresearch/research`.
- **Reuse-before-create:** confirm the reuse check now lists experts from the freshly-fetched
  `origin/main`, and reusing an existing expert opens **no** PR.
- **Headless writability:** confirm a least-privilege headless run can create the clone and commit under
  `~/.madskillz/experts/` with no guard denial (relies on the `~/.madskillz/` validation from the voice
  relocation spec).
- **Fail-closed:** confirm an unestablishable-expertise halt opens **no** PR.

## Risks / mitigations

- **Concurrent expert PRs collide on `plugin.json`.** Accepted: per-mint bundling keeps it to one PR per
  run, and the human resolves the trivial version-number conflict when merging the second. (The
  alternative of no-bump-on-expert-PRs was rejected in favor of strictly honoring the bump rule.)
- **A study aborts before its publish step.** The bundled PR never opens — but the experts are already
  **committed on the run branch** in the bare repo, so the work is recoverable (resume re-attaches the
  worktree and can publish). Noted as the accepted trade-off of end-of-run grouping.
- **`gh` unauthenticated in a headless run.** Fails closed with guidance; never a faked PR. Same failure
  mode the research-PR flow already documents.
- **Bare clone under `~/.madskillz/experts` ever becomes guarded.** Unlikely (custom dir, validated for
  voice); if it happens the same escape hatch as voice applies (relocate the dir).
