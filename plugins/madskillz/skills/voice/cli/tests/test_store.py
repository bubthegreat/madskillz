import json
import shutil
import subprocess
from pathlib import Path

import pytest

from voicectl import paths, store
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
    assert store.github_slug("https://github.com/o/n.git/") == "o/n"
    assert store.github_slug("/tmp/origin.git") is None
    assert store.github_slug("https://example.com/notgithub.com/o/n") is None


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


def test_init_create_calls_create_remote(voice_env, tmp_path, monkeypatch, git_env):
    target = tmp_path / "new.git"
    def fake_create(url):
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", url], check=True)
    monkeypatch.setattr(store, "create_remote", fake_create)
    r = store.init(str(target), create=True)
    assert r["action"] == "adopted-empty" and r["created"] is True


def _push_store(bare_remote, dest):
    """Make bare_remote look like a real voice store: core.md on the store branch."""
    c = clone_of(bare_remote, dest)
    (c / "core.md").write_text(CORE)
    _git(c, "add", "-A"); _git(c, "commit", "-q", "-m", "store")
    _git(c, "push", "-q", "-u", "origin", "main")
    return c


def test_init_clones_store_into_missing_parent(tmp_path, monkeypatch, voice_env, bare_remote):
    """A fresh machine has no ~/.madskillz at all, so the clone has to make the parent dir."""
    _push_store(bare_remote, tmp_path / "c")
    fresh = tmp_path / "newmachine" / "voice"
    monkeypatch.setenv("VOICE_DIR", str(fresh))
    assert not fresh.parent.exists()

    r = store.init(str(bare_remote))
    assert r["action"] == "cloned" and r["mode"] == "synced"
    assert r["backup"] is None
    assert (fresh / "core.md").exists()


def test_init_restores_local_dir_when_clone_fails(voice_env, tmp_path, monkeypatch, git_env):
    """The adopt path renames the local dir aside before cloning. A failed clone must put
    it back, not leave the owner hunting for a .bak-<ts> dir."""
    monkeypatch.setattr(store, "remote_state", lambda url: "store")
    before = (voice_env / "core.md").read_text()

    with pytest.raises(store.StoreError) as e:
        store.init(str(tmp_path / "nope.git"))
    assert "restored" in str(e.value)

    assert voice_env.is_dir()
    assert (voice_env / "core.md").read_text() == before
    assert list(tmp_path.glob("voice" + store.paths.BACKUP_SUFFIX + "*")) == []


def test_init_already_wired_refuses_public_before_pushing(voice_env, bare_remote, monkeypatch):
    """Re-running init on a wired store must not push a corpus to a public remote."""
    assert store.init(str(bare_remote))["action"] == "adopted-empty"
    head = _git(voice_env, "rev-parse", "origin/main")
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "private line")

    monkeypatch.setattr(store, "github_slug", lambda url: "alice/voice")
    monkeypatch.setattr(store, "visibility", lambda url: "PUBLIC")
    with pytest.raises(store.InitRefused):
        store.init(str(bare_remote))

    assert _git(voice_env, "rev-parse", "origin/main") == head
    assert "private line" not in _git(voice_env, "show", "origin/main:corpus.jsonl")


def test_init_refuses_mismatched_origin(voice_env, bare_remote, tmp_path):
    _make_synced_store(voice_env, bare_remote)
    other = str(tmp_path / "other.git")
    with pytest.raises(store.StoreError) as e:
        store.init(other)
    msg = str(e.value)
    assert str(bare_remote) in msg and other in msg


def test_two_machines_converge(tmp_path, monkeypatch, voice_env, bare_remote):
    from voicectl import update
    a = voice_env
    _make_synced_store(a, bare_remote)
    b = tmp_path / "machine-b"
    monkeypatch.setenv("VOICE_DIR", str(b))
    assert store.init(str(bare_remote))["action"] == "cloned"

    # A captures + updates
    monkeypatch.setenv("VOICE_DIR", str(a))
    add_corpus(a, "2026-03-01T00:00:00Z", "from A")
    update.prep()
    cand = a / "cand.md"
    cand.write_text(CORE.replace("- **trait one**", "- **trait A**\n- **trait one**"))
    update.apply(cand)

    # B captures concurrently (has not pulled), then updates
    monkeypatch.setenv("VOICE_DIR", str(b))
    add_corpus(b, "2026-03-02T00:00:00Z", "from B")
    p = update.prep()          # pulls A's core + corpus (union)
    assert p["pull"] == "ok"
    assert [e["text"] for e in p["new_entries"]] == ["from B"]
    cand = b / "cand.md"
    cand.write_text((b / "core.md").read_text().replace("- **trait A**", "- **trait A**\n- **trait B**"))
    update.apply(cand)

    # A pulls and both agree
    monkeypatch.setenv("VOICE_DIR", str(a))
    assert store.pull() == 0
    assert (a / "core.md").read_text() == (b / "core.md").read_text()
    for d in (a, b):
        text = (d / "corpus.jsonl").read_text()
        assert "from A" in text and "from B" in text
    assert "trait A" in (a / "core.md").read_text() and "trait B" in (a / "core.md").read_text()


