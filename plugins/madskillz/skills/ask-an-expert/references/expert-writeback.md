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
- **Its own dedicated clone** — never share a bare clone/worktree set across purposes; a gate or
  script elsewhere in this repo doing `reset --hard origin/main` on a shared clone would wipe an
  in-flight expert branch.

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
#   per expert-format.md (with a dated Provenance line)
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
