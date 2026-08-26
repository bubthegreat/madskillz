"""The voice store: the live voice dir as a git clone of a repo the user owns.

All git access for the pipeline lives here. Nothing else in the package shells out
to git against the store clone.
"""

import os
import socket
import subprocess
from pathlib import Path

from . import paths

GITATTRIBUTES = "corpus.jsonl merge=union\n"
GITIGNORE = "sync.log\n.sync.lock\n.last-sync-attempt\ntool/\n*.tmp\nvoice.md\nposts/\n"
README = """# voice store

Personal voice profiles (`core.md` + context overlays) and the prompt corpus
(`corpus.jsonl`) used by the madskillz `voice` skill via `voicectl`.

**Keep this repo private.** `corpus.jsonl` holds verbatim prompts.

Managed by `voicectl`; edit profiles by hand only when `voicectl status` shows no
pending update, then run `voicectl push`.
"""

LOCAL_ONLY_HINT = "local-only mode (no remote); run 'voicectl init --remote URL' to sync"

# Safety net for the conflict loop: a rebase over this many conflicting commits is a
# situation a human should look at, so we fall back to the remote state instead.
MAX_CONFLICT_STEPS = 20


class StoreError(Exception):
    pass


def git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run `git -C <cwd or voice dir> <args>`. Raises StoreError on failure when `check`."""
    r = subprocess.run(
        ["git", "-C", str(cwd or paths.voice_dir()), *args],
        capture_output=True,
        text=True,
    )
    if check and r.returncode != 0:
        raise StoreError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r


def is_repo(d: Path | None = None) -> bool:
    return ((d or paths.voice_dir()) / ".git").exists()


def remote_url(d: Path | None = None) -> str | None:
    if not is_repo(d):
        return None
    r = git("remote", "get-url", "origin", cwd=d, check=False)
    return r.stdout.strip() or None


def mode() -> str:
    """Returns 'synced' when the store is a clone with an origin, else 'local-only'."""
    return "synced" if remote_url() else "local-only"


def hostname() -> str:
    return socket.gethostname().split(".")[0]


def owner_name() -> str:
    r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
    return r.stdout.strip() or os.environ.get("USER") or "owner"


def scaffold(d: Path) -> list[str]:
    """Write the store's fixed support files if they are missing. Returns what was written."""
    written = []
    for name, body in (
        (".gitattributes", GITATTRIBUTES),
        (".gitignore", GITIGNORE),
        ("README.md", README),
    ):
        p = d / name
        if not p.exists():
            p.write_text(body, encoding="utf-8")
            written.append(name)
    return written


def seed_templates(d: Path, owner: str) -> list[str]:
    """Copy every shipped profile template that `d` does not already have.

    The copy is personalized: every `<handle>` placeholder becomes the owner's name,
    and the template marker in the frontmatter becomes `status: personal`.
    """
    src = paths.templates_dir()
    if not src.is_dir():
        raise StoreError(f"templates dir not found: {src}")
    seeded = []
    for t in sorted(src.glob("*.md")):
        dst = d / t.name
        if dst.exists():
            continue
        text = t.read_text(encoding="utf-8")
        text = text.replace("<handle>", owner)
        text = text.replace("status: template", "status: personal", 1)
        dst.write_text(text, encoding="utf-8")
        seeded.append(t.name)
    return seeded


def commit_all(message: str) -> bool:
    """Stage everything and commit when there is something to commit."""
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        return False
    git("commit", "-q", "-m", message)
    return True


def _conflicted_files() -> list[str]:
    out = git("diff", "--name-only", "--diff-filter=U", check=False).stdout
    return [line for line in out.split() if line]


def _rebase_in_progress() -> bool:
    g = paths.voice_dir() / ".git"
    return (g / "rebase-merge").exists() or (g / "rebase-apply").exists()


def _resolve_to_remote(files: list[str]) -> None:
    """Take the remote side of every conflicted file and mark it merged."""
    for f in files:
        git("checkout", "--ours", "--", f, check=False)
        git("add", "--", f, check=False)


def _drop_autostash() -> None:
    """Drop the stash entry `--autostash` left behind when its pop conflicted."""
    lines = [ln for ln in git("stash", "list", check=False).stdout.splitlines() if ln.strip()]
    if lines and lines[0].rstrip().endswith("autostash"):
        git("stash", "drop", "-q", check=False)


def pull() -> int:
    """Rebase local commits onto origin.

    Returns 0 when the pull was clean, 2 when at least one profile conflicted and the
    remote version was kept (the files are printed). Raises StoreError when the fetch
    itself fails. A local-only store is a no-op returning 0. Never returns with unmerged
    paths or conflict markers in the working tree.
    """
    if mode() != "synced":
        return 0
    branch = paths.store_branch()
    git("fetch", "-q", "origin", branch)
    r = git("pull", "-q", "--rebase", "--autostash", "origin", branch, check=False)

    conflicted: set[str] = set()
    if r.returncode != 0:
        if not _rebase_in_progress():
            raise StoreError(f"pull failed: {r.stderr.strip()}")
        # Remote wins for every conflicted profile. During a rebase "ours" is the upstream side.
        for _ in range(MAX_CONFLICT_STEPS):
            if not _rebase_in_progress():
                break
            files = _conflicted_files()
            conflicted.update(files)
            _resolve_to_remote(files)
            cont = git("-c", "core.editor=true", "rebase", "--continue", check=False)
            if cont.returncode != 0 and not _conflicted_files():
                # Resolving to the remote side emptied this commit; drop it and move on.
                git("rebase", "--skip", check=False)
        if _rebase_in_progress():
            # Still stuck after the cap. Unwind to where we started - the abort also restores
            # the autostash - and hand it to the owner. Local work is never thrown away.
            git("rebase", "--abort")
            raise StoreError(
                f"pull: could not rebase cleanly after {MAX_CONFLICT_STEPS} steps; "
                f"local commits and uncommitted changes were kept; "
                f"resolve manually in {paths.voice_dir()}"
            )

    # A failed autostash pop leaves unmerged paths but still exits 0, so check either way.
    # The rebase is over by now, so HEAD carries the remote side and "ours" is again remote.
    popped = _conflicted_files()
    if popped:
        conflicted.update(popped)
        _resolve_to_remote(popped)
        # keep them as plain working-tree files, not staged
        git("reset", "-q", "--", *popped)
        _drop_autostash()

    if not conflicted:
        return 0
    names = ", ".join(sorted(conflicted))
    print(f"pull: conflict on {names} - kept remote version; re-run your update")
    return 2


def push() -> str:
    """Commit any pending changes and push. On reject, pull once and retry."""
    if mode() != "synced":
        return f"push: {LOCAL_ONLY_HINT}"
    branch = paths.store_branch()
    made = commit_all(f"voice: update ({hostname()})")
    # A missing origin/<branch> ref makes rev-list fail; that is a store that has never been
    # pushed, so it has everything to push.
    ahead = git("rev-list", "--count", f"origin/{branch}..HEAD", check=False)
    if not made and ahead.returncode == 0 and ahead.stdout.strip() == "0":
        return "push: nothing to push"
    r = git("push", "-q", "origin", branch, check=False)
    if r.returncode != 0:
        pull()
        git("push", "-q", "origin", branch)
    return f"push: pushed to origin/{branch}"
