"""SessionEnd gate: the cheap tier of the two-tier materiality check. Decides whether it
is worth spending an LLM, then detaches a headless updater agent; the updater's own
update-prep/update-apply do the pull/push. Contract unchanged: never blocks teardown,
never errors, no stdout."""

import os
import subprocess
import time
from datetime import datetime, timezone

from . import config, paths
from .corpus import count_since
from .profile import get_marker


def _log(msg: str) -> None:
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with paths.log_path().open("a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except OSError:
        pass


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

    min_count = config.get_int("minCount")
    min_interval = config.get_int("minInterval")
    lock_stale = int(os.environ.get("VOICE_SYNC_LOCK_STALE_SECONDS", "1800"))
    model = config.get("model")

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

    # Threshold on the marker `update-apply` advances. The legacy `Repo-synced through`
    # marker is never written any more, so counting from it would launch an updater on
    # every session for as long as the corpus is non-empty.
    marker = get_marker(core.read_text(encoding="utf-8"), "processed")
    count = count_since(corpus, marker)
    if count < min_count:
        return

    stamp.touch()
    lock.touch()
    _log(f"gate passed: {count} new msgs >= {min_count} - launching background sync (model={model})")

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
        f'cd "{voice_dir}" 2>/dev/null || cd "$HOME"\n'
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
