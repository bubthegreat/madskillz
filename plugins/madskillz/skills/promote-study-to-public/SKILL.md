---
name: promote-study-to-public
description: >-
  Use when the owner wants to promote a merged study from the private jmresearch/research
  repo to a public mirror repo (jmresearch/research-public) so others can read and
  reproduce the work. Trigger on "promote-study-to-public", "promote <topic/slug>",
  "make this study public", "push to the public repo", or "publish the study externally."
  Copies the study folder from the merged private branch to a new public-repo branch,
  opens a PR in the public repo, and returns the PR URL for the owner to merge.
  Never merges on its own; the human reviews and merges the public PR.
---

# promote-study-to-public: publish a merged study to the public mirror

Copy a study that has already been merged into `jmresearch/research` (the private repo)
into `jmresearch/research-public` (the public mirror), creating a branch + PR there for
a human to review and merge. The public PR is the visibility gate — nothing reaches the
public repo's default branch without human approval.

## Integrity stance (non-negotiable)

1. Only promote studies that are already merged to the private repo's default branch.
   Do not promote a draft, a pending PR, or work that has not cleared the human gate.
2. Never push directly to the public repo's default branch. Always open a PR.
3. Never strip content silently. If anything in the study folder looks like it should
   not be in a public repo (see §4, Privacy Scan), stop and ask.
4. Never fake a commit, push, or PR. If `gh` fails or push is rejected, report honestly.
5. The human merges. This skill opens and updates the PR; it never merges to main.

## Step 1 — Identify the study and confirm it is merged

Accept the study as `<topic>/<research-short-name>` (kebab-case slugs) from the command
argument, or prompt if not provided. Validate that both parts are kebab-case before proceeding.

```bash
DEFAULT_BRANCH=$(gh repo view jmresearch/research --json defaultBranchRef -q .defaultBranchRef.name)

# Confirm the study folder exists on the private repo's default branch
gh api repos/jmresearch/research/contents/<topic>/<research-short-name>/paper.md \
  --jq '.name' || {
  echo "Study not found in jmresearch/research on $DEFAULT_BRANCH — confirm it is merged and the path is correct."
  exit 1
}
```

If the study is not found: stop. Do not proceed with an unmerged or misidentified study.
Tell the owner to confirm the study is merged and the topic/slug are spelled correctly.

## Step 2 — Preflight: verify gh auth and public repo access

```bash
gh auth status                                  # must be authenticated

# Verify or create the public repo
if gh repo view jmresearch/research-public >/dev/null 2>&1; then
  echo "Public repo exists."
else
  echo "Public repo jmresearch/research-public does not exist."
  echo "Create it with: gh repo create jmresearch/research-public --public --description 'Public research mirror'"
  echo "Then re-run this skill."
  exit 1
fi

PUB_DEFAULT=$(gh repo view jmresearch/research-public --json defaultBranchRef -q .defaultBranchRef.name)
```

If the public repo does not exist, stop and give the owner the exact `gh repo create` command
to run. Do not create it automatically — the owner should own that action. Resume after they
confirm it exists.

## Step 3 — Set up the public repo worktree

The public repo uses its own isolated bare clone and worktree, separate from the private one.

```bash
PUB_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/jmresearch-research-public"
PUB_BARE="$PUB_ROOT/repo.git"

if [ -d "$PUB_BARE" ] && git -C "$PUB_BARE" rev-parse --is-bare-repository >/dev/null 2>&1; then
  :                                                    # reuse — NEVER recreate or reset
elif [ -e "$PUB_BARE" ]; then
  echo "FATAL: $PUB_BARE exists but is not a valid bare repo. Stopping."; exit 1
else
  PUB_URL=$(gh repo view jmresearch/research-public --json sshUrl -q .sshUrl)
  mkdir -p "$PUB_ROOT"; TMP="$PUB_ROOT/.repo.git.tmp.$$"
  git clone --bare "$PUB_URL" "$TMP"
  git -C "$TMP" rev-parse --is-bare-repository >/dev/null 2>&1 \
    || { echo "FATAL: bare clone invalid"; rm -rf "$TMP"; exit 1; }
  mv -T --no-clobber "$TMP" "$PUB_BARE" 2>/dev/null || rm -rf "$TMP"
fi

git -C "$PUB_BARE" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C "$PUB_BARE" fetch origin --prune

TOPIC="<topic>"
SLUG="<research-short-name>"
PUB_BRANCH="promote/<topic>/<research-short-name>"
PUB_FILESAFE="${TOPIC}__${SLUG}"
PUB_WT="$PUB_ROOT/worktrees/$PUB_FILESAFE"

if [ -d "$PUB_WT" ]; then
  :                                                         # resume
elif git -C "$PUB_BARE" show-ref --verify --quiet "refs/remotes/origin/$PUB_BRANCH"; then
  git -C "$PUB_BARE" worktree add "$PUB_WT" -b "$PUB_BRANCH" "origin/$PUB_BRANCH"
else
  git -C "$PUB_BARE" worktree add "$PUB_WT" -b "$PUB_BRANCH" "origin/$PUB_DEFAULT"
fi
```

