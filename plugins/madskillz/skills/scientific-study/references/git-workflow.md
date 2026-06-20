# Git workflow — study branch, iterative commits, PR

Target: the **private** repo `jmresearch/research`. Flow: do all the work in an
**isolated per-study git worktree** on a **study branch**, commit the draft and each
review cycle separately, then open a **PR** into the default branch. A human reviews and
merges — this skill never merges and never pushes to the default branch directly. Use
`gh` for auth (private access) and for opening the PR. Never claim a commit/push/PR that
did not happen.

**Why a worktree (concurrency isolation).** Multiple research teams run concurrently
against the same local cache. A single shared checkout is unsafe: one run's
`checkout`/`reset --hard` yanks the working tree out from under another. Instead the cache
is a **bare** clone (shared object store, no working tree to collide on), and **each study
gets its own worktree** on its own branch. Two studies then share only the object database
(concurrent `fetch`/`worktree add` are lock-safe); their working trees never collide, and
no command ever resets shared state.

> These are **manual** `git worktree` commands against the *external* research clone — the
> harness's native worktree tool isolates the current project (madskillz), not an arbitrary
> external clone, so it does not apply here. Do not "simplify" these to a native call.

## 1. Preflight — verify access (stop if it fails)

```bash
gh auth status                                   # is gh installed & authenticated?
DEFAULT_BRANCH=$(gh repo view jmresearch/research --json defaultBranchRef -q .defaultBranchRef.name)
```

- `gh` missing or not authenticated → stop. Tell the user to run `gh auth login`
  (suggest the `!` prefix so it runs inline). Do not fake anything.
- `gh repo view` fails → no access / repo missing. Report honestly; do not proceed.
- Capture `DEFAULT_BRANCH` — do not assume `main`.

## 2. Resolve the shared bare cache and create an isolated study worktree

The cache is a **bare** clone (object store only). Each study works in its **own worktree**
on its **own branch** — so concurrent runs never share a working tree.

```bash
ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/jmresearch-research"
BARE="$ROOT/repo.git"                              # shared bare clone (no working tree)

# One-time: create the bare clone. (Migration: an older non-bare checkout may exist at
# "$ROOT" directly — it is now vestigial and can be deleted; this skill no longer uses it.)
[ -d "$BARE" ] || gh repo clone jmresearch/research "$BARE" -- --bare
# Track remotes under refs/remotes/origin/* (a bare clone otherwise maps heads directly,
# which has no origin/<branch> ref and would force-update local study branches on fetch).
git -C "$BARE" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C "$BARE" fetch origin --prune                # refresh remote-tracking refs (lock-safe, concurrent-OK)

BRANCH="study/<topic>/<research-short-name>"
SLUG="<topic>__<research-short-name>"               # filesystem-safe; unique per study
WT="$ROOT/worktrees/$SLUG"                          # THIS study's isolated worktree

# If an older NON-bare cache exists at "$ROOT", run the §2.1 migration here first — it imports
# any in-flight study branches as old-cache/* refs that the resume chain below can attach to.

if [ -d "$WT" ]; then
  :                                                                         # resume: reuse the existing worktree
elif git -C "$BARE" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$BARE" worktree add "$WT" "$BRANCH"                               # resume: local branch exists
elif git -C "$BARE" show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git -C "$BARE" worktree add "$WT" -b "$BRANCH" "origin/$BRANCH"           # resume: branch was pushed earlier
elif git -C "$BARE" show-ref --verify --quiet "refs/remotes/old-cache/$BRANCH"; then
  git -C "$BARE" worktree add "$WT" -b "$BRANCH" "old-cache/$BRANCH"        # resume: in-flight work migrated from the old cache (§2.1)
else
  git -C "$BARE" worktree add "$WT" -b "$BRANCH" "origin/$DEFAULT_BRANCH"   # new study off up-to-date default
fi
```

All subsequent git commands run **in the worktree** (`git -C "$WT" …`), never against
`$BARE` or any shared checkout. Resuming a study reuses its worktree/branch and never
resets committed work.

### 2.1 Migrating in-flight work from an older non-bare cache (one-time)

Earlier versions kept a single **non-bare** clone at `$ROOT` itself (so `$ROOT/.git` exists
and `$ROOT/repo.git` does not). In-flight study branches and uncommitted edits may still live
there. Migrate **non-destructively** — never delete the old checkout and never discard
uncommitted work; the user may have other branches still to carry over.

```bash
OLD_GITDIR="$ROOT/.git"
if [ -d "$OLD_GITDIR" ]; then
  # 1) Surface — do NOT auto-commit or discard — any uncommitted work in the old checkout.
  if [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]; then
    git -C "$ROOT" status --short
    git -C "$ROOT" stash list
    # STOP and ask the user to commit or stash this on its branch before continuing.
    # (Their in-flight edits live only in this working tree; never throw them away.)
  fi
  # 2) Import the old checkout's in-flight study branches into the bare repo as remote-tracking
  #    refs — safe: never clobbers origin or local heads, never moves the old branches.
  git -C "$BARE" remote add old-cache "$OLD_GITDIR" 2>/dev/null \
    || git -C "$BARE" remote set-url old-cache "$OLD_GITDIR"
  git -C "$BARE" fetch old-cache '+refs/heads/study/*:refs/remotes/old-cache/study/*'
  git -C "$BARE" for-each-ref --format='migrated in-flight branch: %(refname:short)' \
    refs/remotes/old-cache/study
fi
```

