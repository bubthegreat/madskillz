import subprocess
import time

from voicectl import gate, store, sync
from tests.conftest import CORE, add_corpus, clone_of
from tests.test_store import _make_synced_store, _git


def test_sync_local_only(voice_env):
    assert "local-only" in sync.run()


def test_sync_pull_then_push(voice_env, bare_remote, tmp_path):
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    (other / "blog.md").write_text((voice_env / "blog.md").read_text() + "\n- remote bullet.\n")
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "r"); _git(other, "push", "-q")
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "mine")
    out = sync.run()
    assert "pushed" in out
    assert "remote bullet" in (voice_env / "blog.md").read_text()
    assert "mine" in _git(voice_env, "show", "origin/main:corpus.jsonl")


def test_status_info_synced(voice_env, bare_remote):
    _make_synced_store(voice_env, bare_remote)
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "mine")
    info = sync.status_info()
    assert info["mode"] == "synced" and info["dirty"] == ["corpus.jsonl"]
    assert info["pending_since_processed"] == 1
    assert info["config"]["model"] == "opus"


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
