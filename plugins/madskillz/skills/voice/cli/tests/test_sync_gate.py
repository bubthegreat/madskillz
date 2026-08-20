import subprocess
import time

from voicectl import gate, paths, sync
from voicectl.profile import get_marker
from tests.conftest import CORE, add_corpus


def _make_sync_repo(tmp_path, monkeypatch, voice_env):
    """Bare origin + clone on main, seeded with the committed voices dir."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    clone = tmp_path / "sync-repo"
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(origin), str(seed)], check=True)
    committed = seed / paths.VOICES_SUBPATH
    committed.mkdir(parents=True)
    (committed / "core.md").write_text(CORE, encoding="utf-8")
    (committed / "blog.md").write_text((voice_env / "blog.md").read_text(), encoding="utf-8")
    env_git = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(seed), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(seed), "commit", "-q", "-m", "seed"], check=True, env={**__import__("os").environ, **env_git})
    subprocess.run(["git", "-C", str(seed), "push", "-q", "origin", "HEAD:main"], check=True)
    subprocess.run(["git", "clone", "-q", "-b", "main", str(origin), str(clone)], check=True)
    monkeypatch.setenv("VOICE_SYNC_REPO", str(clone))
    return clone


def test_assess_not_material_when_identical(voice_env, tmp_path, monkeypatch):
    clone = _make_sync_repo(tmp_path, monkeypatch, voice_env)
    verdict = sync.assess(voice_env, clone / paths.VOICES_SUBPATH)
    assert not verdict.material


def test_assess_material_on_new_section_and_bullets(voice_env, tmp_path, monkeypatch):
    clone = _make_sync_repo(tmp_path, monkeypatch, voice_env)
    core = voice_env / "core.md"
    text = core.read_text().replace(
        "## AI-tells", "## Decision heuristics\n- a.\n- b.\n- c.\n\n## AI-tells"
    )
    core.write_text(text)
    verdict = sync.assess(voice_env, clone / paths.VOICES_SUBPATH)
    assert verdict.material
    assert any("Decision heuristics" in s for s in verdict.new_sections)
    assert verdict.changed_bullets >= 3


def test_sync_pushes_and_stamps_markers(voice_env, tmp_path, monkeypatch):
    clone = _make_sync_repo(tmp_path, monkeypatch, voice_env)
    core = voice_env / "core.md"
    core.write_text(
        core.read_text()
        .replace("## AI-tells", "## New stuff\n- x.\n\n## AI-tells")
        .replace("Processed through: 2026-01-01T00:00:00Z", "Processed through: 2026-03-01T00:00:00Z")
    )
    out = sync.run()
    assert "pushed" in out
    live = core.read_text()
    assert get_marker(live, "repo") == "2026-03-01T00:00:00Z"
    committed = (clone / paths.VOICES_SUBPATH / "core.md").read_text()
    assert "## New stuff" in committed
    assert get_marker(committed, "repo") == "2026-03-01T00:00:00Z"
    # origin actually received it
    log = subprocess.run(
        ["git", "-C", str(clone), "log", "--oneline", "origin/main"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "voice: sync" in log


def test_sync_refuses_wrong_branch(voice_env, tmp_path, monkeypatch):
    clone = _make_sync_repo(tmp_path, monkeypatch, voice_env)
    (voice_env / "core.md").write_text(
        (voice_env / "core.md").read_text().replace("## AI-tells", "## New stuff\n- x.\n\n## AI-tells")
    )
    subprocess.run(["git", "-C", str(clone), "checkout", "-q", "-b", "other"], check=True)
    try:
        sync.run()
        raised = False
    except sync.SyncError as e:
        raised = "refusing" in str(e)
    assert raised


def test_gate_launches_only_past_thresholds(voice_env, monkeypatch):
    hit = voice_env / "launched"
    monkeypatch.setenv("VOICE_SYNC_LAUNCH", f"touch {hit}")
    monkeypatch.setenv("VOICE_SYNC_MIN_COUNT", "2")
    monkeypatch.setenv("VOICE_SYNC_MIN_INTERVAL_SECONDS", "0")

    gate.run()  # 0 new messages < 2
    assert not hit.exists()

    add_corpus(voice_env, "2026-01-02T00:00:00Z", "one")
    add_corpus(voice_env, "2026-01-03T00:00:00Z", "two")
    gate.run()
    assert hit.exists()
    assert not (voice_env / ".sync.lock").exists()  # released after sync launch


def test_gate_respects_interval_and_lock(voice_env, monkeypatch):
    hit = voice_env / "launched"
    monkeypatch.setenv("VOICE_SYNC_LAUNCH", f"touch {hit}")
    monkeypatch.setenv("VOICE_SYNC_MIN_COUNT", "1")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "one")

    (voice_env / ".last-sync-attempt").touch()
    monkeypatch.setenv("VOICE_SYNC_MIN_INTERVAL_SECONDS", "9999")
    gate.run()
    assert not hit.exists()  # throttled

    monkeypatch.setenv("VOICE_SYNC_MIN_INTERVAL_SECONDS", "0")
    lock = voice_env / ".sync.lock"
    lock.touch()
    gate.run()
    assert not hit.exists()  # live lock blocks

    old = time.time() - 99999
    __import__("os").utime(lock, (old, old))
    gate.run()
    assert hit.exists()  # stale lock cleared, launch proceeds


def test_gate_never_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("VOICE_DIR", str(tmp_path / "nonexistent"))
    gate.run()  # missing everything: silent no-op
