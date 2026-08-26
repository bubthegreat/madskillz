"""Sync = pull then push against the user's voice store. Also the status snapshot."""

from . import config, paths, store
from .corpus import count_since
from .profile import get_marker


def status_info() -> dict:
    core = paths.core_path()
    corpus = paths.corpus_path()
    d = paths.voice_dir()
    info: dict = {
        "voice_dir": str(d),
        "mode": store.mode(),
        "remote": store.remote_url(),
        "branch": paths.store_branch(),
        "ahead": 0,
        "behind": 0,
        "dirty": [],
        "core_exists": core.is_file(),
        "contexts": paths.live_contexts(),
        "lock_held": (d / ".sync.lock").is_file(),
        "config": config.all_values(),
    }
    if store.is_repo():
        info["dirty"] = sorted(
            l[3:] for l in store.git("status", "--porcelain").stdout.splitlines() if l
        )
        if info["mode"] == "synced":
            r = store.git(
                "rev-list", "--left-right", "--count",
                f"HEAD...origin/{info['branch']}", check=False,
            )
            if r.returncode == 0:
                a, b = r.stdout.split()
                info["ahead"], info["behind"] = int(a), int(b)
    if core.is_file():
        text = core.read_text(encoding="utf-8")
        info["processed_through"] = get_marker(text, "processed") or "none"
        info["repo_synced_through"] = get_marker(text, "repo") or "none"
        info["pending_since_processed"] = count_since(corpus, get_marker(text, "processed"))
    return info


def run(dry_run: bool = False) -> str:
    if store.mode() != "synced":
        return f"sync: {store.LOCAL_ONLY_HINT}"
    if dry_run:
        i = status_info()
        return (f"sync (dry-run): ahead {i['ahead']}, behind {i['behind']}, "
                f"dirty: {', '.join(i['dirty']) or 'none'}")
    code = store.pull()
    pushed = store.push()
    prefix = "sync: conflict resolved to remote; " if code == 2 else "sync: "
    return prefix + pushed
