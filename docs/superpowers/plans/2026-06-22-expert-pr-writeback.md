# Expert PR Write-Back Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `ask-an-expert` mints or updates an expert, persist it to the canonical madskillz repo and open a PR for human review — never leave it in the research project or the throwaway plugin cache.

**Architecture:** This is a **documentation / skill-authoring** change — no executable code. `ask-an-expert` (which owns the `experts/` library) gains a write-back procedure: a dedicated **bare** madskillz clone under `~/.madskillz/experts/` with **per-run worktrees** (mirroring `scientific-study`'s `git-workflow.md`), an isolated `experts/<run-slug>` branch per run, and a `gh` PR a human merges. The research-family skills (`scientific-peer-review`, `scientific-study`) pass a **run-id + defer-publish** so a study's minted experts bundle into **one** PR opened at study end; standalone minting opens one PR per expert.

**Tech Stack:** Markdown skill files; `git` (bare clone + worktrees); `gh` CLI; JSON (`plugin.json`, `evals.json`). No language runtime, no unit-test framework — tasks verify content structurally (`grep`, `python3 -m json.tool`) and the spec's live behavior is exercised in a final manual validation.

## Global Constraints

Copy these exact values wherever a task needs them:

- **Canonical repo:** `bubthegreat/madskillz`; **base branch:** `main`.
- **Dedicated sync clone (bare):** `~/.madskillz/experts/repo.git`; **per-run worktrees:** `~/.madskillz/experts/worktrees/<run-slug>`; **run branch:** `experts/<run-slug>`.
- **`<run-slug>`:** in-study = `<topic>__<research-short-name>` (the study slug); standalone = `<expert-name>-<YYYYMMDD>`.
- **Library path in repo:** `plugins/madskillz/skills/ask-an-expert/experts/<name>.md`.
- **Version file:** `plugins/madskillz/.claude-plugin/plugin.json` (currently `0.12.0`). Feature ships at **`0.13.0`**; each runtime expert PR does a **patch** bump.
- **Keystone reference (cited by other docs as):** `references/expert-writeback.md` (relative to the `ask-an-expert` skill dir).
- **Publish modes:** *deferred/bundled* (in-study, run-id + defer-publish) vs *immediate* (standalone, no run-id).
- **Integrity:** never fake a PR/commit/push; `gh` missing/unauthed → stop with guidance. Reuse-with-no-change and fail-closed halt → **no PR**.
- **Commit trailer (every commit):** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Stage only the specific file(s) — **never `git add -A`** (worktrees are full madskillz checkouts).

This work happens on branch `feat/ask-an-expert-pr-writeback` (already created; the spec is committed there).

---

### Task 1: Author the keystone reference `expert-writeback.md`

The single source of truth for the bare-clone + per-run-worktree + persist + publish + PR mechanism. Tasks 2–4 reference it, so its vocabulary (paths, branch names, publish modes, PR body) is locked here.

**Files:**
- Create: `plugins/madskillz/skills/ask-an-expert/references/expert-writeback.md`

**Interfaces:**
- Consumes: nothing (first task).
- Produces (the vocabulary later tasks must reuse verbatim): the ref path `references/expert-writeback.md`; bare clone `~/.madskillz/experts/repo.git`; worktrees `~/.madskillz/experts/worktrees/<run-slug>`; branch `experts/<run-slug>`; the terms **run-id**, **defer-publish**, **deferred/bundled** vs **immediate** publish; PR command `gh pr create -R bubthegreat/madskillz --base main`; **patch** bump of `plugins/madskillz/.claude-plugin/plugin.json`; PR title `experts: mint <names> (<source>)`.

- [ ] **Step 1: Write the file with exactly this content**

````markdown
# Expert write-back — persist a minted expert to madskillz and open a PR

`ask-an-expert` owns the shared `experts/` library, which lives in the **madskillz repo**
(`bubthegreat/madskillz`, at `plugins/madskillz/skills/ask-an-expert/experts/`). When this skill
**mints a new expert or updates an existing one**, that is a change to a canonical source: it must be
written into madskillz and **opened as a PR for human review** — never left in the project being
researched, and never left only in the throwaway plugin cache (`~/.claude/plugins/cache/…`, which the
next plugin update reverts).

This file is the procedure. It mirrors `scientific-study/references/git-workflow.md`: a **bare clone**
with **per-run worktrees**, isolated branches, and a `gh` PR a human merges. It applies **whenever
ask-an-expert persists an expert** — inside a research run or standalone.

## The dedicated sync clone

```
~/.madskillz/experts/repo.git                 # shared bare clone (object store; no working tree)
~/.madskillz/experts/worktrees/<run-slug>     # one isolated worktree per run
```

- **Under `~/.madskillz/`, not `~/.claude/`** — the unattended headless agent is least-privilege and
  the harness sensitive-file guard blocks writes under `~/.claude/`; `~/.madskillz/` is writable (see
  `docs/superpowers/specs/2026-06-21-voice-storage-relocation-design.md`).
- **Separate from the voice `madskillz-sync` clone** — the voice gate does `reset --hard origin/main`
  on its clone; sharing it would wipe an in-flight expert branch. Different clone, different purpose.

### Create it once, atomically (never recreate/reset it)

```bash
ROOT="$HOME/.madskillz/experts"
BARE="$ROOT/repo.git"
URL=$(gh repo view bubthegreat/madskillz --json sshUrl -q .sshUrl)   # git@github.com:bubthegreat/madskillz.git

if [ -d "$BARE" ] && git -C "$BARE" rev-parse --is-bare-repository >/dev/null 2>&1; then
  :                                                  # present & valid → reuse; NEVER re-clone/rm/reset it
elif [ -e "$BARE" ]; then
  echo "FATAL: $BARE exists but is not a valid bare repo (failed/partial clone, or a concurrent"
  echo "       create in progress). Do NOT delete it blindly. Stopping."; exit 1
else
  mkdir -p "$ROOT"; TMP="$ROOT/.repo.git.tmp.$$"
  git clone --bare "$URL" "$TMP"
  git -C "$TMP" rev-parse --is-bare-repository >/dev/null 2>&1 || { rm -rf "$TMP"; exit 1; }
  mv -T --no-clobber "$TMP" "$BARE" 2>/dev/null || rm -rf "$TMP"     # lost the race → keep the winner's bare
fi
git -C "$BARE" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C "$BARE" fetch origin --prune                # refresh remote-tracking refs (lock-safe, concurrent-OK)
```

**Never clobber shared infrastructure** (same rule as the research cache): the bare repo and every
*other* run's `experts/*` branch and worktree belong to concurrent runs. Your run owns exactly its own
`experts/<run-slug>` branch and its own worktree. Never `rm -rf`/recreate the bare, `reset
--hard`/`branch -f`/`push --force` a ref you did not create, or remove another run's worktree. If a
shared path looks broken, **stop and surface it** — do not "fix" it by deleting it.

## Resolve this run's worktree

`<run-slug>` is filesystem-safe and unique per run: a study uses `<topic>__<research-short-name>` (the
study slug); standalone uses `<expert-name>-<YYYYMMDD>`.

```bash
DEFAULT_BRANCH=$(gh repo view bubthegreat/madskillz --json defaultBranchRef -q .defaultBranchRef.name)  # main
BRANCH="experts/<run-slug>"
WT="$ROOT/worktrees/<run-slug>"

if [ -d "$WT" ]; then
  :                                                                          # resume: reuse this run's worktree
elif git -C "$BARE" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$BARE" worktree add "$WT" "$BRANCH"                                # resume: local branch exists
elif git -C "$BARE" show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git -C "$BARE" worktree add "$WT" -b "$BRANCH" "origin/$BRANCH"            # resume: branch was pushed earlier
else
  git -C "$BARE" worktree add "$WT" -b "$BRANCH" "origin/$DEFAULT_BRANCH"    # new run off up-to-date main
fi
```

The library path inside the worktree is `$WT/plugins/madskillz/skills/ask-an-expert/experts/`. The
**reuse-before-create** check (`find-the-right-expert.md`) lists experts from there — i.e. from a
freshly-fetched `origin/main`, the real current library, not a stale plugin cache.

## Persist a minted/updated expert (one commit per expert)

Write or edit the file in the worktree, then commit just that file:

```bash
# write/edit "$WT/plugins/madskillz/skills/ask-an-expert/experts/<name>.md"
#   per ../references/expert-format.md (with a dated Provenance line)
git -C "$WT" add "plugins/madskillz/skills/ask-an-expert/experts/<name>.md"
git -C "$WT" commit -m "experts: mint <name> (<source>)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

Stage only the expert file(s) — **never `git add -A`** (the worktree is a full madskillz checkout, so
it also contains the rest of the plugin). The committed file is the same one the panel adopts and the
same one the PR ships. The adversarial gate (`find-the-right-expert.md`) runs as usual; its one allowed
revision is another commit on this branch.

## Publish — open the PR

Two modes:

- **Deferred / bundled (in-study):** the caller passed a **run-id** and **defer-publish**. Do NOT open
  the PR per expert — accumulate every minted/updated expert on `experts/<run-slug>`, and run the
  publish **once at study end** (the `scientific-study` publish step calls it).
- **Immediate (standalone):** no run-id → publish right after the adversarial gate resolves.

Publish = patch-bump, push, PR:

```bash
# 1) Patch-bump the plugin version (honor the propagate-with-a-bump rule): bump the PATCH field of
#    plugins/madskillz/.claude-plugin/plugin.json (e.g. 0.13.0 -> 0.13.1). One bump per PR.
git -C "$WT" add "plugins/madskillz/.claude-plugin/plugin.json"
git -C "$WT" commit -m "chore: bump madskillz patch (mint experts: <names>)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"

# 2) Push the run branch and open ONE PR (all experts minted/updated this run).
git -C "$WT" push -u origin "$BRANCH"
gh pr create -R bubthegreat/madskillz \
  --base "$DEFAULT_BRANCH" --head "$BRANCH" \
  --title "experts: mint <names> (<source>)" \
  --body-file <generated PR body>           # template below
```

Report the PR URL. **Do not merge** — a human reviews and merges. A study's research PR (to
`jmresearch/research`) **links this PR** from its "Domain experts" section.

### Which experts get a PR

- **Accepted** and **accepted-with-residual-gap** experts → PR opens; a residual adversarial-gap is
  surfaced in the body (the expert is still used for what it does cover).
- **Fail-closed halt** ("could not establish adequate expertise for <domain>") → **nothing was minted,
  no PR.** The caller's existing halt handling is unchanged.
- **Reuse of an existing expert with no change** → no commit, **no PR.**

## PR body template

```markdown
## Experts minted/updated: <names>

**Source:** <study `<topic>/<research-short-name>` | standalone>
Minted by `ask-an-expert` and challenged once by the adversarial reviewer. A human reviews and merges
this PR.

### Experts
- `experts/<name>.md` — <one line: the expertise / Scope summary>. <residual adversarial-gap note, or "clean">

### Provenance
<Why each expert was minted/updated, and what an update added — mirrors each file's Provenance.>

### Version
Patch bump <old> → <new>.
```

## Failure handling

- `gh` missing / unauthenticated → **stop**; tell the user to run `gh auth login` (suggest the `!`
  prefix). **Never fake a PR URL.**
- `git push` / `gh pr create` fails (incl. transient `unexpected EOF`) → retry 2–3×; the commits
  already live on `experts/<run-slug>` in the bare repo, so report honestly and offer manual push.
  Never claim a PR that did not open.
- Push rejected (branch diverged) → `git -C "$WT" pull --ff-only origin "$BRANCH"` and retry; else
  report the conflict.
- Your branch/worktree vanished (a misbehaving concurrent run) → recover from the bare repo's
  reflog/objects; do not restart. Committed expert work survives in git objects.
- Shared path looks broken → surface it; never delete/reset it.
````

- [ ] **Step 2: Verify the file exists and carries the required anchors**

Run:
```bash
F=plugins/madskillz/skills/ask-an-expert/references/expert-writeback.md
test -f "$F" || echo "MISSING FILE"
for p in '~/.madskillz/experts/repo.git' 'experts/<run-slug>' \
         'gh pr create -R bubthegreat/madskillz' 'defer-publish' \
         'Fail-closed halt' 'never fake'; do
  grep -qF "$p" "$F" && echo "ok: $p" || echo "MISSING: $p"
done
```
Expected: six `ok:` lines, no `MISSING`. Any `MISSING` line names an anchor to add to the file.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/ask-an-expert/references/expert-writeback.md
git commit -m "feat(ask-an-expert): add expert write-back + PR procedure (expert-writeback.md)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Wire `ask-an-expert`'s own flow to write back + publish

Make the skill's own documents say minting persists to the canonical clone and publishes per `expert-writeback.md`, with the run-id/defer-publish input and the reuse-check reading `origin/main`.

**Files:**
- Modify: `plugins/madskillz/skills/ask-an-expert/SKILL.md`
- Modify: `plugins/madskillz/skills/ask-an-expert/references/find-the-right-expert.md`
- Modify: `plugins/madskillz/skills/ask-an-expert/experts/README.md`

**Interfaces:**
- Consumes (from Task 1): `references/expert-writeback.md`, the terms **run-id**/**defer-publish**, publish modes.
- Produces: the contract that callers (Task 3/4) pass **run-id + defer-publish** to defer publishing.

- [ ] **Step 1: SKILL.md — extend the intro paragraph.** Find this exact text (lines 16–19):

```
Define, maintain, and query reusable **domain-expert personas**. Two ways in: ask an
already-defined expert a question directly, or have one **found and defined** for a domain
that isn't covered yet. Experts live in `experts/<concise-name>.md` and are reused across the
whole `scientific-*` research family and standalone.
```

Replace with:

```
Define, maintain, and query reusable **domain-expert personas**. Two ways in: ask an
already-defined expert a question directly, or have one **found and defined** for a domain
that isn't covered yet. Experts live in `experts/<concise-name>.md` and are reused across the
whole `scientific-*` research family and standalone. The library is owned here but **lives in the
madskillz repo** — so minting or updating an expert is a change to a canonical source: this skill
**writes it back to madskillz and opens a PR** for human review (never leaving it in the project
being researched or the throwaway plugin cache). See `references/expert-writeback.md`.
```

- [ ] **Step 2: SKILL.md — extend Step 2 to carry the write-back + run context.** Find this exact text (lines 45–51):

```
## Step 2 — Find the right expert (when none fits)

Follow `references/find-the-right-expert.md`: derive the *actual* expertise the question
demands, check whether a standing reviewer or an existing expert already covers it (reuse or
extend rather than duplicate), and only when neither fits, write a new
`experts/<concise-name>.md` per `references/expert-format.md`. The finder either routes to an
existing persona, returns a ready expert file, or gives an honest "expertise not establishable."
```

Replace with:

```
## Step 2 — Find the right expert (when none fits)

Follow `references/find-the-right-expert.md`: derive the *actual* expertise the question
demands, check whether a standing reviewer or an existing expert already covers it (reuse or
extend rather than duplicate), and only when neither fits, write a new
`experts/<concise-name>.md` per `references/expert-format.md`. The finder either routes to an
existing persona, returns a ready expert file, or gives an honest "expertise not establishable."

A minted or updated expert is **persisted to the canonical madskillz clone and published as a PR**
per `references/expert-writeback.md`. A research caller (`scientific-peer-review`/`scientific-study`)
passes a **run-id** and **defer-publish** so the run's experts bundle into one PR opened at study
end; a standalone ask publishes immediately (one PR per expert). Reuse-with-no-change and a
fail-closed "expertise not establishable" open **no PR**.
```

- [ ] **Step 3: find-the-right-expert.md — anchor the reuse-check to the canonical clone.** Find this exact text (lines 32–33):

```
   2. **Existing `experts/`.** List them; if one covers the derived requirements, **reuse it**;
      if it is close but missing something, **update** it rather than create a near-duplicate.
```

Replace with:

```
   2. **Existing `experts/`.** List them **from the canonical madskillz clone (`origin/main`,
      freshly fetched per `expert-writeback.md`)** — the real current library, not a stale plugin
      cache. If one covers the derived requirements, **reuse it**; if it is close but missing
      something, **update** it rather than create a near-duplicate.
```

- [ ] **Step 4: find-the-right-expert.md — anchor the write + publish.** Find this exact text (lines 34–37):

```
3. **Define or update the persona.** If an existing reviewer or expert fits, extend *that* file.
   Only when neither reasonably covers the need, write a new `experts/<concise-name>.md` per
   `expert-format.md`, with **Scope** and **Boundaries** matching the derived requirements, and a
   **Provenance** note (which request created or extended it, and what was added).
```

Replace with:

```
3. **Define or update the persona.** If an existing reviewer or expert fits, extend *that* file.
   Only when neither reasonably covers the need, write a new `experts/<concise-name>.md` per
   `expert-format.md`, with **Scope** and **Boundaries** matching the derived requirements, and a
   **Provenance** note (which request created or extended it, and what was added). Write and commit
   it **into the canonical madskillz clone (not the current project or the plugin cache) and publish
   it as a PR** — see `expert-writeback.md`.
```

- [ ] **Step 5: find-the-right-expert.md — note the publish in Output.** Find this exact text (lines 59–62):

```
## Output

The path to the ready `experts/<name>.md` (reused, created, or updated) plus a one-line note on
which and why; or an honest "expertise not establishable" with the reason.
```

Replace with:

```
## Output

The path to the ready `experts/<name>.md` (reused, created, or updated) — for a minted/updated
expert this is its path inside the run's `expert-writeback.md` worktree — plus a one-line note on
which and why, and (when published immediately) the PR URL; or an honest "expertise not
establishable" with the reason. Deferred (in-study) minting leaves publishing to the study's
end-of-run step.
```

- [ ] **Step 6: experts/README.md — note the write-back flow.** Find this exact text (lines 8–10):

```
- **Adding one:** the finder (`../references/find-the-right-expert.md`) derives the real
  requirements, reuses or extends an existing expert when possible, and only then mints a new
  file. A minted/updated expert is challenged once by the adversarial reviewer before use.
```

Replace with:

```
- **Adding one:** the finder (`../references/find-the-right-expert.md`) derives the real
  requirements, reuses or extends an existing expert when possible, and only then mints a new
  file. A minted/updated expert is challenged once by the adversarial reviewer before use, then
  **written back to the madskillz repo and opened as a PR** for human review — minting through a
  run does not edit this directory in place; see `../references/expert-writeback.md`.
```

- [ ] **Step 7: Verify the cross-references resolve**

Run:
```bash
D=plugins/madskillz/skills/ask-an-expert
grep -l 'expert-writeback.md' "$D/SKILL.md" "$D/references/find-the-right-expert.md" "$D/experts/README.md"
grep -c -e 'defer-publish' -e 'origin/main' "$D/SKILL.md" "$D/references/find-the-right-expert.md"
```
Expected: the first command lists all three files (each now references `expert-writeback.md`); the second shows `defer-publish` and `origin/main` present in the two skill docs.

- [ ] **Step 8: Commit**

```bash
git add plugins/madskillz/skills/ask-an-expert/SKILL.md \
        plugins/madskillz/skills/ask-an-expert/references/find-the-right-expert.md \
        plugins/madskillz/skills/ask-an-expert/experts/README.md
git commit -m "feat(ask-an-expert): persist minted experts to madskillz + open a PR

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Research family — request side passes run-id + defer-publish

So a study's minted experts are committed to the sync clone under the run's branch and bundled, not stored in the research project.

**Files:**
- Modify: `plugins/madskillz/skills/scientific-peer-review/SKILL.md`
- Modify: `plugins/madskillz/skills/scientific-study/references/review-loop.md`

**Interfaces:**
- Consumes (from Task 2): the contract that `ask-an-expert` accepts **run-id + defer-publish**.
- Produces: the run-slug = `<topic>__<research-short-name>` and the expectation that experts publish at the study's Step 6 (consumed by Task 4).

- [ ] **Step 1: scientific-peer-review/SKILL.md — pass run context to ask-an-expert.** Find this exact text (lines 86–89):

```
escalates "out of my depth on X"), check whether the panel credibly covers the paper's
domain(s). If a central claim needs expertise none of the standing reviewers have, write a
`requested-expert.md` (domain; why — which claims/sections; the questions it must answer; who
raised it) and resolve it with the **`ask-an-expert`** skill — reuse an existing
`experts/<name>.md` or mint one via its finder. Add the resolved expert to the panel as an
```

Replace with:

```
escalates "out of my depth on X"), check whether the panel credibly covers the paper's
domain(s). If a central claim needs expertise none of the standing reviewers have, write a
`requested-expert.md` (domain; why — which claims/sections; the questions it must answer; who
raised it) and resolve it with the **`ask-an-expert`** skill — reuse an existing
`experts/<name>.md` or mint one via its finder. When invoked inside a study run, pass the study's
**run-id (`<topic>__<research-short-name>`) and `defer-publish`** so a minted expert is committed to
the madskillz sync clone on the run's branch and **bundled into one PR opened at study end** (see
ask-an-expert's `references/expert-writeback.md`) — never stored in the research project. Add the
resolved expert to the panel as an
```

- [ ] **Step 2: review-loop.md — pass run context in the expert gate.** Find this exact text (lines 43–46):

```
`scientific-peer-review` runs a domain-coverage triage each review (see its `SKILL.md`). When
the paper needs expertise the panel lacks, it writes a `requested-expert.md`, resolves it via
the **`ask-an-expert`** skill (reuse or mint), and adds the expert to the panel —
auto-continuing the cycle. A minted/updated expert is challenged once by the adversarial
```

Replace with:

```
`scientific-peer-review` runs a domain-coverage triage each review (see its `SKILL.md`). When
the paper needs expertise the panel lacks, it writes a `requested-expert.md`, resolves it via
the **`ask-an-expert`** skill (reuse or mint) — passing the study's **run-id
(`<topic>__<research-short-name>`) and `defer-publish`** so a minted expert is committed to the
madskillz sync clone on the run's branch and published as **one bundled madskillz PR at Step 6**
(see `git-workflow.md` §4.1 and ask-an-expert's `references/expert-writeback.md`), not left in the
research project — and adds the expert to the panel, auto-continuing the cycle. A minted/updated
expert is challenged once by the adversarial
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -c 'defer-publish' plugins/madskillz/skills/scientific-peer-review/SKILL.md \
                        plugins/madskillz/skills/scientific-study/references/review-loop.md
```
Expected: each file reports `1` (both now pass `defer-publish`).

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-peer-review/SKILL.md \
        plugins/madskillz/skills/scientific-study/references/review-loop.md
git commit -m "feat(research): pass run-id + defer-publish when minting experts

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Research family — publish side opens + links the bundled expert PR

Add the end-of-run publish step to the study git workflow and link the expert PR from the research PR.

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/references/git-workflow.md`
- Modify: `plugins/madskillz/skills/scientific-study/SKILL.md`

**Interfaces:**
- Consumes (from Task 1 & 3): `expert-writeback.md`'s publish step; the run-slug branch `experts/<run-slug>`.
- Produces: nothing downstream (terminal wiring).

- [ ] **Step 1: git-workflow.md — add the publish sub-section.** Find this exact text (the end of §4, lines 205–206):

```
Report the PR URL. Do **not** merge. The human reviews and merges the PR.
```

Replace with:

```
Report the PR URL. Do **not** merge. The human reviews and merges the PR.

### 4.1 Publish staged experts (separate madskillz PR)

If this run minted or updated any experts (the domain-coverage triage did so with `defer-publish`),
publish them now as **one bundled PR to `bubthegreat/madskillz`** per ask-an-expert's
`references/expert-writeback.md` (its run-slug is this study's `<topic>__<research-short-name>`): it
patch-bumps `plugin.json`, pushes the `experts/<run-slug>` branch, and opens the PR. This is a
**separate** PR from the research PR above — the experts belong to madskillz, not to
`jmresearch/research`. Capture its URL to link in the research PR's "Domain experts" section. If no
expert was minted this run, skip. `gh`/push failure handling is the same as above — never fake a PR.
```

- [ ] **Step 2: git-workflow.md — link the expert PR from the PR template.** Find this exact text (lines 284–286):

```
### Domain experts
<Experts consulted or minted for this review (each `experts/<name>.md`), any residual
expertise gap the adversarial reviewer noted, or "none".>
```

Replace with:

```
### Domain experts
<Experts consulted or minted for this review (each `experts/<name>.md`), any residual
expertise gap the adversarial reviewer noted, or "none". For experts **minted/updated** this run,
link the bundled madskillz PR that ships them (opened per §4.1).>
```

- [ ] **Step 3: SKILL.md — mention the expert PR in Step 6.** Find this exact text (lines 125–132):

```
## Step 6 — Publish as a PR

Lay out the folder per `references/repo-layout.md`, push the study branch, and open
a PR into the default branch of `jmresearch/research` (per `git-workflow.md`). The
PR description summarizes: the study (and whether it is novel or a
replication/validation), how each review cycle changed the paper, any **residual
findings**, any domain **experts** consulted or minted (and any unmet-expertise halt),
and the compliance outcomes. Report the PR URL. The human reviews and merges there.
```

Replace with:

```
## Step 6 — Publish as a PR

Lay out the folder per `references/repo-layout.md`, push the study branch, and open
a PR into the default branch of `jmresearch/research` (per `git-workflow.md`). The
PR description summarizes: the study (and whether it is novel or a
replication/validation), how each review cycle changed the paper, any **residual
findings**, any domain **experts** consulted or minted (and any unmet-expertise halt),
and the compliance outcomes. If this run **minted or updated** any experts, also open the
**separate bundled madskillz PR** that ships them (per `git-workflow.md` §4.1) and link it from
the research PR's "Domain experts" section — minted experts live in the madskillz repo, not in
`jmresearch/research`. Report the PR URL. The human reviews and merges there.
```

- [ ] **Step 4: Verify**

Run:
```bash
grep -c '4.1' plugins/madskillz/skills/scientific-study/references/git-workflow.md
grep -c 'bundled madskillz PR' plugins/madskillz/skills/scientific-study/SKILL.md
```
Expected: the first prints `≥2` (the new `### 4.1` heading plus references to it), the second prints `1`.

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/references/git-workflow.md \
        plugins/madskillz/skills/scientific-study/SKILL.md
git commit -m "feat(scientific-study): open + link the bundled expert PR at study end

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Add behavior evals for write-back + PR

Capture the new behavior as gradeable evals so a future change that regresses it is caught.

**Files:**
- Modify: `plugins/madskillz/skills/ask-an-expert/evals/evals.json`

**Interfaces:**
- Consumes: the behavior defined in Tasks 1–4.
- Produces: nothing downstream.

- [ ] **Step 1: Insert two eval objects.** In `evals.json`, find this exact text (the `no-trigger-control` entry that ends the `tests` array, lines 45–50):

```
    {
      "id": "no-trigger-control",
      "prompt": "What's the capital of France?",
      "should_trigger": false,
      "grading_criteria": ["Skill does not trigger"]
    }
  ]
```

Replace with (inserts the two new entries before the control case):

```
    {
      "id": "mint-writes-back-and-prs",
      "prompt": "Mint a new expert on tokamak plasma confinement and have it weigh in on this fusion claim.",
      "should_trigger": true,
      "grading_criteria": [
        "Mints the expert into the canonical madskillz sync clone (~/.madskillz/experts/...), NOT into the current working project or the plugin cache",
        "Opens a PR to bubthegreat/madskillz (base main) carrying the new expert plus a patch version bump, per references/expert-writeback.md",
        "Does not leave the expert file committed in the project being worked on",
        "Never fabricates a PR URL; if gh is missing/unauthenticated it stops with guidance instead"
      ]
    },
    {
      "id": "reuse-opens-no-pr",
      "prompt": "Ask a systems-theory expert whether this inputs-to-outputs framing holds up.",
      "should_trigger": true,
      "grading_criteria": [
        "Reuses the existing experts/systems-theory.md rather than minting a near-duplicate",
        "Opens NO PR, because reusing an unchanged expert is not a change to the canonical source"
      ]
    },
    {
      "id": "no-trigger-control",
      "prompt": "What's the capital of France?",
      "should_trigger": false,
      "grading_criteria": ["Skill does not trigger"]
    }
  ]
```

- [ ] **Step 2: Verify the JSON still parses**

Run:
```bash
python3 -m json.tool plugins/madskillz/skills/ask-an-expert/evals/evals.json >/dev/null && echo OK
grep -c -e 'mint-writes-back-and-prs' -e 'reuse-opens-no-pr' plugins/madskillz/skills/ask-an-expert/evals/evals.json
```
Expected: prints `OK`, then `2` (both new eval ids present).

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/ask-an-expert/evals/evals.json
git commit -m "test(ask-an-expert): evals for expert write-back + PR (and reuse opens no PR)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Ship — version bump + final consistency sweep

Bump the plugin for the feature and confirm the cross-references are internally consistent.

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: the shipped feature at `0.13.0`.

- [ ] **Step 1: Bump the version.** In `plugins/madskillz/.claude-plugin/plugin.json`, find:

```
  "version": "0.12.0",
```

Replace with:

```
  "version": "0.13.0",
```

- [ ] **Step 2: Consistency sweep — every doc that should reference the keystone does**

Run:
```bash
grep -rl 'expert-writeback' plugins/madskillz/skills | sort
python3 -m json.tool plugins/madskillz/.claude-plugin/plugin.json | grep '"version"'
```
Expected: the `grep` lists at least `ask-an-expert/SKILL.md`, `ask-an-expert/references/find-the-right-expert.md`, `ask-an-expert/references/expert-writeback.md`, `ask-an-expert/experts/README.md`, `scientific-peer-review/SKILL.md`, `scientific-study/references/review-loop.md`, `scientific-study/references/git-workflow.md`; the version prints `0.13.0`.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore: bump madskillz to 0.13.0 (mint experts back into madskillz via PR)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Validation (manual — run once after Task 6; exercises real git/gh)

These are the spec's end-to-end checks. They open a **real test PR**; close it and delete the test branch afterward.

- [ ] **Standalone mint, end-to-end.** Ask `ask-an-expert` to mint a throwaway expert standalone (e.g. "mint an expert on tokamak plasma confinement and answer a quick question"). Confirm: (a) the bare clone is created at `~/.madskillz/experts/repo.git`; (b) the expert file is committed on an `experts/<slug>` branch there; (c) a PR opens against `bubthegreat/madskillz` base `main` with a patch bump; (d) **nothing** is written into the current project (`git -C . status` clean of the expert file). Close the PR and delete the branch.
- [ ] **Reuse opens no PR.** Ask a `systems-theory` question that an existing expert covers; confirm it reuses `experts/systems-theory.md` and opens **no** PR.
- [ ] **In-study bundling (if running a real study).** Drive a small study whose triage mints two experts; confirm both land on **one** `experts/<topic>__<short-name>` branch and **one** bundled PR opens at study end, linked from the research PR's "Domain experts" section, with the research PR still targeting `jmresearch/research`.
- [ ] **Headless writability.** Confirm a least-privilege headless run can create the clone and commit under `~/.madskillz/experts/` with no guard denial.
- [ ] **Fail-closed.** Confirm an unestablishable-expertise request opens **no** PR.

## Notes for the executor

- This plan only edits Markdown + JSON; there is no build or unit-test suite to run. "Verification" steps are `grep`/`json.tool` structural checks. The real behavior lives in how an agent follows these skill docs, exercised by the manual validation above.
- Do the edits with exact find/replace — the surrounding skill prose is load-bearing and reviewed; do not paraphrase neighbouring text.
- Keep each task's commit to just its listed files.
