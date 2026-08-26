import json
import subprocess
from pathlib import Path

import pytest

from voicectl import store
from tests.conftest import CORE, add_corpus, clone_of


def _git(d, *a):
    return subprocess.run(
        ["git", "-C", str(d), *a], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_mode_local_only_without_git(voice_env):
    assert store.mode() == "local-only"
    assert store.pull() == 0
    assert "local-only" in store.push()


def test_scaffold_writes_once(voice_env):
    assert sorted(store.scaffold(voice_env)) == [".gitattributes", ".gitignore", "README.md"]
    assert "corpus.jsonl merge=union" in (voice_env / ".gitattributes").read_text()
    assert "sync.log" in (voice_env / ".gitignore").read_text()
    assert store.scaffold(voice_env) == []


def test_seed_templates_fills_missing_and_rewrites_owner(voice_env):
    (voice_env / "blog.md").unlink()
    seeded = store.seed_templates(voice_env, owner="alice")
    assert seeded == ["blog.md", "chat.md"]
    text = (voice_env / "blog.md").read_text()
    assert "owner: alice" in text and "status: personal" in text
    # existing core untouched
    assert "owner: tester" in (voice_env / "core.md").read_text()


def test_seed_templates_replaces_every_handle(voice_env):
    tmpl = voice_env.parent / "templates" / "chat.md"
    tmpl.write_text(tmpl.read_text() + "\n# Voice of <handle>\n\nWritten by <handle>.\n", encoding="utf-8")
    (voice_env / "core.md").unlink()
    store.seed_templates(voice_env, owner="alice")
    text = (voice_env / "chat.md").read_text()
    assert "<handle>" not in text
    assert text.count("alice") == 3


def _make_synced_store(voice_env, bare_remote):
    """Turn voice_env into a clone of bare_remote with one initial commit pushed."""
    _git(voice_env, "init", "-q", "-b", "main")
    _git(voice_env, "remote", "add", "origin", str(bare_remote))
    store.scaffold(voice_env)
    store.commit_all("seed")
    _git(voice_env, "push", "-q", "-u", "origin", "main")
    return voice_env


def test_push_commits_and_pushes(voice_env, bare_remote):
    _make_synced_store(voice_env, bare_remote)
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "hello")
    out = store.push()
    assert "pushed" in out
    assert "voice: update" in _git(voice_env, "log", "--oneline", "origin/main")
    assert "nothing to push" in store.push()


def test_pull_fast_forwards(voice_env, bare_remote, tmp_path):
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    (other / "core.md").write_text(CORE.replace("trait two", "trait TWO"))
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "remote edit"); _git(other, "push", "-q")
    assert store.pull() == 0
    assert "trait TWO" in (voice_env / "core.md").read_text()


def test_corpus_union_merge_keeps_both_sides(voice_env, bare_remote, tmp_path):
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    with (other / "corpus.jsonl").open("a") as f:
        f.write(json.dumps({"ts": "2026-02-01T00:00:00Z", "text": "from other"}) + "\n")
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "other"); _git(other, "push", "-q")
    add_corpus(voice_env, "2026-02-02T00:00:00Z", "from me")
    out = store.push()  # rejected -> pull (union) -> retry
    assert "pushed" in out
    text = (voice_env / "corpus.jsonl").read_text()
    assert "from other" in text and "from me" in text


def test_pull_autostash_keeps_uncommitted_corpus(voice_env, bare_remote, tmp_path):
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    with (other / "corpus.jsonl").open("a") as f:
        f.write(json.dumps({"ts": "2026-02-01T00:00:00Z", "text": "from other"}) + "\n")
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "other"); _git(other, "push", "-q")
    add_corpus(voice_env, "2026-02-02T00:00:00Z", "uncommitted mine")
    assert store.pull() == 0
    text = (voice_env / "corpus.jsonl").read_text()
    assert "from other" in text and "uncommitted mine" in text
    # union-merged, not left as a conflict for someone to clean up
    assert "<<<<<<<" not in text
    # still a plain uncommitted working-tree change, ready for the next commit
    assert _git(voice_env, "status", "--porcelain") == "M corpus.jsonl"  # _git strips


def test_core_conflict_resolves_to_remote(voice_env, bare_remote, tmp_path, capsys):
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    (other / "core.md").write_text(CORE.replace("trait two", "REMOTE"))
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "remote"); _git(other, "push", "-q")
    (voice_env / "core.md").write_text(CORE.replace("trait two", "LOCAL"))
    store.commit_all("local")
    assert store.pull() == 2
    assert "REMOTE" in (voice_env / "core.md").read_text()
    assert "core.md" in capsys.readouterr().out
    # repo is clean, not mid-rebase
    assert not (voice_env / ".git" / "rebase-merge").exists()
    assert not (voice_env / ".git" / "rebase-apply").exists()
    assert _git(voice_env, "status", "--porcelain") == ""