## Step 4 — Privacy scan (fail-closed)

Before copying any content, scan the study folder in the private repo for anything that
should not be public:

- PII or PHI: names, email addresses, phone numbers, dates of birth, health record numbers,
  identifiable patient data
- Private URLs, internal server names, credentials, API keys
- Content that was marked reference-only or blocked in COMPLIANCE.md specifically because
  of redistribution restrictions — check `COMPLIANCE.md` before copying

```bash
# Pull the study folder from the private repo's default branch into a temp location
PRIV_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/jmresearch-research"
PRIV_WT="$PRIV_ROOT/worktrees/${TOPIC}__${SLUG}"

# If the private worktree exists, use it; otherwise extract via gh api or sparse clone
# The study folder we need: <topic>/<research-short-name>/
```

If the COMPLIANCE.md lists any asset as "blocked" or "reference-only due to redistribution
restriction," confirm those files are not present in the copy or are already stubs. If
anything is unclear: **stop and ask the owner** rather than proceeding. Never copy a file
whose public redistribution you cannot confirm.

## Step 5 — Copy the study and commit

Copy the study folder from the private repo source into the public worktree:

```bash
# Sync study folder content from private worktree (or a fresh sparse checkout)
STUDY_SRC="$PRIV_WT/$TOPIC/$SLUG"
STUDY_DST="$PUB_WT/$TOPIC/$SLUG"
mkdir -p "$STUDY_DST"
rsync -av --delete \
  --exclude='journey/'        \   # private provenance dialogue — omit from public
  "$STUDY_SRC/" "$STUDY_DST/"

# Stage and commit
git -C "$PUB_WT" add "$TOPIC/$SLUG"
git -C "$PUB_WT" commit -m "$(cat <<'EOF'
promote(<topic>/<research-short-name>): publish study to public mirror

Copied from jmresearch/research (private) — study passed peer review
and human approval before promotion. Source: <private-PR-URL or commit SHA>.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

**Important omissions from the public copy:**
- `journey/transcript.md` — the private owner↔assistant dialogue is provenance for the
  private repo and is the owner's to share or not. Omit it unless the owner explicitly
  asks to include it.
- Any file listed in COMPLIANCE.md as not for redistribution.

## Step 6 — Push and open a PR in the public repo

```bash
git -C "$PUB_WT" push -u origin "$PUB_BRANCH"

gh -R jmresearch/research-public pr create \
  --base "$PUB_DEFAULT" \
  --head "$PUB_BRANCH" \
  --title "research(<topic>): <research-short-name>" \
  --body-file <generated PR body>
```

### PR body template (public repo)

```markdown
## <Paper title>

**Topic:** <topic> · **Short name:** <research-short-name>
**Source:** Promoted from private repo `jmresearch/research` (merged PR: <link or SHA>)
**License:** CC BY 4.0 (paper, data, assets) · MIT (scripts)

This study was drafted and revised through agentic peer review before a human approved
and merged it in the private research repository. It is now promoted here for public
access and reproducibility.

### What this study does
<2–4 sentences from the original paper's abstract.>

### Compliance & privacy
<Disposition summary from COMPLIANCE.md: included vs. reference-only datasets; PII/PHI screen result.>
No `journey/transcript.md` included (private owner dialogue; omitted by default).

### Reproduction
<From README.md reproduction section.>

### Attribution
<From README.md licensing section.>
```

Report the public PR URL. The owner reviews and merges. This skill never merges.

## Step 7 — Human-review follow-ups

If the owner requests changes before merging the public PR:

1. Apply the change to the study folder in the public worktree.
2. Commit as `"human review: <summary>"` and push to the same branch.
3. Leave a `gh pr comment` noting what changed.

Still never merge — the human does.

## Worktree cleanup (optional, post-push)

```bash
git -C "$PUB_BARE" worktree remove "$PUB_WT"
git -C "$PUB_BARE" worktree prune
```

Removing the public worktree does not delete the branch. Resume + re-attach via §3 if
human-review follow-ups are needed after cleanup.

## Edge cases

- Study not merged in private repo → stop at §1; do not promote a draft.
- Public repo doesn't exist → stop at §2; give owner the creation command.
- COMPLIANCE.md missing or unreadable → fail-closed; stop and ask.
- PII/PHI detected in scan → stop; ask owner to de-identify or provide a reference-only stub.
- Push rejected (diverged) → `git -C "$PUB_WT" pull --ff-only` and retry; or report conflict.
- `gh pr create` fails → retry 2–3×; branch is pushed; owner can open PR manually. Never fake a PR URL.
- Owner asks to include `journey/transcript.md` → confirm intent explicitly before adding it.
- Owner asks to merge → out of scope; human merges the public PR.
- No public repo access → report honestly; do not proceed.