def test_templates_dir_falls_back_beside_the_store(tmp_path, monkeypatch, voice_env):
    """With no env override and no skill checkout, the templates live NEXT TO the store dir.
    Inside it they would look like user files to `init`, which renames those aside."""
    monkeypatch.delenv("VOICE_TEMPLATES_DIR", raising=False)
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "gone" / "cli" / "voicectl" / "paths.py"))
    assert paths.templates_dir() == voice_env.parent / "voice-templates"


def _templates_beside_store(tmp_path, voice_env, monkeypatch):
    """Put the fixture templates outside any voice dir and point the resolver at them."""
    templates = tmp_path / "voice-templates"
    templates.mkdir()
    for t in (voice_env.parent / "templates").glob("*.md"):
        shutil.copy(t, templates / t.name)
    monkeypatch.delenv("VOICE_TEMPLATES_DIR", raising=False)
    monkeypatch.setattr(paths, "templates_dir", lambda: templates)
    return templates


def test_init_clones_over_a_runtime_only_dir(tmp_path, monkeypatch, voice_env, bare_remote):
    """A voice dir holding only runtime files (`tool/`, `sync.log`) has no user data, so
    adopting a store must clone straight in: no backup, and the tool copy stays put."""
    _push_store(bare_remote, tmp_path / "c")
    _templates_beside_store(tmp_path, voice_env, monkeypatch)

    fresh = tmp_path / "machine" / "voice"
    (fresh / "tool" / "templates").mkdir(parents=True)
    (fresh / "sync.log").write_text("noise\n", encoding="utf-8")
    monkeypatch.setenv("VOICE_DIR", str(fresh))

    r = store.init(str(bare_remote))
    assert r["action"] == "cloned"
    assert r["backup"] is None
    assert list((tmp_path / "machine").glob("voice" + paths.BACKUP_SUFFIX + "*")) == []
    assert (fresh / "tool" / "templates").is_dir()
    assert (fresh / "sync.log").is_file()
    assert (fresh / "core.md").is_file()
    assert r["seeded"]


def test_migrate_to_repo_backs_up_and_drops_cruft(voice_env, bare_remote):
    """The one-shot migration copies the old dir aside BEFORE any git runs, drops the dead
    compat render and the retired sync clone, and never pushes either to the remote."""
    (voice_env / "voice.md").write_text("compat render", encoding="utf-8")
    (voice_env / "posts").mkdir()
    (voice_env / "posts" / "x.md").write_text("a post", encoding="utf-8")
    (voice_env / "madskillz-sync" / ".git").mkdir(parents=True)
    (voice_env / "tool").mkdir()
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "local line")

    r = store.migrate_to_repo(str(bare_remote))
    assert r["action"] == "adopted-empty"

    backup = Path(r["backup"])
    assert (backup / "core.md").is_file()
    assert (backup / "voice.md").is_file()
    assert (backup / "posts" / "x.md").is_file()
    assert not (backup / "tool").exists()
    assert not (backup / "madskillz-sync").exists()

    assert not (voice_env / "voice.md").exists()
    assert not (voice_env / "madskillz-sync").exists()
    assert (voice_env / "posts" / "x.md").is_file()   # kept on disk, gitignored
    assert (voice_env / "tool").is_dir()

    tracked = _git(voice_env, "ls-tree", "-r", "--name-only", "origin/main").split()
    assert "core.md" in tracked and "corpus.jsonl" in tracked
    assert "voice.md" not in tracked and "posts/x.md" not in tracked
    assert not [t for t in tracked if t.startswith("madskillz-sync")]