def test_pull_conflict_loop_keeps_later_local_commit(voice_env, bare_remote, tmp_path, capsys):
    """Two local commits rebase onto a conflicting remote: the conflict resolves to the
    remote side, and the second local commit still lands."""
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    (other / "core.md").write_text(CORE.replace("trait two", "REMOTE"))
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "remote"); _git(other, "push", "-q")

    (voice_env / "core.md").write_text(CORE.replace("trait two", "LOCAL"))
    assert store.commit_all("local core") is True
    add_corpus(voice_env, "2026-02-03T00:00:00Z", "local corpus line")
    assert store.commit_all("local corpus") is True

    assert store.pull() == 2
    assert "REMOTE" in (voice_env / "core.md").read_text()
    assert "local corpus line" in (voice_env / "corpus.jsonl").read_text()
    assert "core.md" in capsys.readouterr().out
    assert not (voice_env / ".git" / "rebase-merge").exists()
    assert not (voice_env / ".git" / "rebase-apply").exists()
    assert _git(voice_env, "status", "--porcelain") == ""


def test_pull_offline_raises(voice_env, bare_remote):
    _make_synced_store(voice_env, bare_remote)
    _git(voice_env, "remote", "set-url", "origin", str(bare_remote.parent / "missing.git"))
    with pytest.raises(store.StoreError):
        store.pull()


def test_pull_resolves_autostash_pop_conflict_to_remote(voice_env, bare_remote, tmp_path, capsys):
    """An uncommitted profile edit that collides with an incoming remote change makes the
    autostash pop conflict. git pull still exits 0, so pull() has to notice and clean up."""
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    (other / "core.md").write_text(CORE.replace("trait two", "REMOTE"))
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "remote"); _git(other, "push", "-q")
    # local edit is never committed
    (voice_env / "core.md").write_text(CORE.replace("trait two", "LOCAL"))

    assert store.pull() == 2
    text = (voice_env / "core.md").read_text()
    assert "REMOTE" in text
    assert "<<<<<<<" not in text
    assert "core.md" in capsys.readouterr().out
    porcelain = _git(voice_env, "status", "--porcelain")
    assert not [ln for ln in porcelain.splitlines() if ln[:2] in ("UU", "AA")]
    assert _git(voice_env, "stash", "list") == ""


def test_pull_last_resort_aborts_and_keeps_local_work(voice_env, bare_remote, tmp_path, monkeypatch):
    """When the conflict loop runs out of steps, pull() aborts the rebase and raises.
    It must never throw local work away with a hard reset."""
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    (other / "core.md").write_text(CORE.replace("trait two", "REMOTE"))
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "remote"); _git(other, "push", "-q")
    (voice_env / "core.md").write_text(CORE.replace("trait two", "LOCAL"))
    assert store.commit_all("local core") is True

    monkeypatch.setattr(store, "MAX_CONFLICT_STEPS", 0)
    with pytest.raises(store.StoreError) as e:
        store.pull()
    assert "resolve manually" in str(e.value)

    assert not (voice_env / ".git" / "rebase-merge").exists()
    assert not (voice_env / ".git" / "rebase-apply").exists()
    assert _git(voice_env, "log", "-1", "--format=%s") == "local core"
    assert _git(voice_env, "status", "--porcelain") == ""


def test_push_without_tracking_ref_pushes(voice_env, bare_remote):
    """A store made by `git init` + `remote add` has no origin/<branch> ref yet, so the
    ahead-count fails. That must not read as "nothing to push"."""
    _git(voice_env, "init", "-q", "-b", "main")
    _git(voice_env, "remote", "add", "origin", str(bare_remote))
    store.scaffold(voice_env)
    assert store.commit_all("seed") is True

    out = store.push()
    assert "pushed" in out
    assert _git(voice_env, "rev-parse", "origin/main") == _git(voice_env, "rev-parse", "HEAD")


def test_github_slug():
    assert store.github_slug("git@github.com:alice/voice.git") == "alice/voice"
    assert store.github_slug("https://github.com/alice/voice") == "alice/voice"
    assert store.github_slug("ssh://git@github.com/alice/voice.git") == "alice/voice"
    assert store.github_slug("/tmp/origin.git") is None


