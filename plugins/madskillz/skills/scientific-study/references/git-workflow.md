# Git workflow — study branch, iterative commits, PR

Target: the **private** repo `jmresearch/research`. Flow: do all the work on a
**study branch**, commit the draft and each review cycle separately, then open a
**PR** into the default branch. A human reviews and merges — this skill never merges
and never pushes to the default branch directly. Use `gh` for auth (private access)
and for opening the PR. Never claim a commit/push/PR that did not happen.

## 1. Preflight — verify access (stop if it fails)

```bash
gh auth status                                   # is gh installed & authenticated?
DEFAULT_BRANCH=$(gh repo view jmresearch/research --json defaultBranchRef -q .defaultBranchRef.name)
```

- `gh` missing or not authenticated → stop. Tell the user to run `gh auth login`
  (suggest the `!` prefix so it runs inline). Do not fake anything.
- `gh repo view` fails → no access / repo missing. Report honestly; do not proceed.
- Capture `DEFAULT_BRANCH` — do not assume `main`.

## 2. Resolve a working checkout (cache) and create the study branch

```bash
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/jmresearch-research"
if [ -d "$CACHE/.git" ]; then
  git -C "$CACHE" fetch origin
  git -C "$CACHE" checkout "$DEFAULT_BRANCH"
  git -C "$CACHE" reset --hard "origin/$DEFAULT_BRANCH"   # cache is a disposable mirror
else
  gh repo clone jmresearch/research "$CACHE"
fi
BRANCH="study/<topic>/<research-short-name>"
git -C "$CACHE" checkout -b "$BRANCH"        # branch off the up-to-date default
```

If the branch already exists (resuming a study), check it out and continue on it
instead of recreating it.

## 3. Commit cadence — make the evolution visible

Commit at each meaningful stage, never squashed, so the PR diff history tells the story:

```bash
# initial draft (Step 2)
git -C "$CACHE" add "<topic>/<research-short-name>"
git -C "$CACHE" commit -m "draft: initial <research-short-name>"

# one commit PER review cycle (Step 3) — repeat per cycle
git -C "$CACHE" add "<topic>/<research-short-name>"
git -C "$CACHE" commit -m "review cycle <N>: address <short summary>"

# compliance gate result (Step 4)
git -C "$CACHE" add "<topic>/<research-short-name>"
git -C "$CACHE" commit -m "compliance: gate outcome for <research-short-name>"
```

Stage only this study's folder — never `git add -A` (the cache is shared; don't sweep
in unrelated state). End each commit message with:
`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 4. Push the branch and open the PR (Step 5)

```bash
git -C "$CACHE" push -u origin "$BRANCH"
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
git -C "$CACHE" add "<topic>/<research-short-name>"
git -C "$CACHE" commit -m "human review: <summary>"
git -C "$CACHE" push origin "$BRANCH"
```

Optionally leave a `gh pr comment` noting what changed. Still never merge.

## 6. Failure handling

- Push rejected (branch diverged because you pushed earlier) → `git pull --ff-only`
  the branch and retry; otherwise report the conflict.
- No network / no push access → commits exist locally in the cache. Report honestly
  and offer to leave them for the user to push later. Never report a PR that was not
  opened.
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
```