Resuming any of those studies then goes through the normal §2 path: the resume chain attaches
a worktree off `old-cache/<branch>` and continues it as a real study branch with its full
history intact. **The old non-bare cache is left untouched** — remove it only once every
in-flight branch has been carried over and the user confirms. (Re-running this is safe and
idempotent: it re-imports the latest state of any branches not yet migrated.)

## 3. Commit cadence — make the evolution visible

Commit at each meaningful stage, never squashed, so the PR diff history tells the story:

```bash
# initial draft (Step 2)
git -C "$WT" add "<topic>/<research-short-name>"
git -C "$WT" commit -m "draft: initial <research-short-name>"

# one commit PER review cycle (Step 3) — repeat per cycle
git -C "$WT" add "<topic>/<research-short-name>"
git -C "$WT" commit -m "review cycle <N>: address <short summary>"

# compliance gate result (Step 4)
git -C "$WT" add "<topic>/<research-short-name>"
git -C "$WT" commit -m "compliance: gate outcome for <research-short-name>"
```

Stage only this study's folder — never `git add -A`. The worktree is a full checkout of
the default branch, so it also contains *other* studies' folders; `git add -A` would sweep
those in. End each commit message with:
`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 4. Push the branch and open the PR (Step 5)

```bash
git -C "$WT" push -u origin "$BRANCH"
gh -R jmresearch/research pr create \
  --base "$DEFAULT_BRANCH" --head "$BRANCH" \
  --title "research(<topic>): <research-short-name>" \
  --body-file <generated PR body>          # template below
```

Report the PR URL. Do **not** merge. The human reviews and merges the PR.

## 5. Human-review follow-ups (Step 6)

Apply the requested change, re-gate it (see `review-loop.md`), then add it as a
**separate** commit on the same branch and push — so the human's requested change is
its own visible diff:

```bash
git -C "$WT" add "<topic>/<research-short-name>"
git -C "$WT" commit -m "human review: <summary>"
git -C "$WT" push origin "$BRANCH"
```

Optionally leave a `gh pr comment` noting what changed. Still never merge. (If the worktree
was cleaned up after the PR, §2's resume path re-attaches one from the existing branch.)

## 6. Worktree cleanup (optional)

The branch lives on the remote once pushed and in the bare repo's refs; the worktree's
working files are reclaimable disk. After the branch is pushed you **may** remove the
worktree — keep the branch and the bare repo:

```bash
git -C "$BARE" worktree remove "$WT"      # add --force only if it refuses on a dirty tree you intend to discard
git -C "$BARE" worktree prune             # clear stale metadata (e.g. a worktree dir deleted by hand)
```

Removing the worktree does **not** delete the branch — resuming or handling human-review
follow-ups just re-creates a worktree via §2. Never delete the bare repo mid-flight; other
concurrent studies share it.

## 7. Failure handling

- Push rejected (branch diverged because you pushed earlier) → `git -C "$WT" pull --ff-only`
  the branch and retry; otherwise report the conflict.
- No network / no push access → commits exist locally **in the worktree** (and the bare
  repo's refs). Report honestly and offer to leave them for the user to push later. Never
  report a PR that was not opened.
- `git worktree add` fails — path already exists, or the branch is checked out in another
  worktree → run `git -C "$BARE" worktree prune`, pick a fresh `$WT` path (or reuse the
  existing one if it is this same study), and retry. Never `reset --hard` a shared checkout
  to force it.
- `gh pr create` fails → report it; the branch is pushed, so the user can open the PR
  manually. Do not claim a PR URL you did not get back.

## PR body template

```markdown
## <Paper title>

**Topic:** <topic> · **Short name:** <research-short-name>
**Type:** <novel research | replication/validation of established work>

Agentic-peer-reviewed before human review. A human reviews and merges this PR.

### What this study does
<2–4 sentences.>

### Review cycles (how feedback changed the paper)
- Cycle 1 — <blockers/majors raised → what was edited>
- Cycle 2 — <…>
(One bullet per cycle; see `review/cycle-N.md` for the full reports.)

### Residual findings (NOT resolved by the loop)
<List any remaining blockers/majors/minors and disputed findings, or "none">

### Compliance & privacy
<Datasets included vs reference-only; PII/PHI screen result; any recorded override.
See COMPLIANCE.md / ATTRIBUTIONS.md.>

### Domain experts
<Experts consulted or minted for this review (each `experts/<name>.md`), any residual
expertise gap the adversarial reviewer noted, or "none".>
```