def test_remote_state(bare_remote, tmp_path):
    assert store.remote_state(str(tmp_path / "nope.git")) == "missing"
    assert store.remote_state(str(bare_remote)) == "empty"
    c = clone_of(bare_remote, tmp_path / "c")
    (c / "junk.txt").write_text("x")
    _git(c, "add", "-A"); _git(c, "commit", "-q", "-m", "x"); _git(c, "push", "-q", "-u", "origin", "main")
    assert store.remote_state(str(bare_remote)) == "foreign"
    (c / "core.md").write_text(CORE)
    _git(c, "add", "-A"); _git(c, "commit", "-q", "-m", "core"); _git(c, "push", "-q")
    assert store.remote_state(str(bare_remote)) == "store"


def test_init_local_only(tmp_path, monkeypatch, voice_env):
    fresh = tmp_path / "fresh"
    monkeypatch.setenv("VOICE_DIR", str(fresh))
    r = store.init(None)
    assert r["action"] == "local" and r["mode"] == "local-only"
    assert (fresh / "core.md").exists() and not (fresh / ".git").exists()


def test_init_clone_empty_remote_seeds_and_pushes(tmp_path, monkeypatch, voice_env, bare_remote):
    fresh = tmp_path / "fresh"
    monkeypatch.setenv("VOICE_DIR", str(fresh))
    r = store.init(str(bare_remote))
    assert r["action"] == "cloned" and r["mode"] == "synced"
    assert "core.md" in r["seeded"]
    assert "core.md" in _git(fresh, "ls-tree", "--name-only", "origin/main")
    assert store.init(str(bare_remote))["action"] == "already"


def test_init_adopt_empty_remote_in_place(voice_env, bare_remote):
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "local line")
    r = store.init(str(bare_remote))
    assert r["action"] == "adopted-empty"
    assert "owner: tester" in (voice_env / "core.md").read_text()  # existing file kept
    assert "corpus.jsonl" in _git(voice_env, "ls-tree", "--name-only", "origin/main")


def test_init_adopt_existing_store_backs_up_and_merges_corpus(voice_env, bare_remote, tmp_path):
    c = clone_of(bare_remote, tmp_path / "c")
    (c / "core.md").write_text(CORE.replace("trait two", "REMOTE"))
    with (c / "corpus.jsonl").open("w") as f:
        f.write(json.dumps({"ts": "2026-01-01T00:00:00Z", "text": "remote line"}) + "\n")
    _git(c, "add", "-A"); _git(c, "commit", "-q", "-m", "store"); _git(c, "push", "-q", "-u", "origin", "main")
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "local line")
    (voice_env / "voice.md").write_text("compat")
    r = store.init(str(bare_remote))
    assert r["action"] == "adopted-store"
    assert r["backup"] and Path(r["backup"]).is_dir()
    text = (voice_env / "core.md").read_text()
    assert "REMOTE" in text  # remote profile wins
    corpus = (voice_env / "corpus.jsonl").read_text()
    assert "remote line" in corpus and "local line" in corpus
    assert not (voice_env / "voice.md").exists()
    assert "local line" in _git(voice_env, "show", "origin/main:corpus.jsonl")


def test_init_refuses_foreign_remote(voice_env, bare_remote, tmp_path):
    c = clone_of(bare_remote, tmp_path / "c")
    (c / "junk.txt").write_text("x")
    _git(c, "add", "-A"); _git(c, "commit", "-q", "-m", "x"); _git(c, "push", "-q", "-u", "origin", "main")
    with pytest.raises(store.InitRefused):
        store.init(str(bare_remote))


def test_init_missing_remote_needs_create(voice_env, tmp_path):
    with pytest.raises(store.InitRefused):
        store.init(str(tmp_path / "nope.git"))


def test_init_refuses_public(voice_env, bare_remote, monkeypatch):
    monkeypatch.setattr(store, "github_slug", lambda url: "alice/voice")
    monkeypatch.setattr(store, "visibility", lambda url: "PUBLIC")
    with pytest.raises(store.InitRefused):
        store.init(str(bare_remote))
    assert store.init(str(bare_remote), allow_public=True)["action"] == "adopted-empty"


def test_init_create_calls_create_remote(voice_env, tmp_path, monkeypatch):
    target = tmp_path / "new.git"
    def fake_create(url):
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", url], check=True)
    monkeypatch.setattr(store, "create_remote", fake_create)
    r = store.init(str(target), create=True)
    assert r["action"] == "adopted-empty" and r["created"] is True
