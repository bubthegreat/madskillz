# Git workflow — clone, lay out, commit, push

Target: the **private** repo `jmresearch/research`. Flow: commit and push straight
to its **default branch** (the user's choice — no PR/review gate). Use `gh` for
auth so private access works. Never claim a push that did not happen.

## 1. Preflight — verify access (stop if it fails)

```bash
gh auth status                                   # is gh installed & authenticated?
gh repo view jmresearch/research --json name,defaultBranchRef -q .defaultBranchRef.name
```

- `gh` missing or not authenticated → stop. Tell the user to run `gh auth login`
  (suggest the `!` prefix so it runs inline in the session). Do not fake a push.
- `gh repo view` fails → no access / repo missing. Report honestly; do not proceed.
- Capture the **default branch name** from the command above — do not assume `main`.

## 2. Resolve a working checkout (cache, don't re-clone every time)

```bash
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/jmresearch-research"
if [ -d "$CACHE/.git" ]; then
  git -C "$CACHE" fetch origin
  git -C "$CACHE" checkout "$DEFAULT_BRANCH"
  git -C "$CACHE" pull --ff-only origin "$DEFAULT_BRANCH"
else
  gh repo clone jmresearch/research "$CACHE"
fi
```

If `pull --ff-only` fails (local divergence), reset to the remote rather than
guessing at a merge: `git -C "$CACHE" reset --hard "origin/$DEFAULT_BRANCH"`
(the cache is a disposable mirror, not a workspace).

## 3. Lay out the item

Create/update `"$CACHE/<topic>/<research-short-name>/"` per `repo-layout.md`. Copy
license files verbatim from `references/licenses/`. If the folder already exists,
this is an **update** — show `git -C "$CACHE" status --short` so the user sees
exactly which files change, and confirm overwrites before committing.

## 4. Commit

```bash
git -C "$CACHE" add "<topic>/<research-short-name>"
git -C "$CACHE" status --short          # show the manifest for the Step 6 confirm
git -C "$CACHE" commit -m "research(<topic>): archive <research-short-name>

<one line on what changed; note reference-only datasets / overrides>

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

Stage only this item's folder — never `git add -A` (avoid sweeping in unrelated
working-tree state from a shared cache).

## 5. Push (only after the Step 6 confirmation)

```bash
git -C "$CACHE" push origin "$DEFAULT_BRANCH"
```

Then report the real result:

```bash
git -C "$CACHE" rev-parse HEAD          # commit SHA to report back
```

- Push rejected (non-fast-forward) → someone else pushed; `pull --ff-only` and
  retry once, otherwise report the conflict.
- No network / no push access → the commit exists locally in the cache. Report the
  failure honestly and offer to leave the local commit for the user to push later.
  Never report success.

## 6. Report

State: commit SHA, the pushed `<topic>/<research-short-name>/` path on the default
branch, and the per-input disposition (included / reference-only / omitted) plus
any recorded overrides. This is the deliverable.
