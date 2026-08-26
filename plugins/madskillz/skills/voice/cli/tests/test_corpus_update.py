import json

import pytest

from voicectl import paths, update
from voicectl.corpus import append_capture, count_since, entries_since
from tests.conftest import CORE, add_corpus


def test_capture_appends_prompt(voice_env):
    corpus = voice_env / "corpus.jsonl"
    assert append_capture(corpus, json.dumps({"prompt": "hello world"}))
    line = json.loads(corpus.read_text().strip())
    assert line["text"] == "hello world" and "ts" in line


def test_capture_skips_empty_and_nonstring(voice_env):
    corpus = voice_env / "corpus.jsonl"
    assert not append_capture(corpus, json.dumps({"prompt": "   "}))
    assert not append_capture(corpus, json.dumps({"prompt": ["x"]}))
    assert corpus.read_text() == ""


def test_entries_since_marker(voice_env):
    add_corpus(voice_env, "2025-12-31T00:00:00Z", "old")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "new")
    corpus = voice_env / "corpus.jsonl"
    assert [e["text"] for e in entries_since(corpus, "2026-01-01T00:00:00Z")] == ["new"]
    assert count_since(corpus, "") == 2


def test_update_prep_and_apply(voice_env):
    add_corpus(voice_env, "2026-01-05T00:00:00Z", "fresh message")
    prep = update.prep()
    assert prep["new_entry_count"] == 1
    assert prep["new_entries"][0]["text"] == "fresh message"

    candidate = voice_env / "candidate.md"
    candidate.write_text(CORE.replace("- **trait one**", "- **trait zero**\n- **trait one**"))
    msg = update.apply(candidate)
    assert "2026-01-05T00:00:00Z" in msg
    core_text = paths.core_path().read_text()
    assert "trait zero" in core_text
    assert "Processed through: 2026-01-05T00:00:00Z" in core_text


def test_update_apply_rejects_invalid(voice_env):
    candidate = voice_env / "candidate.md"
    candidate.write_text("not a profile")
    before = paths.core_path().read_text()
    with pytest.raises(update.UpdateError):
        update.apply(candidate)
    assert paths.core_path().read_text() == before


def test_entries_dedupe_on_ts_and_text(voice_env):
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "dup")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "dup")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "not dup")
    corpus = voice_env / "corpus.jsonl"
    assert count_since(corpus, "") == 2


from tests.test_store import _make_synced_store, _git


def test_prep_pulls_remote_core_first(voice_env, bare_remote, tmp_path):
    from tests.conftest import clone_of
    _make_synced_store(voice_env, bare_remote)
    other = clone_of(bare_remote, tmp_path / "other")
    (other / "core.md").write_text(CORE.replace("Processed through: 2026-01-01T00:00:00Z",
                                                "Processed through: 2026-01-03T00:00:00Z"))
    _git(other, "add", "-A"); _git(other, "commit", "-q", "-m", "r"); _git(other, "push", "-q")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "older than remote marker")
    add_corpus(voice_env, "2026-01-04T00:00:00Z", "newer")
    p = update.prep()
    assert p["pull"] == "ok"
    assert p["processed_through"] == "2026-01-03T00:00:00Z"
    assert [e["text"] for e in p["new_entries"]] == ["newer"]


def test_prep_offline_falls_back_to_local(voice_env, bare_remote):
    _make_synced_store(voice_env, bare_remote)
    _git(voice_env, "remote", "set-url", "origin", str(bare_remote.parent / "gone.git"))
    p = update.prep()
    assert p["pull"] == "offline"
    assert p["processed_through"] == "2026-01-01T00:00:00Z"


def test_apply_pushes(voice_env, bare_remote):
    _make_synced_store(voice_env, bare_remote)
    add_corpus(voice_env, "2026-01-05T00:00:00Z", "fresh")
    candidate = voice_env / "candidate.md"
    candidate.write_text(CORE.replace("- **trait one**", "- **trait zero**\n- **trait one**"))
    msg = update.apply(candidate)
    assert "pushed" in msg
    assert "trait zero" in _git(voice_env, "show", "origin/main:core.md")
