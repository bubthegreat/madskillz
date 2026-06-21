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

**Never clobber shared infrastructure (the one rule that prevents cross-study damage).** The bare
repo (`$ROOT/repo.git`), every *other* `study/*` branch ref, and every other study's worktree belong
to **concurrent runs**. Your run owns exactly two things: **your own `study/<topic>/<slug>` branch**
and **your own worktree dir**. Therefore, against the shared cache you must **never**:
`rm -rf`/recreate the bare repo; `git clone --bare` over an existing bare; `reset --hard`,
`branch -f`, or `push --force` any ref you did not create; `worktree remove`/`worktree prune` for a
worktree that is not yours; or `git checkout`/`reset` in a way that moves a *shared* HEAD. Re-cloning
or resetting the bare wipes sibling branch refs and worktree metadata — that is the exact failure this
layout exists to prevent. If a shared path looks broken, **stop and surface it**; do not "fix" it by
deleting it. (Updating *your own* study branch is fine; everything else is read-only.)

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

# Create the shared bare clone ONCE, atomically, and NEVER recreate or reset it — sibling
# studies' worktrees and branch refs live inside it (see "Never clobber shared infrastructure").
# (Migration: an older non-bare checkout may exist at "$ROOT" directly; do NOT delete it until
# §2.1 confirms every in-flight branch is carried over.)
if [ -d "$BARE" ] && git -C "$BARE" rev-parse --is-bare-repository >/dev/null 2>&1; then
  :                                                  # present and valid → reuse; NEVER re-clone/rm/reset it
elif [ -e "$BARE" ]; then
  # A path exists but is not a valid bare repo: a prior clone failed, or a concurrent run is
  # mid-create. Do NOT rm -rf it (another study may be racing on it). Stop and surface it.
  echo "FATAL: $BARE exists but is not a valid bare repo (failed/partial clone, or a concurrent"
  echo "       create in progress). Do NOT delete it blindly — a sibling study may share it."
  echo "       Wait/retry; if truly orphaned, the user removes it. Stopping."; exit 1
else
  # Clone into a unique temp dir, then publish atomically so two concurrent creators cannot
  # clobber each other. Use the SSH/owner URL git resolves — gh's `--bare` path can default to
  # HTTPS and fail non-interactively ("could not read Username for 'https://github.com'").
  URL=$(gh repo view jmresearch/research --json sshUrl -q .sshUrl)   # git@github.com:owner/repo.git
  mkdir -p "$ROOT"; TMP="$ROOT/.repo.git.tmp.$$"
  git clone --bare "$URL" "$TMP"
  git -C "$TMP" rev-parse --is-bare-repository >/dev/null 2>&1 \
    || { echo "FATAL: bare clone invalid"; rm -rf "$TMP"; exit 1; }
  mv -T --no-clobber "$TMP" "$BARE" 2>/dev/null || rm -rf "$TMP"     # lost the race → keep the winner's bare
fi
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

### 2.2 Recovery — a concurrent run clobbered your study anyway

If a *misbehaving* concurrent run violated the rules above (recreated the bare, or `reset --hard`'d
a shared checkout while your branch was its HEAD), your branch ref or worktree can vanish. **Your
committed work is not lost — git objects survive until garbage-collected.** Recover, don't restart:

```bash
# 1) Find your commits. Try, in order, the bare's reflog, the old cache, and dangling objects.
git -C "$BARE"        reflog --all 2>/dev/null | grep -i "<slug or commit subject>"
git -C "$ROOT/.git"   log --oneline -3 "$BRANCH" 2>/dev/null     # old non-bare cache often still has the ref
git -C "$BARE"        fsck --no-reflogs --lost-found 2>/dev/null | grep commit   # dangling commits
# 2) Restore YOUR branch ref (allowed — it is yours) to the recovered tip, WITHOUT a checkout
#    that could disturb another run:  git -C <repo-with-objects> branch -f "$BRANCH" <sha>
```

If the shared cache keeps getting clobbered, **stop fighting it and finish from a private clone
outside the cache** — collision-proof, and it preserves full commit history:

```bash
PRIV="$HOME/jmr-<slug>"                                   # OUTSIDE $ROOT; no other run touches it
git clone --branch "$BRANCH" "$ROOT/.git" "$PRIV"        # or clone from "$BARE", or from origin
git -C "$PRIV" remote set-url origin "$(gh repo view jmresearch/research --json sshUrl -q .sshUrl)"
cp -a "$WT/<topic>/<slug>/." "$PRIV/<topic>/<slug>/"     # overlay any on-disk worktree edits not yet committed
git -C "$PRIV" add "<topic>/<slug>"; git -C "$PRIV" commit -m "…"
git -C "$PRIV" push -u origin "$BRANCH"                   # then open/continue the PR from here
```

Never report this recovery as routine in the PR without saying it happened — note the incident (and
that no committed work was lost) in `journey/transcript.md`.

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
  worktree → run `git -C "$BARE" worktree prune` (safe: only drops metadata for worktree dirs
  that no longer exist — it never removes a live sibling worktree), pick a fresh `$WT` path (or
  reuse the existing one if it is this same study), and retry. Never `reset --hard` a shared
  checkout to force it.
- **Your branch ref or worktree vanished** (a concurrent run recreated the bare or reset a shared
  HEAD) → do not restart the study; recover the commits and finish from a private clone per
  **§2.2**. Your committed work survives in git objects.
- `bare clone fails "could not read Username for https://github.com"` → gh used HTTPS
  non-interactively; clone the SSH URL instead (`gh repo view … --json sshUrl`), as §2 now does.
- `gh pr create` fails (including transient `unexpected EOF` / `error connecting to api.github.com`)
  → retry 2–3×; the branch is already pushed, so the user can also open the PR manually. Do not
  claim a PR URL you did not get back.

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
