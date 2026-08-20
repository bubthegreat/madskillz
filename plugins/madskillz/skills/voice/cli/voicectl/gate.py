"""SessionEnd gate: the cheap tier of the two-tier materiality check. Decides whether it
is worth spending an LLM, then detaches a headless updater agent. Port of
voice-sync-gate.sh; contract unchanged: never blocks teardown, never errors, no stdout."""

import os
import subprocess
import time
from datetime import datetime, timezone

from . import paths
from .corpus import count_since
from .profile import get_marker


def _log(msg: str) -> None:
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with paths.log_path().open("a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except OSError:
        pass


def _refresh_sync_repo(repo, branch) -> None:
    """Bring the DEDICATED sync repo to origin/<branch> so the agent's push fast-forwards.
    Guarded: refuses unless the repo is checked out on <branch>, so it can never reset a
    roaming working checkout. Safe only because the dedicated repo holds nothing precious."""
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True
        )

    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        _log(f"refresh: '{repo}' is not a git repo - skip")
        return
    cur = git("branch", "--show-current").stdout.strip()
    if cur != branch:
        _log(f"refresh: '{repo}' is on '{cur}', not target '{branch}' - refusing to reset")
        return
    if git("fetch", "origin", branch, "-q").returncode != 0:
        _log("refresh: fetch failed (offline?) - skip")
        return
    if git("reset", "--hard", f"origin/{branch}", "-q").returncode != 0:
        _log("refresh: reset failed - skip")
        return
    git("clean", "-fd", "-q")
    _log(f"refresh: '{repo}' reset to origin/{branch}")


def run() -> None:
    """Always returns (exit 0 semantics); all failures are logged, never raised."""
    try:
        _run()
    except Exception as e:  # noqa: BLE001 - the gate must never fail teardown
        _log(f"gate error: {e!r}")


def _run() -> None:
    voice_dir = paths.voice_dir()
    core = paths.core_path()
    corpus = paths.corpus_path()
    lock = voice_dir / ".sync.lock"
    stamp = voice_dir / ".last-sync-attempt"

    min_count = int(os.environ.get("VOICE_SYNC_MIN_COUNT", "15"))
    min_interval = int(os.environ.get("VOICE_SYNC_MIN_INTERVAL_SECONDS", "720"))
    lock_stale = int(os.environ.get("VOICE_SYNC_LOCK_STALE_SECONDS", "1800"))
    model = os.environ.get("VOICE_SYNC_MODEL", "opus")
    repo = paths.sync_repo()
    branch = paths.sync_branch()

    if not corpus.is_file() or not core.is_file():
        return

    now = time.time()
    if stamp.is_file() and now - stamp.stat().st_mtime < min_interval:
        return
    if lock.is_file():
        if now - lock.stat().st_mtime < lock_stale:
            _log("skip: sync already running")
            return
        _log("clearing stale lock")
        lock.unlink(missing_ok=True)

    marker = get_marker(core.read_text(encoding="utf-8"), "repo")
    count = count_since(corpus, marker)
    if count < min_count:
        return

    stamp.touch()
    lock.touch()
    _log(f"gate passed: {count} new msgs >= {min_count} - launching background sync (model={model})")

    if os.environ.get("VOICE_SYNC_AUTOREFRESH"):
        _refresh_sync_repo(repo, branch)

    # Test/override hook: run synchronously, then release the lock.
    launch = os.environ.get("VOICE_SYNC_LAUNCH")
    if launch:
        subprocess.run(launch, shell=True)
        lock.unlink(missing_ok=True)
        return

    import shutil as _shutil

    if not _shutil.which("claude"):
        _log("skip: claude not found")
        lock.unlink(missing_ok=True)
        return

    # Detach so SessionEnd never waits on the LLM. LEAST-PRIVILEGE (deliberate): the
    # unattended agent gets exactly the tools the voice sync needs; never bypassPermissions.
    script = (
        f'cd "{repo}" 2>/dev/null || cd "$HOME"\n'
        f'claude -p "update my voice" --model "{model}" --add-dir "{voice_dir}" '
        f"--allowedTools Read Edit Write Skill Glob Grep 'Bash(git:*)' 'Bash(python3:*)' "
        f"'Bash(voicectl:*)' >>\"{paths.log_path()}\" 2>&1\n"
        f'rm -f "{lock}" 2>/dev/null\n'
    )
    subprocess.Popen(
        ["bash", "-c", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
