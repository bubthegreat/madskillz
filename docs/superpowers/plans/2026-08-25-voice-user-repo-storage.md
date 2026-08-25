# Voice User-Owned Repo Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move a user's voice profiles + corpus out of the plugin repo into one private git repo the user owns, cloned to `~/.madskillz/voice/`, with pull/push so N machines converge.

**Architecture:** The live voice dir becomes a git clone (the "store"). A new `store.py` owns all git operations (init/adopt/clone/pull/push/visibility), `config.py` owns per-machine tunables in the clone's local git config, and `sync.py` shrinks to `pull` + `push`. `update-prep` pulls first, `update-apply` pushes after. The skill ships only templates; `init` seeds missing profiles from them.

**Tech Stack:** Python 3.11 stdlib (`subprocess`, `argparse`), pytest, bash installer, `git`, optional `gh`.

**Spec:** `docs/superpowers/specs/2026-08-25-voice-user-repo-storage-design.md`

## Global Constraints

- Python `>=3.11`, **stdlib only** (`cli/pyproject.toml`: `dependencies = []`).
- Hook contract for `capture`/`gate`: always exit 0, nothing on stdout, errors to `sync.log`.
- Corpus line format unchanged: `{"ts": "<UTC ISO Z>", "text": "..."}` JSONL, append-only.
- Render/merge rules and `references/voice-update.md` unchanged.
- Live dir default `~/.madskillz/voice`; env overrides `VOICE_DIR`, `CLAUDE_DIR` stay.
- Every git call goes through `store.git()`; no other module shells out to git.
- Commit messages: plain Conventional Commits, no caveman.
- Run tests from `plugins/madskillz/skills/voice/cli` with `uv run pytest -q`.
- All work on branch `feat/voice-system`.

---

## File map

| File | Responsibility |
|---|---|
| `cli/voicectl/corpus.py` (modify) | `entries()` dedupes on `(ts, text)`. |
| `cli/voicectl/config.py` (create) | `get/set` of `voice.*` keys in the store clone's local git config, env override. |
| `cli/voicectl/store.py` (create) | git plumbing: `git()`, `mode()`, `remote_url()`, `scaffold()`, `seed_templates()`, `pull()`, `push()`, `init()`, `github_slug()`, `visibility()`, `remote_state()`. |
| `cli/voicectl/paths.py` (modify) | drop `sync_repo/sync_branch/VOICES_SUBPATH`; add `templates_dir()`, `BACKUP_SUFFIX`; `NON_OVERLAY = {"core.md", "README.md"}`. |
| `cli/voicectl/sync.py` (rewrite) | `run()` = `pull` then `push`; no materiality. |
| `cli/voicectl/update.py` (modify) | `prep()` pulls first; `apply()` pushes after. |
| `cli/voicectl/gate.py` (modify) | tunables via `config`; no repo refresh; updater `cd`s to `VOICE_DIR`. |
| `cli/voicectl/cli.py` (modify) | commands `init` (flags), `pull`, `push`, `config`, `migrate-to-repo`, new `status` fields. |
| `cli/tests/conftest.py` (modify) | `git_env` fixture, `bare_remote` fixture, `make_store` helper. |
| `cli/tests/test_store.py` (create) | init/adopt/clone/pull/push/conflict/visibility/two-machine tests. |
| `cli/tests/test_config.py` (create) | config round-trip + env override. |
| `cli/tests/test_sync_gate.py` (modify) | replace materiality tests with pull+push tests; gate tests read config. |
| `cli/tests/test_corpus_update.py` (modify) | dedupe test; prep/apply pull/push tests. |
| `references/voices/*.md` (rewrite) | templates: `status: template`, `owner: <handle>`, no owner data. |
| `scripts/install_voice_pipeline.sh` (modify) | copy templates into `tool/templates`, call `voicectl init`, drop sync clone. |
| `scripts/install_voice_pipeline.test.sh` (modify) | local-only + remote paths. |
| `SKILL.md` (modify) | Init flow section; second-machine paragraph. |
| `CLAUDE.md` (repo root, modify) | delete the `voice-sync` clone exception. |
| `evals/evals.json` (modify) | line 13 wording. |

---

### Task 1: Corpus dedupe on `(ts, text)`

**Files:**
- Modify: `cli/voicectl/corpus.py:23-40` (`entries`)
- Test: `cli/tests/test_corpus_update.py`

**Interfaces:**
- Produces: `entries(corpus: Path) -> list[dict]` now returns unique `(ts, text)` pairs, first occurrence wins, order preserved.

- [ ] **Step 1: Write the failing test**

Append to `cli/tests/test_corpus_update.py`:

```python
def test_entries_dedupe_on_ts_and_text(voice_env):
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "dup")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "dup")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "not dup")
    corpus = voice_env / "corpus.jsonl"
    assert count_since(corpus, "") == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/madskillz/skills/voice/cli && uv run pytest tests/test_corpus_update.py::test_entries_dedupe_on_ts_and_text -q`
Expected: FAIL, `assert 3 == 2`.

- [ ] **Step 3: Implement**

In `cli/voicectl/corpus.py`, replace the body of `entries()`:

```python
def entries(corpus: Path) -> list[dict]:
    """Parsed corpus lines, deduped on (ts, text) - union merges across machines can
    duplicate a line both sides added. First occurrence wins; order preserved."""
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    try:
        lines = corpus.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not (isinstance(d.get("ts"), str) and isinstance(d.get("text"), str)):
            continue
        key = (d["ts"], d["text"])
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add cli/voicectl/corpus.py cli/tests/test_corpus_update.py
git commit -m "fix(voice): dedupe corpus entries on (ts, text)"
```

---

### Task 2: `config.py` - per-machine tunables in local git config

**Files:**
- Create: `cli/voicectl/config.py`
- Test: `cli/tests/test_config.py`
- Modify: `cli/tests/conftest.py` (add `git_env` fixture)

**Interfaces:**
- Produces:
  - `DEFAULTS: dict[str, str] = {"model": "opus", "minCount": "15", "minInterval": "720", "corpusSync": "true"}`
  - `ENV_ALIASES: dict[str, str] = {"model": "VOICE_SYNC_MODEL", "minCount": "VOICE_SYNC_MIN_COUNT", "minInterval": "VOICE_SYNC_MIN_INTERVAL_SECONDS"}`
  - `get(key: str) -> str` - env alias (if set) > `git config --local voice.<key>` (if store is a repo) > default. Unknown key → `KeyError`.
  - `set(key: str, value: str) -> None` - writes `git config --local voice.<key>`; raises `ConfigError` if the voice dir is not a git repo or key unknown.
  - `get_bool(key) -> bool`, `get_int(key) -> int`.
  - `class ConfigError(Exception)`.

- [ ] **Step 1: Add `git_env` fixture to conftest**

Append to `cli/tests/conftest.py`:

```python
@pytest.fixture
def git_env(monkeypatch):
    """Deterministic git identity so commits work in a sandbox."""
    for k, v in {
        "GIT_AUTHOR_NAME": "tester",
        "GIT_AUTHOR_EMAIL": "tester@example.com",
        "GIT_COMMITTER_NAME": "tester",
        "GIT_COMMITTER_EMAIL": "tester@example.com",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(k, v)
```

- [ ] **Step 2: Write the failing tests**

Create `cli/tests/test_config.py`:

```python
import subprocess

import pytest

from voicectl import config


def test_get_defaults_without_repo(voice_env):
    assert config.get("model") == "opus"
    assert config.get_int("minCount") == 15
    assert config.get_bool("corpusSync") is True


def test_set_requires_repo(voice_env):
    with pytest.raises(config.ConfigError):
        config.set("model", "sonnet")


def test_set_and_get_round_trip(voice_env, git_env):
    subprocess.run(["git", "init", "-q", "-b", "main", str(voice_env)], check=True)
    config.set("model", "sonnet")
    config.set("corpusSync", "false")
    assert config.get("model") == "sonnet"
    assert config.get_bool("corpusSync") is False


def test_env_alias_overrides(voice_env, git_env, monkeypatch):
    subprocess.run(["git", "init", "-q", "-b", "main", str(voice_env)], check=True)
    config.set("minCount", "3")
    monkeypatch.setenv("VOICE_SYNC_MIN_COUNT", "7")
    assert config.get_int("minCount") == 7


def test_unknown_key(voice_env):
    with pytest.raises(KeyError):
        config.get("nope")
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL, `ModuleNotFoundError: voicectl.config`.

- [ ] **Step 4: Implement**

Create `cli/voicectl/config.py`:

```python
"""Per-machine tunables, stored as `voice.<key>` in the store clone's LOCAL git config
(never committed). Env aliases win so tests and hooks can override without touching git."""

import os
import subprocess

from . import paths

DEFAULTS: dict[str, str] = {
    "model": "opus",
    "minCount": "15",
    "minInterval": "720",
    "corpusSync": "true",
}

ENV_ALIASES: dict[str, str] = {
    "model": "VOICE_SYNC_MODEL",
    "minCount": "VOICE_SYNC_MIN_COUNT",
    "minInterval": "VOICE_SYNC_MIN_INTERVAL_SECONDS",
}


class ConfigError(Exception):
    pass


def _is_repo() -> bool:
    return (paths.voice_dir() / ".git").exists()


def _git_config(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(paths.voice_dir()), "config", "--local", *args],
        capture_output=True, text=True,
    )


def get(key: str) -> str:
    if key not in DEFAULTS:
        raise KeyError(key)
    alias = ENV_ALIASES.get(key)
    if alias and os.environ.get(alias):
        return os.environ[alias]
    if _is_repo():
        r = _git_config("--get", f"voice.{key}")
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return DEFAULTS[key]


def set(key: str, value: str) -> None:  # noqa: A001 - CLI verb
    if key not in DEFAULTS:
        raise KeyError(key)
    if not _is_repo():
        raise ConfigError(
            f"{paths.voice_dir()} is not a git repo; run 'voicectl init' first"
        )
    r = _git_config(f"voice.{key}", value)
    if r.returncode != 0:
        raise ConfigError(r.stderr.strip())


def get_bool(key: str) -> bool:
    return get(key).strip().lower() in ("1", "true", "yes", "on")


def get_int(key: str) -> int:
    return int(get(key))


def all_values() -> dict[str, str]:
    return {k: get(k) for k in DEFAULTS}
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_config.py -q`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add cli/voicectl/config.py cli/tests/test_config.py cli/tests/conftest.py
git commit -m "feat(voice): per-machine tunables via voicectl config (local git config)"
```

---

### Task 3: `paths.py` cleanup + `templates_dir()`

**Files:**
- Modify: `cli/voicectl/paths.py`
- Modify: `cli/tests/conftest.py` (`voice_env` drops `VOICE_SYNC_REPO`, sets `VOICE_TEMPLATES_DIR`)

**Interfaces:**
- Produces:
  - `templates_dir() -> Path`: `VOICE_TEMPLATES_DIR` env → skill checkout `references/voices` (relative to this package: `Path(__file__).resolve().parents[2] / "references" / "voices"`) if it exists → `voice_dir() / "tool" / "templates"`.
  - `NON_OVERLAY = {"core.md", "README.md"}`.
  - `BACKUP_SUFFIX = ".bak-"`.
  - `store_branch() -> str` = env `VOICE_SYNC_BRANCH` or `"main"`.
- Removes: `sync_repo()`, `sync_branch()`, `VOICES_SUBPATH`.

Note: `sync.py`, `gate.py`, `cli.py`, `test_sync_gate.py` still reference the removed names after this task; the suite will fail until Tasks 5-8 land. That is expected - commit anyway, the branch is feature-only.

- [ ] **Step 1: Rewrite `paths.py`**

```python
"""Path resolution for the voice pipeline. Everything is env-overridable so tests can sandbox."""

import os
from pathlib import Path


def voice_dir() -> Path:
    return Path(os.environ.get("VOICE_DIR", Path.home() / ".madskillz" / "voice"))


def claude_dir() -> Path:
    return Path(os.environ.get("CLAUDE_DIR", Path.home() / ".claude"))


def corpus_path() -> Path:
    return voice_dir() / "corpus.jsonl"


def core_path() -> Path:
    return voice_dir() / "core.md"


def overlay_path(context: str) -> Path:
    return voice_dir() / f"{context}.md"


def log_path() -> Path:
    return voice_dir() / "sync.log"


def store_branch() -> str:
    return os.environ.get("VOICE_SYNC_BRANCH", "main")


def templates_dir() -> Path:
    """Skill-shipped profile templates. Env override > skill checkout > installed tool copy."""
    env = os.environ.get("VOICE_TEMPLATES_DIR")
    if env:
        return Path(env)
    checkout = Path(__file__).resolve().parents[2] / "references" / "voices"
    if checkout.is_dir():
        return checkout
    return voice_dir() / "tool" / "templates"


# Files in the live voice dir that are markdown but not context overlays.
NON_OVERLAY = {"core.md", "README.md"}

# Suffix for the backup dir `init --remote` makes when adopting a non-empty remote.
BACKUP_SUFFIX = ".bak-"


def live_contexts() -> list[str]:
    """Context names with a live overlay present."""
    d = voice_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md") if p.name not in NON_OVERLAY)
```

- [ ] **Step 2: Update `voice_env` in conftest**

Replace the two `monkeypatch.setenv` lines in `voice_env` with:

```python
    monkeypatch.setenv("VOICE_DIR", str(vdir))
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "core.md").write_text(
        CORE.replace("owner: tester", "owner: <handle>").replace("status: personal", "status: template"),
        encoding="utf-8",
    )
    (templates / "blog.md").write_text(
        OVERLAY.replace("owner: tester", "owner: <handle>").replace("status: personal", "status: template"),
        encoding="utf-8",
    )
    (templates / "chat.md").write_text(
        OVERLAY.replace("voice: blog", "voice: chat").replace("owner: tester", "owner: <handle>").replace("status: personal", "status: template"),
        encoding="utf-8",
    )
    monkeypatch.setenv("VOICE_TEMPLATES_DIR", str(templates))
```

- [ ] **Step 3: Verify the unaffected tests still pass**

Run: `uv run pytest tests/test_profile_merge.py tests/test_corpus_update.py tests/test_config.py -q`
Expected: pass (test_sync_gate import errors are expected until Task 5).

- [ ] **Step 4: Commit**

```bash
git add cli/voicectl/paths.py cli/tests/conftest.py
git commit -m "refactor(voice): paths - drop sync-clone paths, add templates_dir"
```

---

### Task 4: `store.py` - git plumbing, scaffold, seed, pull, push

**Files:**
- Create: `cli/voicectl/store.py`
- Create: `cli/tests/test_store.py`
- Modify: `cli/tests/conftest.py` (`bare_remote` fixture, `clone_of` helper)

**Interfaces:**
- Produces:
  - `class StoreError(Exception)`
  - `git(*args, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess` - runs `git -C <cwd or voice_dir()> ...`; raises `StoreError(stderr)` when `check` and nonzero.
  - `is_repo(d: Path | None = None) -> bool`
  - `remote_url(d: Path | None = None) -> str | None`
  - `mode() -> str` - `"synced"` if repo with origin, else `"local-only"`.
  - `scaffold(d: Path) -> list[str]` - writes `.gitattributes`, `.gitignore`, `README.md` if missing; returns names written.
  - `seed_templates(d: Path, owner: str) -> list[str]` - copies each `templates_dir()/*.md` missing in `d`, rewriting `owner: <handle>` → `owner: {owner}` and `status: template` → `status: personal`; returns names seeded.
  - `owner_name() -> str` - `git config user.name` or `$USER` or `"owner"`.
  - `commit_all(message: str) -> bool` - `git add -A`; commit if dirty; returns True if a commit was made.
  - `pull() -> int` - `0` clean, `2` conflict resolved to remote (prints files), raises `StoreError` on fetch failure. No-op returning 0 in local-only mode.
  - `push() -> str` - commit_all + push; on reject: `pull()` then retry once. Returns summary line. Local-only mode returns the hint string without error.
  - `hostname() -> str`.

- [ ] **Step 1: Add fixtures to conftest**

Append to `cli/tests/conftest.py`:

```python
import subprocess
from pathlib import Path


@pytest.fixture
def bare_remote(tmp_path, git_env):
    """Empty bare repo on branch main."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    return origin


def clone_of(origin: Path, dest: Path) -> Path:
    subprocess.run(["git", "clone", "-q", str(origin), str(dest)], check=True)
    return dest
```

(`import pytest` already exists at top; keep one import block.)

- [ ] **Step 2: Write failing tests**

Create `cli/tests/test_store.py`:

```python
import json
import subprocess
from pathlib import Path

import pytest

from voicectl import paths, store
from tests.conftest import CORE, add_corpus, clone_of


def _git(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, check=True).stdout.strip()


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
    assert _git(voice_env, "status", "--porcelain") == ""


def test_pull_offline_raises(voice_env, bare_remote):
    _make_synced_store(voice_env, bare_remote)
    _git(voice_env, "remote", "set-url", "origin", str(bare_remote.parent / "missing.git"))
    with pytest.raises(store.StoreError):
        store.pull()
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_store.py -q`
Expected: FAIL, `ModuleNotFoundError: voicectl.store`.

- [ ] **Step 4: Implement `store.py` (part 1: plumbing, scaffold, seed, pull, push)**

Create `cli/voicectl/store.py`:

```python
"""The voice store: the live voice dir as a git clone of a repo the user owns.
All git access for the pipeline lives here."""

import os
import re
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


class StoreError(Exception):
    pass


def git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(
        ["git", "-C", str(cwd or paths.voice_dir()), *args],
        capture_output=True, text=True,
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
    return "synced" if remote_url() else "local-only"


def hostname() -> str:
    return socket.gethostname().split(".")[0]


def owner_name() -> str:
    r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
    return r.stdout.strip() or os.environ.get("USER") or "owner"


def scaffold(d: Path) -> list[str]:
    written = []
    for name, body in ((".gitattributes", GITATTRIBUTES), (".gitignore", GITIGNORE), ("README.md", README)):
        p = d / name
        if not p.exists():
            p.write_text(body, encoding="utf-8")
            written.append(name)
    return written


def seed_templates(d: Path, owner: str) -> list[str]:
    src = paths.templates_dir()
    if not src.is_dir():
        raise StoreError(f"templates dir not found: {src}")
    seeded = []
    for t in sorted(src.glob("*.md")):
        dst = d / t.name
        if dst.exists():
            continue
        text = t.read_text(encoding="utf-8")
        text = text.replace("owner: <handle>", f"owner: {owner}", 1)
        text = text.replace("status: template", "status: personal", 1)
        dst.write_text(text, encoding="utf-8")
        seeded.append(t.name)
    return seeded


def _dirty() -> bool:
    return bool(git("status", "--porcelain").stdout.strip())


def commit_all(message: str) -> bool:
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        return False
    git("commit", "-q", "-m", message)
    return True


def _conflicted_files() -> list[str]:
    return [l for l in git("diff", "--name-only", "--diff-filter=U", check=False).stdout.split() if l]


def pull() -> int:
    """Rebase local commits onto origin. 0 = clean; 2 = a profile conflicted and the remote
    version was kept (files printed). Raises StoreError when the fetch itself fails."""
    if mode() != "synced":
        return 0
    branch = paths.store_branch()
    git("fetch", "-q", "origin", branch)
    r = git("pull", "-q", "--rebase", "--autostash", "origin", branch, check=False)
    if r.returncode == 0:
        return 0
    conflicted = _conflicted_files()
    if not conflicted:
        git("rebase", "--abort", check=False)
        raise StoreError(f"pull failed: {r.stderr.strip()}")
    # Remote wins for every conflicted profile. During a rebase "ours" is the upstream side.
    for f in conflicted:
        git("checkout", "--ours", "--", f)
        git("add", "--", f)
    git("-c", "core.editor=true", "rebase", "--continue", check=False)
    if (paths.voice_dir() / ".git" / "rebase-merge").exists():
        git("rebase", "--abort", check=False)
        git("reset", "-q", "--hard", f"origin/{branch}")
    print(f"pull: conflict on {', '.join(conflicted)} - kept remote version; re-run your update")
    return 2


def push() -> str:
    if mode() != "synced":
        return f"push: {LOCAL_ONLY_HINT}"
    branch = paths.store_branch()
    made = commit_all(f"voice: update ({hostname()})")
    ahead = git("rev-list", "--count", f"origin/{branch}..HEAD", check=False).stdout.strip()
    if not made and ahead in ("", "0"):
        return "push: nothing to push"
    r = git("push", "-q", "origin", branch, check=False)
    if r.returncode != 0:
        pull()
        git("push", "-q", "origin", branch)
    return f"push: pushed to origin/{branch}"
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_store.py -q`
Expected: 9 passed. If `test_core_conflict_resolves_to_remote` fails because `--ours` chose the wrong side, check `git status` output in the test dir: during `pull --rebase`, upstream = "ours". Do not flip it without reproducing.

- [ ] **Step 6: Commit**

```bash
git add cli/voicectl/store.py cli/tests/test_store.py cli/tests/conftest.py
git commit -m "feat(voice): store module - scaffold, seed, pull, push over the user's voice repo"
```

---

### Task 5: `store.init()` - pick, wire, or create the repo

**Files:**
- Modify: `cli/voicectl/store.py` (append)
- Modify: `cli/tests/test_store.py` (append)

**Interfaces:**
- Produces:
  - `github_slug(url: str) -> str | None` - `"owner/name"` for `git@github.com:o/n.git`, `https://github.com/o/n(.git)`, `ssh://git@github.com/o/n.git`; else None.
  - `remote_state(url: str) -> str` - `"missing"` (ls-remote fails), `"empty"` (no refs), `"store"` (has `core.md` at root of `store_branch()`), `"foreign"` (non-empty, no core.md).
  - `visibility(url: str) -> str` - `"PUBLIC"|"PRIVATE"|"INTERNAL"|"UNKNOWN"`; uses `gh repo view <slug> --json visibility -q .visibility` when slug and `gh` exist, else `"UNKNOWN"`.
  - `create_remote(url: str) -> None` - `gh repo create <slug> --private`; `StoreError` if not github or `gh` missing.
  - `init(remote: str | None, create: bool = False, allow_public: bool = False) -> dict` with keys `mode`, `action` (`"local"|"cloned"|"adopted-empty"|"adopted-store"|"already"|"created"`), `seeded: list[str]`, `backup: str | None`, `visibility: str`.
  - `InitRefused(StoreError)` for public / foreign / missing-without-create.

Behavior matrix for `init(remote=URL)` with `d = voice_dir()`:

| `d` state | remote state | action |
|---|---|---|
| repo with origin == URL | any | `already`: pull, seed missing, scaffold, commit+push if dirty |
| repo with other origin | any | `StoreError("origin is X, not URL; remove .git or pass matching remote")` |
| missing/empty dir | `store`/`empty` | clone → (`empty`: scaffold+seed+commit+push) → `cloned` |
| dir, no `.git` | `empty` | `git init -b main`, remote add, scaffold, seed, commit, push → `adopted-empty` |
| dir, no `.git` | `store` | rename `d` → `d.bak-<ts>`, clone, append local `corpus.jsonl` lines from backup, seed missing, commit+push → `adopted-store`; local profiles are NOT copied (remote wins) |
| any | `foreign` | `InitRefused` |
| any | `missing` | `create` → `create_remote` then re-run with `empty`; else `InitRefused("remote missing; pass --create")` |

Visibility: when slug resolves and `visibility()` is `PUBLIC` and not `allow_public` → `InitRefused` **before** any push. `UNKNOWN` → proceed, `result["visibility"]="UNKNOWN"`.

`init(remote=None)`: `d.mkdir`, seed, scaffold → `action="local"`. Never touches git.

`ts` for the backup name: `datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")`.

- [ ] **Step 1: Write failing tests**

Append to `cli/tests/test_store.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_store.py -q -k "init or slug or remote_state"`
Expected: FAIL with `AttributeError` on missing functions.

- [ ] **Step 3: Implement**

Append to `cli/voicectl/store.py`:

```python
import shutil
from datetime import datetime, timezone

_GH_RE = re.compile(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


class InitRefused(StoreError):
    pass


def github_slug(url: str) -> str | None:
    m = _GH_RE.search(url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def remote_state(url: str) -> str:
    r = subprocess.run(["git", "ls-remote", "--heads", url], capture_output=True, text=True)
    if r.returncode != 0:
        return "missing"
    if not r.stdout.strip():
        return "empty"
    probe = subprocess.run(
        ["git", "archive", f"--remote={url}", paths.store_branch(), "core.md"],
        capture_output=True,
    )
    if probe.returncode == 0:
        return "store"
    # `git archive --remote` is unsupported on some hosts (GitHub); fall back to a shallow clone.
    with __import__("tempfile").TemporaryDirectory() as td:
        c = subprocess.run(
            ["git", "clone", "-q", "--depth=1", "--branch", paths.store_branch(), url, td],
            capture_output=True, text=True,
        )
        if c.returncode == 0 and (Path(td) / "core.md").exists():
            return "store"
    return "foreign"


def visibility(url: str) -> str:
    slug = github_slug(url)
    if not slug or not shutil.which("gh"):
        return "UNKNOWN"
    r = subprocess.run(
        ["gh", "repo", "view", slug, "--json", "visibility", "-q", ".visibility"],
        capture_output=True, text=True,
    )
    return r.stdout.strip().upper() if r.returncode == 0 and r.stdout.strip() else "UNKNOWN"


def create_remote(url: str) -> None:
    slug = github_slug(url)
    if not slug:
        raise StoreError("--create only supports github.com remotes; create the repo, then re-run")
    if not shutil.which("gh"):
        raise StoreError("--create needs the gh CLI (https://cli.github.com) logged in")
    r = subprocess.run(["gh", "repo", "create", slug, "--private"], capture_output=True, text=True)
    if r.returncode != 0:
        raise StoreError(f"gh repo create {slug}: {r.stderr.strip()}")


def _first_commit_and_push(d: Path, owner: str) -> list[str]:
    scaffold(d)
    seeded = seed_templates(d, owner)
    commit_all("voice: initialize store")
    git("push", "-q", "-u", "origin", paths.store_branch(), cwd=d)
    return seeded


def _append_corpus(src: Path, dst: Path) -> None:
    if not src.is_file():
        return
    with dst.open("a", encoding="utf-8") as out:
        out.write(src.read_text(encoding="utf-8").rstrip("\n") + "\n" if src.stat().st_size else "")


def init(remote: str | None, create: bool = False, allow_public: bool = False) -> dict:
    d = paths.voice_dir()
    owner = owner_name()
    result: dict = {"mode": "local-only", "action": "local", "seeded": [], "backup": None,
                    "visibility": "UNKNOWN", "created": False}

    if remote is None:
        d.mkdir(parents=True, exist_ok=True)
        scaffold(d)
        result["seeded"] = seed_templates(d, owner)
        return result

    if is_repo(d):
        current = remote_url(d)
        if current != remote:
            raise StoreError(f"{d} already has origin '{current}', not '{remote}'; remove .git or pass the matching remote")
        pull()
        scaffold(d)
        result["seeded"] = seed_templates(d, owner)
        push()
        result.update(mode="synced", action="already")
        return result

    state = remote_state(remote)
    if state == "missing":
        if not create:
            raise InitRefused(f"remote not found: {remote} (pass --create to make a private repo)")
        create_remote(remote)
        result["created"] = True
        state = "empty"
    if state == "foreign":
        raise InitRefused(f"{remote} is non-empty and is not a voice store (no core.md at root); pick another repo")

    vis = visibility(remote)
    result["visibility"] = vis
    if vis == "PUBLIC" and not allow_public:
        raise InitRefused(f"{remote} is PUBLIC; the corpus holds verbatim prompts. Make it private or pass --allow-public")

    branch = paths.store_branch()
    existing_files = d.is_dir() and any(d.iterdir())

    if state == "store":
        backup = None
        if existing_files:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = d.with_name(d.name + paths.BACKUP_SUFFIX + ts)
            d.rename(backup)
        git("clone", "-q", "--branch", branch, remote, str(d), cwd=Path.cwd())
        if backup:
            _append_corpus(backup / "corpus.jsonl", d / "corpus.jsonl")
            result["backup"] = str(backup)
        scaffold(d)
        result["seeded"] = seed_templates(d, owner)
        commit_all(f"voice: adopt machine {hostname()}")
        git("push", "-q", "origin", branch)
        result.update(mode="synced", action="adopted-store" if backup else "cloned")
        return result

    # state == "empty"
    d.mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", branch)
    git("remote", "add", "origin", remote)
    result["seeded"] = _first_commit_and_push(d, owner)
    result.update(mode="synced", action="adopted-empty" if existing_files else "cloned")
    return result
```

Move the `import shutil` / `datetime` lines to the top import block when done.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_store.py -q`
Expected: all pass. `test_init_adopt_existing_store_backs_up_and_merges_corpus` asserts `voice.md` is absent: the backup rename moves it away and it is gitignored, so the clone never has it.

- [ ] **Step 5: Commit**

```bash
git add cli/voicectl/store.py cli/tests/test_store.py
git commit -m "feat(voice): store.init - wire an existing repo, adopt local files, or create one"
```

---

### Task 6: `sync.py` rewrite + `status`

**Files:**
- Rewrite: `cli/voicectl/sync.py`
- Modify: `cli/voicectl/cli.py:82-104` (`cmd_status`), `cmd_sync`
- Rewrite: `cli/tests/test_sync_gate.py` (sync half; gate half in Task 8)

**Interfaces:**
- Produces: `sync.run(dry_run: bool = False) -> str`. `dry_run` prints mode, ahead/behind, dirty files and returns without git writes. Otherwise `store.pull()` then `store.push()`; returns combined one-line summary. `SyncError` removed; `store.StoreError` propagates.
- `status_info() -> dict` moves into `sync.py`: keys `voice_dir, mode, remote, branch, ahead, behind, dirty, core_exists, contexts, lock_held, processed_through, repo_synced_through, pending_since_processed, corpus_sync, config`.

- [ ] **Step 1: Write failing tests**

Replace the sync tests in `cli/tests/test_sync_gate.py` (delete `_make_sync_repo`, `test_assess_*`, `test_sync_pushes_and_stamps_markers`, `test_sync_refuses_wrong_branch`) with:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_sync_gate.py -q -k "sync or status"`
Expected: FAIL (`assess` import errors / attribute errors).

- [ ] **Step 3: Rewrite `sync.py`**

```python
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
        "corpus_sync": config.get_bool("corpusSync"),
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
```

- [ ] **Step 4: Update `cli.py` `cmd_status` and `cmd_sync`**

```python
def cmd_status(args) -> int:
    info = sync.status_info()
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        for k, v in info.items():
            print(f"{k}: {v}")
    return 0


def cmd_sync(args) -> int:
    try:
        print(sync.run(dry_run=args.dry_run))
        return 0
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
```

Add `store` to the `from . import ...` line; remove the `--no-push` argument from the `sync` parser.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_sync_gate.py -q -k "sync or status"`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add cli/voicectl/sync.py cli/voicectl/cli.py cli/tests/test_sync_gate.py
git commit -m "refactor(voice): sync is pull+push on the voice store; status reports repo state"
```

---

### Task 7: `update-prep` pulls, `update-apply` pushes

**Files:**
- Modify: `cli/voicectl/update.py`
- Modify: `cli/tests/test_corpus_update.py`

**Interfaces:**
- `prep() -> dict` gains keys `pull: "ok"|"conflict-remote-kept"|"offline"|"local-only"` and `mode`.
- `apply(candidate_file, processed_through=None) -> str` returns its existing line plus `"; " + push summary` (or `"; push failed: <err>"`, still exit 0 from the CLI because the local apply stands).

- [ ] **Step 1: Write failing tests**

Append to `cli/tests/test_corpus_update.py`:

```python
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
    candidate.unlink()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_corpus_update.py -q -k "prep_pulls or offline or apply_pushes"`
Expected: FAIL (`KeyError: 'pull'`, no "pushed").

- [ ] **Step 3: Implement**

In `cli/voicectl/update.py`, add `from . import store` and change `prep()`/`apply()`:

```python
def _pull_status() -> str:
    if store.mode() != "synced":
        return "local-only"
    try:
        return "conflict-remote-kept" if store.pull() == 2 else "ok"
    except store.StoreError:
        return "offline"


def prep() -> dict:
    pull = _pull_status()
    core = paths.core_path()
    if not core.is_file():
        raise UpdateError(f"live core profile missing: {core} (run 'voicectl init')")
    text = core.read_text(encoding="utf-8")
    marker = get_marker(text, "processed")
    new = entries_since(paths.corpus_path(), marker)
    return {
        "core_path": str(core),
        "mode": store.mode(),
        "pull": pull,
        "processed_through": marker or "none",
        "new_entry_count": len(new),
        "newest_ts": new[-1]["ts"] if new else marker,
        "new_entries": new,
    }
```

At the end of `apply()`, replace the `return` with:

```python
    msg = f"update-apply: installed {core} (Processed through: {processed_through or 'unchanged'})"
    try:
        return msg + "; " + store.push()
    except store.StoreError as e:
        return msg + f"; push failed: {e} (local apply stands; run 'voicectl sync' later)"
```

Also delete the `candidate.md` artifact risk: `push()` runs `git add -A`, so `apply()` must remove the candidate if it lives inside the voice dir. Add before the push:

```python
    try:
        if candidate_file.resolve().is_relative_to(core.parent.resolve()):
            candidate_file.unlink(missing_ok=True)
    except (OSError, ValueError):
        pass
```

and remove the `candidate.unlink()` line from `test_apply_pushes` (the function now does it). Add `*.tmp` is already gitignored; candidate files use whatever name the agent chose, hence the unlink.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_corpus_update.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add cli/voicectl/update.py cli/tests/test_corpus_update.py
git commit -m "feat(voice): update-prep pulls the store first; update-apply pushes after"
```

---

### Task 8: `gate.py` - config tunables, no repo refresh

**Files:**
- Modify: `cli/voicectl/gate.py`
- Modify: `cli/tests/test_sync_gate.py` (gate tests)

**Interfaces:**
- `gate.run()` unchanged signature. Reads `minCount`, `minInterval`, `model` via `config`; `VOICE_SYNC_LOCK_STALE_SECONDS` and `VOICE_SYNC_LAUNCH` stay env-only. `_refresh_sync_repo` deleted. Updater script `cd`s into `voice_dir()`.

- [ ] **Step 1: Add a config-driven gate test**

Append to `cli/tests/test_sync_gate.py`:

```python
def test_gate_reads_config_from_store(voice_env, bare_remote, monkeypatch):
    from voicectl import config
    _make_synced_store(voice_env, bare_remote)
    hit = voice_env / "launched"
    monkeypatch.setenv("VOICE_SYNC_LAUNCH", f"touch {hit}")
    monkeypatch.delenv("VOICE_SYNC_MIN_COUNT", raising=False)
    config.set("minCount", "1")
    config.set("minInterval", "0")
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "one")
    gate.run()
    assert hit.exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_sync_gate.py::test_gate_reads_config_from_store -q`
Expected: FAIL (default minCount 15 not reached).

- [ ] **Step 3: Implement**

In `gate.py`: delete `_refresh_sync_repo`; replace the tunable block and the launch script:

```python
from . import config, paths
...
    min_count = config.get_int("minCount")
    min_interval = config.get_int("minInterval")
    lock_stale = int(os.environ.get("VOICE_SYNC_LOCK_STALE_SECONDS", "1800"))
    model = config.get("model")
```

Remove the `repo = paths.sync_repo()` / `branch = ...` lines and the `VOICE_SYNC_AUTOREFRESH` block. Change the detached script's first line to:

```python
        f'cd "{voice_dir}" 2>/dev/null || cd "$HOME"\n'
```

Update the module docstring: drop "Port of voice-sync-gate.sh" and describe: cheap tier; detaches the updater; the updater's own `update-prep`/`update-apply` do the pull/push.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add cli/voicectl/gate.py cli/tests/test_sync_gate.py
git commit -m "refactor(voice): gate reads tunables from voicectl config; no sync-clone refresh"
```

---

### Task 9: CLI wiring - `init` flags, `pull`, `push`, `config`, `migrate-to-repo`

**Files:**
- Modify: `cli/voicectl/cli.py`
- Create: `cli/tests/test_cli.py`

**Interfaces:**
- `voicectl init [--remote URL] [--create] [--allow-public]` → prints one line per result field; exit 1 on `StoreError`, exit 3 on `InitRefused`.
- `voicectl pull` → exit code = `store.pull()` return (0/2), 1 on error.
- `voicectl push` → prints summary; exit 1 on error.
- `voicectl config` (list all), `voicectl config KEY` (get), `voicectl config KEY VALUE` (set).
- `voicectl migrate-to-repo --remote URL [--create] [--allow-public]` → same as `init` but `--remote` required; prints backup path.
- `voicectl sync [--dry-run]`.
- Old `init --source` removed.

- [ ] **Step 1: Write failing tests**

Create `cli/tests/test_cli.py`:

```python
import json

from voicectl.cli import main
from tests.test_store import _make_synced_store


def test_init_local_only_cli(voice_env, capsys):
    assert main(["init"]) == 0
    assert "local-only" in capsys.readouterr().out


def test_init_with_remote_and_config(voice_env, bare_remote, capsys):
    assert main(["init", "--remote", str(bare_remote)]) == 0
    out = capsys.readouterr().out
    assert "action: adopted-empty" in out
    assert main(["config", "model", "sonnet"]) == 0
    assert main(["config", "model"]) == 0
    assert capsys.readouterr().out.strip() == "sonnet"
    assert main(["config"]) == 0
    assert "minCount" in capsys.readouterr().out


def test_init_missing_remote_exit_3(voice_env, tmp_path, capsys):
    assert main(["init", "--remote", str(tmp_path / "nope.git")]) == 3
    assert "--create" in capsys.readouterr().err


def test_pull_push_status_json(voice_env, bare_remote, capsys):
    _make_synced_store(voice_env, bare_remote)
    assert main(["pull"]) == 0
    assert main(["push"]) == 0
    assert main(["status", "--json"]) == 0
    info = json.loads(capsys.readouterr().out.split("push:")[-1].split("\n", 1)[1])
    assert info["mode"] == "synced"


def test_migrate_requires_remote(voice_env):
    import pytest
    with pytest.raises(SystemExit):
        main(["migrate-to-repo"])
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cli.py -q`
Expected: FAIL (unknown arguments / missing subcommands).

- [ ] **Step 3: Implement**

In `cli/voicectl/cli.py`, replace `cmd_init` and add commands:

```python
def _run_init(args) -> int:
    try:
        r = store.init(args.remote, create=args.create, allow_public=args.allow_public)
    except store.InitRefused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 3
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"mode: {r['mode']}")
    print(f"action: {r['action']}")
    print(f"seeded: {', '.join(r['seeded']) or 'nothing'}")
    if r["backup"]:
        print(f"backup: {r['backup']}")
    if r["mode"] == "synced":
        print(f"visibility: {r['visibility']}")
    else:
        print(f"hint: {store.LOCAL_ONLY_HINT}")
    return 0


def cmd_init(args) -> int:
    return _run_init(args)


def cmd_migrate(args) -> int:
    return _run_init(args)


def cmd_pull(_args) -> int:
    try:
        code = store.pull()
        print("pull: ok" if code == 0 else "pull: conflict resolved to remote")
        return code
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def cmd_push(_args) -> int:
    try:
        print(store.push())
        return 0
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def cmd_config(args) -> int:
    try:
        if args.key and args.value is not None:
            config.set(args.key, args.value)
            print(f"{args.key} = {args.value}")
        elif args.key:
            print(config.get(args.key))
        else:
            for k, v in config.all_values().items():
                print(f"{k} = {v}")
        return 0
    except KeyError as e:
        print(f"error: unknown key {e}; known: {', '.join(config.DEFAULTS)}", file=sys.stderr)
        return 1
    except config.ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
```

Parser wiring inside `main()` (replace the old `init` block, add the rest):

```python
    def _init_flags(parser, remote_required: bool):
        parser.add_argument("--remote", required=remote_required, help="git URL of your private voice repo")
        parser.add_argument("--create", action="store_true", help="create the repo (github.com + gh) if missing")
        parser.add_argument("--allow-public", action="store_true")

    i = sub.add_parser("init", help="wire this machine to your voice repo (or local-only without --remote)")
    _init_flags(i, remote_required=False)
    i.set_defaults(fn=cmd_init)

    m = sub.add_parser("migrate-to-repo", help="move an existing local voice dir into a voice repo")
    _init_flags(m, remote_required=True)
    m.set_defaults(fn=cmd_migrate)

    sub.add_parser("pull", help="rebase onto the voice repo (remote wins profile conflicts)").set_defaults(fn=cmd_pull)
    sub.add_parser("push", help="commit live changes and push to the voice repo").set_defaults(fn=cmd_push)

    c = sub.add_parser("config", help="get/set per-machine tunables (model, minCount, minInterval, corpusSync)")
    c.add_argument("key", nargs="?")
    c.add_argument("value", nargs="?")
    c.set_defaults(fn=cmd_config)
```

Import line becomes `from . import backfill, config, gate, paths, store, sync, update`.

- [ ] **Step 4: Run full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add cli/voicectl/cli.py cli/tests/test_cli.py
git commit -m "feat(voice): voicectl init/pull/push/config/migrate-to-repo"
```

---

### Task 10: Two-machine convergence test

**Files:**
- Modify: `cli/tests/test_store.py` (append)

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run**

Run: `uv run pytest tests/test_store.py::test_two_machines_converge -q`
Expected: PASS. If it fails on B's prep marker, confirm A's `update.apply` pushed (`git -C <a> log origin/main`).

- [ ] **Step 3: Commit**

```bash
git add cli/tests/test_store.py
git commit -m "test(voice): two machines converge on one core and one corpus"
```

---

### Task 11: Ship templates instead of the owner's profiles

**Files:**
- Rewrite: `references/voices/core.md`, `blog.md`, `research.md`, `chat.md`, `storycraft.md`
- Modify: `references/voice-overlay-template.md` (one line)

The owner's current profiles are preserved in git history and in `~/.madskillz/voice/` (migrated in Task 14). Do **not** copy any owner-specific bullet into a template.

- [ ] **Step 1: Write `references/voices/core.md`**

```markdown
---
voice: core
owner: <handle>
purpose: how the owner talks and thinks - the descriptive base every context voice extends
status: template
---

# Voice core - how <handle> actually talks and thinks

> The owner's real, evolving voice base. Context overlays (blog, research, chat, storycraft)
> extend this file; `voicectl render <context>` merges an overlay's prescriptive layer with
> this core into the one doc a writer reads. This is a **voice**, not a set of facts; nothing
> here licenses bending the substance. The descriptive sections below are filled in only from
> the owner's real messages by "update my voice": **keep** = preserve as flavor,
> **tone-down** = crutch, don't reproduce literally in prose.

## Two layers, on purpose
- **Descriptive - "how I actually talk."** A faithful record of real tendencies and tics so the
  voice can *represent* the owner. Each is tagged **keep** or **tone-down**.
- **Prescriptive - "how that becomes good writing."** Lives in the overlays. When the two
  conflict for published writing, **prescriptive wins.**

## Mechanics
<!-- Observed sentence-level habits: punctuation, rhythm, openers, self-corrections. Filled by
"update my voice" from the corpus. Empty until the first update pass. -->

## Inquiry style
<!-- How the owner chews on an idea: question shapes, analogies, push-back moves. Observed only. -->

## Phrasebook
<!-- Recurring phrases, openers, go-aheads, with rough frequencies when known. Observed only. -->

## Decision heuristics
<!-- How the owner decides and says so. Observed only. -->

## AI-tells
**Scope: every register.** Moves that read as a model, not the owner. Start with this
register-independent baseline; "update my voice" appends owner-specific corrections as the owner
red-lines drafts.
- **Unearned importance** - never assert that something matters without saying why or how much.
  Delete "the key insight here", "most importantly", "this cannot be overstated"; give a cost,
  a count, or a consequence instead.
- **Truisms and maxims** - if a sentence would survive being printed on a poster, cut it and
  state what is true *here*.
- **Manufactured catchy phrasing** ("The X that separates A from B is C") - write the
  observation or instruction plainly.
- **Announcing the statement** ("to be clear", "it is worth saying") - say the thing.
- **Narrator-emotion framing** ("what worries me here") - state the risk and its mechanism.
- **"not because X, but because Y"** - state the one real cause.
- **Colon-reveal flourishes** ("and I'm keeping it:", "and it's a big one:") - state the
  preference or the bound; its size shows itself.
- **Self-help nouns** ("the takeaway", "the reframe") - say what changed plainly.

## Flagged overuse (tendencies to watch)
<!-- Words and phrases the owner leans on; vary them in prose. Observed only, with counts. -->

## Provenance & sync
- Processed through: none
- Repo-synced through: none
- Changelog:
  - <date> - seeded from the voice skill template.
```

- [ ] **Step 2: Write the overlay templates**

`references/voices/blog.md`:

```markdown
---
voice: blog
owner: <handle>
purpose: first-person blog posts in the owner's voice for a curious general reader
status: template
extends: core
---

# Voice: blog - the owner's blog register

You are writing a blog post **as the owner** - first person, in their voice. Share the learning
journey of an idea so a curious general reader comes away understanding it and finding it
neat. Correctness outranks every stylistic move. The descriptive base and the AI-tells come
from the core profile; this overlay is how that voice becomes a good post.

## Who I am on the page
- A curious non-specialist who walks in with a mental model, gets corrected, and treats the
  correction as the point of the post.
- The reader's stand-in: if I was confused, they were too, and we work it out together.
- I write to reach a normal human without dumbing the substance down.

## Voice rules
- Backstory and reader-grounding first: assume curiosity, never prior knowledge.
- Comparisons are explicit similes with a concrete scene ("that's like..."), never a
  compressed aphorism.
- Setup sized to the joke or the correction: enough for it to land, no scaffolding beyond that.
- Link the real research inline and credit the people who did it.
- Structure moves (a reversal, a reveal) are never labeled in the prose.

## Register: colloquial vs. formal writing
- Blog is the colloquial register: humor and asides are allowed here and switched off in
  `research`. Directness and structure carry over; irony does not.
```

`references/voices/research.md`:

```markdown
---
voice: research
owner: <handle>
purpose: professional and research writing in the owner's voice - papers, briefs, field manuals
status: template
extends: core
---

# Voice: research - the owner's professional register

Formal register. No sarcasm, no colloquialism, no jokes. The owner's directness, structure,
and willingness to say "I could not verify this" carry over; the humor moves do not. The
catchy-phrase AI-tell applies hardest here, because a model reaches for polish when the humor
is switched off.

## Register: professional/research writing
- Short declarative sentences. One claim per sentence.
- Say what is uncertain and why; never trade truth for defensibility.
- No hedging stacks: one honest qualifier, then the claim.

## Evidence and claims
- Every quantitative claim carries its number and its source.
- Unlinked claims are "trust me" - link or cut.
- Name the mechanism, not the importance.
```

`references/voices/chat.md`:

```markdown
---
voice: chat
owner: <handle>
purpose: conversational messages written as the owner - replies, comments, short posts
status: template
extends: core
---

# Voice: chat - the owner's conversational register

Short, direct, in the owner's actual cadence. The descriptive layer in core is the whole
point here: this is the register closest to how the owner already types.

## Conversational rules
- Keep the owner's **keep**-tagged mechanics; drop the **tone-down** ones only where they
  would read as sloppy to a stranger.
- No sign-offs, no preamble, no restating the question.
- Typos and chat artifacts in the core are descriptive, not licensed: write clean.
```

`references/voices/storycraft.md`:

```markdown
---
voice: storycraft
owner: <handle>
purpose: fiction narration and character prose written in the owner's voice
status: template
extends: core
---

# Voice: storycraft - the owner's narrative register

Narration carries the owner's rhythm and comparison habits; characters carry their own voices.
The AI-tells in core apply to narration in full.

## Narration rules
- The owner's sentence rhythm (from core Mechanics) sets the narration's default cadence.
- Comparisons are concrete and physical, never aphoristic.
- No manufactured reveals; a reversal is written, not announced.
- Dialogue is exempt from the owner's voice - each character owns their own.
```

- [ ] **Step 3: Update `references/voice-overlay-template.md`**

Change the copy instruction paragraph to:

```markdown
> **Copy this file to `~/.madskillz/voice/<name>.md`** (your voice store, not the skill),
> set `status: personal`, fill the frontmatter, and write only the **prescriptive** rules for
> this medium. The descriptive layer always comes from `core.md`; `voicectl render <name>`
> merges the two. Then `voicectl push`. Never present a template as the owner.
```

- [ ] **Step 4: Verify render works from templates**

Run:

```bash
cd plugins/madskillz/skills/voice/cli
VOICE_DIR=/tmp/claude-1000/-home-bub-Development-madskillz/d3188f06-d1e2-4568-b76a-a894b72e5f1e/scratchpad/tpl-check uv run voicectl init >/dev/null
VOICE_DIR=/tmp/claude-1000/-home-bub-Development-madskillz/d3188f06-d1e2-4568-b76a-a894b72e5f1e/scratchpad/tpl-check uv run voicectl render blog | head -20
VOICE_DIR=/tmp/claude-1000/-home-bub-Development-madskillz/d3188f06-d1e2-4568-b76a-a894b72e5f1e/scratchpad/tpl-check uv run python -c "from voicectl.profile import validate_core; import pathlib; print(validate_core(pathlib.Path('/tmp/claude-1000/-home-bub-Development-madskillz/d3188f06-d1e2-4568-b76a-a894b72e5f1e/scratchpad/tpl-check/core.md').read_text()))"
```

Expected: rendered blog doc with `voice: blog`, `owner: <git user.name>`; `validate_core` prints `[]`.

- [ ] **Step 5: Commit**

```bash
git add references/voices references/voice-overlay-template.md
git commit -m "feat(voice): ship profile templates; owner profiles leave the plugin repo"
```

---

### Task 12: Installer + installer test

**Files:**
- Modify: `scripts/install_voice_pipeline.sh`
- Modify: `scripts/install_voice_pipeline.test.sh`

- [ ] **Step 1: Rewrite the installer**

```bash
#!/usr/bin/env bash
# install_voice_pipeline.sh - one-shot, idempotent installer for the voice skill on this machine.
#
# What it sets up:
#   1. ~/.madskillz/voice/tool/                 copy of voicectl + profile templates, installed as a uv tool
#   2. ~/.claude/hooks/capture-voice.sh         global UserPromptSubmit shim -> voicectl capture
#   3. ~/.claude/hooks/voice-sync-gate.sh       SessionEnd shim -> voicectl gate
#   4. ~/.claude/settings.json                  hook wiring for 2 + 3 (never clobbers other hooks)
#   5. ~/.madskillz/voice/                      the voice store: `voicectl init` (clone/adopt/create)
#   6. corpus backfill + first push
#
# Env:
#   VOICE_DIR                 voice dir                       (~/.madskillz/voice)
#   CLAUDE_DIR                claude config dir               (~/.claude)
#   VOICE_REMOTE              git URL of your private voice repo; unset = local-only
#   VOICE_CREATE=1            create VOICE_REMOTE (github.com + gh) if it does not exist
#   VOICE_ALLOW_PUBLIC=1      allow a public remote (the corpus holds verbatim prompts)
#   VOICE_INSTALL_NO_TOOL=1   skip the uv tool install (tests / offline)
#   VOICE_INSTALL_NO_INIT=1   skip init/backfill/push (tests)
set -u

here="$(cd "$(dirname "$0")" && pwd)"
skill_root="$(cd "$here/.." && pwd)"
VOICE_DIR="${VOICE_DIR:-$HOME/.madskillz/voice}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
export VOICE_DIR CLAUDE_DIR

say() { printf '%s\n' "$*"; }
ok=0; skipped=0
did()  { say "  + $*"; ok=$((ok+1)); }
skip() { say "  = $*"; skipped=$((skipped+1)); }

command -v python3 >/dev/null 2>&1 || { say "ERROR: python3 required"; exit 1; }
command -v git >/dev/null 2>&1 || { say "ERROR: git required"; exit 1; }

# --- 1. voicectl tool + templates -----------------------------------------------------------
# The tool copy lives OUTSIDE the store's tracked files (tool/ is gitignored) so it never
# dangles when the skill checkout moves, and templates ride along for `voicectl init`.
tool_dir="$VOICE_DIR/tool"
if [ -n "${VOICE_INSTALL_NO_TOOL:-}" ]; then
  skip "voicectl install skipped (VOICE_INSTALL_NO_TOOL)"
elif ! command -v uv >/dev/null 2>&1; then
  say "  ! uv not found - voicectl not installed; install uv and re-run"
else
  rm -rf "$tool_dir"
  mkdir -p "$tool_dir/templates"
  cp -r "$skill_root/cli/pyproject.toml" "$skill_root/cli/voicectl" "$tool_dir/"
  cp "$skill_root/references/voices/"*.md "$tool_dir/templates/"
  if uv tool install --force --quiet "$tool_dir" 2>/dev/null; then
    did "installed voicectl (uv tool) from $tool_dir"
  else
    say "  ! uv tool install failed - voicectl unavailable"
  fi
fi

# --- 2+3. hook shims ---------------------------------------------------------------------------
mkdir -p "$CLAUDE_DIR/hooks"
for h in capture-voice.sh voice-sync-gate.sh; do
  src="$skill_root/hooks/$h" dst="$CLAUDE_DIR/hooks/$h"
  [ -f "$src" ] || { say "ERROR: hook source missing: $src"; exit 1; }
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then skip "hook current: $dst"; else
    cp "$src" "$dst" && chmod +x "$dst" && did "installed hook: $dst"
  fi
done

# --- 4. settings.json --------------------------------------------------------------------------
# Adds the two hook entries, matched by script name. An existing gate entry that still carries
# the old VOICE_SYNC_REPO / VOICE_SYNC_AUTOREFRESH env is rewritten to the plain command.
wired="$(SETTINGS="$CLAUDE_DIR/settings.json" python3 - <<'PY'
import json, os, sys

path = os.environ["SETTINGS"]
try:
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
except FileNotFoundError:
    settings = {}
except Exception as e:
    print(f"ERROR: cannot parse {path}: {e}")
    sys.exit(1)

hooks = settings.setdefault("hooks", {})
wanted = {
    "UserPromptSubmit": ("capture-voice.sh", 'bash "$HOME/.claude/hooks/capture-voice.sh"'),
    "SessionEnd": ("voice-sync-gate.sh", 'bash "$HOME/.claude/hooks/voice-sync-gate.sh"'),
}
changed = []
for event, (marker, command) in wanted.items():
    entries = hooks.setdefault(event, [])
    found = None
    for e in entries:
        for h in e.get("hooks", []):
            if marker in h.get("command", ""):
                found = h
    if found is None:
        entries.append({"hooks": [{"type": "command", "command": command, "timeout": 10}]})
        changed.append(f"{event}:added")
    elif found["command"] != command and "VOICE_SYNC_" in found["command"]:
        found["command"] = command
        changed.append(f"{event}:rewritten")

if changed:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
print(",".join(changed) if changed else "none")
PY
)"
case "$wired" in
  ERROR*) say "$wired"; exit 1 ;;
  none)   skip "settings.json hooks already wired" ;;
  *)      did "settings.json: $wired" ;;
esac

# --- 5+6. the voice store ------------------------------------------------------------------------
PATH="$HOME/.local/bin:$PATH"
if [ -n "${VOICE_INSTALL_NO_INIT:-}" ]; then
  skip "store init skipped (VOICE_INSTALL_NO_INIT)"
elif ! command -v voicectl >/dev/null 2>&1; then
  say "  ! voicectl not on PATH - store init skipped; re-run after installing uv"
else
  init_args=()
  if [ -n "${VOICE_REMOTE:-}" ]; then
    init_args+=(--remote "$VOICE_REMOTE")
    [ -n "${VOICE_CREATE:-}" ] && init_args+=(--create)
    [ -n "${VOICE_ALLOW_PUBLIC:-}" ] && init_args+=(--allow-public)
  fi
  if out="$(voicectl init "${init_args[@]}" 2>&1)"; then
    say "$out" | sed 's/^/    /'
    did "voice store ready ($VOICE_DIR)"
    if voicectl backfill >/dev/null 2>&1; then did "backfilled local Claude history into the corpus"; fi
    if [ -n "${VOICE_REMOTE:-}" ]; then
      if out="$(voicectl push 2>&1)"; then did "$out"; else say "  ! push failed: $out"; fi
    else
      say "  ! local-only: set VOICE_REMOTE (or ask Claude to 'set up my voice') to sync across machines"
    fi
  else
    say "  ! voicectl init failed:"; say "$out" | sed 's/^/    /'
  fi
fi

say ""
say "voice pipeline: $ok change(s), $skipped already in place."
```

- [ ] **Step 2: Rewrite the installer test**

```bash
#!/usr/bin/env bash
# Sandboxed test for install_voice_pipeline.sh: hooks + settings wiring, idempotent re-run,
# and the old gate command gets rewritten. Store init is exercised by the pytest suite.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

export VOICE_DIR="$tmp/voice" CLAUDE_DIR="$tmp/claude"
export VOICE_INSTALL_NO_TOOL=1 VOICE_INSTALL_NO_INIT=1

fail() { echo "FAIL: $*"; exit 1; }

mkdir -p "$CLAUDE_DIR"
cat > "$CLAUDE_DIR/settings.json" <<'JSON'
{"hooks": {"SessionEnd": [{"hooks": [{"type": "command",
 "command": "VOICE_SYNC_REPO=\"$HOME/.madskillz/voice/madskillz-sync\" VOICE_SYNC_AUTOREFRESH=1 bash \"$HOME/.claude/hooks/voice-sync-gate.sh\"", "timeout": 10}]}]}}
JSON

out1="$(bash "$here/install_voice_pipeline.sh")"
[ -x "$CLAUDE_DIR/hooks/capture-voice.sh" ] || fail "capture hook missing"
[ -x "$CLAUDE_DIR/hooks/voice-sync-gate.sh" ] || fail "gate hook missing"
grep -q "capture-voice.sh" "$CLAUDE_DIR/settings.json" || fail "UserPromptSubmit not wired"
grep -q "VOICE_SYNC_REPO" "$CLAUDE_DIR/settings.json" && fail "old gate command not rewritten"
echo "$out1" | grep -q "SessionEnd:rewritten" || fail "expected rewrite notice: $out1"

out2="$(bash "$here/install_voice_pipeline.sh")"
echo "$out2" | grep -q "0 change(s)" || fail "re-run was not a no-op: $out2"
n="$(grep -c "capture-voice.sh" "$CLAUDE_DIR/settings.json")"
[ "$n" -eq 1 ] || fail "duplicate capture hook wiring ($n)"

echo "PASS: install_voice_pipeline.test.sh"
```

- [ ] **Step 3: Run it**

Run: `bash plugins/madskillz/skills/voice/scripts/install_voice_pipeline.test.sh`
Expected: `PASS: install_voice_pipeline.test.sh`.

- [ ] **Step 4: Commit**

```bash
git add scripts/install_voice_pipeline.sh scripts/install_voice_pipeline.test.sh
git commit -m "feat(voice): installer wires the voice store via voicectl init; drops the sync clone"
```

---

### Task 13: Docs - SKILL.md init flow, CLAUDE.md, evals, memory

**Files:**
- Modify: `plugins/madskillz/skills/voice/SKILL.md`
- Modify: `CLAUDE.md` (repo root)
- Modify: `plugins/madskillz/skills/voice/evals/evals.json:13`
- Modify: `/home/bub/.claude/projects/-home-bub-Development-madskillz/memory/voice-system-voicectl.md`

- [ ] **Step 1: SKILL.md**

Replace the intro paragraph's last two sentences and the "Updating", "Minting", "Machine setup" sections:

Intro (replace from "A writer never reads these separately" to the end of that paragraph):

```markdown
A writer never reads these separately: `voicectl render <context>` deterministically merges the
overlay's prescriptive layer with the core into one doc. The live copies live in the user's
**voice store** - `~/.madskillz/voice/`, a clone of a private git repo the user owns - so every
machine converges on one core, one overlay set, one corpus. This skill ships only templates;
nobody's real profile is in the plugin.
```

"Updating the voice" step 4 becomes:

```markdown
4. `update-apply` pushes to the voice store on its own. If it reports `push failed`, run
   `voicectl sync` when back online; the local apply stands.
```

and step 1 gains: "`update-prep` pulls first; a `pull: conflict-remote-kept` result means
another machine updated concurrently - the remote core is now the base, continue normally."

"Minting a new context voice": change the copy target to `~/.madskillz/voice/<name>.md` and
end with "`voicectl push` when the owner has reviewed it."

Replace "Machine setup (once)" with:

```markdown
## Setting up a machine ("set up my voice")

Run `bash scripts/install_voice_pipeline.sh` once (installs `voicectl`, the hooks, and
templates). Then wire the voice store. The user never needs the flags; walk them through this:

1. `voicectl status --json`. If `mode` is `synced`, done - report `remote` and `contexts`.
2. Ask one question: **Where should your voice live?**
   - **Existing repo** - they paste a URL or `owner/name`.
   - **Create one for me** - default `<github-user>/voice` (`gh api user -q .login`).
   - **Local only** - no sync; say plainly that other machines will not see this voice.
3. Resolve `owner/name` to a URL: `git@github.com:owner/name.git` if `ssh -T git@github.com`
   succeeds, else `https://github.com/owner/name.git`.
4. `voicectl init --remote URL`. Exit 3 with a `refused:` line means one of:
   - `remote not found` - re-run with `--create` (github + `gh` only; other hosts: the user
     creates the repo, then re-run).
   - `is PUBLIC` - the corpus holds verbatim prompts. Offer `gh repo edit owner/name
     --visibility private --accept-visibility-change-consequences`, or `--allow-public` if
     the user insists.
   - `not a voice store` - the repo has other content. Ask for another repo.
5. `voicectl backfill`, then `voicectl push`.
6. Report `voicectl status`: `remote`, `mode`, corpus line count, `contexts`.

**Second machine:** same flow. Step 4 finds the existing store and clones it; if this machine
already had a local-only voice dir, `init` backs it up to `~/.madskillz/voice.bak-<ts>`, keeps
the remote profiles, and folds the local corpus in. Nothing is lost.

Per-machine tunables: `voicectl config` (`model`, `minCount`, `minInterval`, `corpusSync`).
`corpusSync=false` is reserved and not enforced yet; the corpus is always pushed.
```

Edge cases: replace "Sync clone missing/offline" with "Offline: `update-prep` says
`pull: offline` and works from the local core; `update-apply` applies locally and reports
the unpushed state. `voicectl sync` later."

- [ ] **Step 2: CLAUDE.md**

Delete the `voice-sync` bullet (lines 15-18). The remaining bullet keeps "Two deliberate
exceptions" → change to "One deliberate exception".

- [ ] **Step 3: evals.json line 13**

Change `"Runs \`voicectl sync\` afterwards and reports its verdict"` to
`"Reports the push result that \`voicectl update-apply\` prints"`.

- [ ] **Step 4: Memory file**

Overwrite `voice-system-voicectl.md` body (keep frontmatter, update description):

```markdown
---
name: voice-system-voicectl
description: voice skill = templates + voicectl; user's real profiles + corpus live in a private "voice store" repo cloned to ~/.madskillz/voice
metadata:
  type: project
---

The voice skill (`plugins/madskillz/skills/voice`) ships only profile templates. The user's
real `core.md`, overlays, and `corpus.jsonl` live in a private git repo cloned to
`~/.madskillz/voice/` (the voice store). `voicectl init --remote URL [--create]` wires a
machine; `update-prep` pulls, `update-apply` pushes; `corpus.jsonl` uses `merge=union`.
Owner's store: `git@github.com:bubthegreat/voice.git` (migrated 2026-08-25).

**Why:** productization - other people can use the skill without their voice landing in
madskillz, and N machines converge on one profile.

**How to apply:** never commit personal voice content into madskillz; for voice questions
run `voicectl status --json` first. Spec: `docs/superpowers/specs/2026-08-25-voice-user-repo-storage-design.md`.
```

- [ ] **Step 5: Commit**

```bash
git add plugins/madskillz/skills/voice/SKILL.md CLAUDE.md plugins/madskillz/skills/voice/evals/evals.json
git commit -m "docs(voice): agent-driven init flow, drop sync-clone exception"
```

---

### Task 14: Owner migration (this machine)

**This task pushes the owner's verbatim prompt corpus to GitHub. Confirm with the owner before Step 2; do not run it from a subagent.**

- [ ] **Step 1: Install the new tool locally and dry-check**

```bash
bash plugins/madskillz/skills/voice/scripts/install_voice_pipeline.sh   # VOICE_REMOTE unset: local-only, tool refreshed
voicectl status --json
```

Expected: `mode: local-only`, `core_exists: true`, contexts `blog, chat, research, storycraft`. Note `voice.md` and `posts/` are now gitignored; `posts/authority-accountability-alignment.md` will be preserved in the backup dir by Step 2.

- [ ] **Step 2: Create the private repo and migrate (owner-confirmed)**

```bash
voicectl migrate-to-repo --remote git@github.com:bubthegreat/voice.git --create
voicectl status --json
```

Expected: `action: adopted-empty`, `visibility: PRIVATE`, `mode: synced`, `ahead: 0`. Check
`gh repo view bubthegreat/voice --json visibility` says `PRIVATE`.

- [ ] **Step 3: Remove the dead sync clone and copy the stray post out**

```bash
cp ~/.madskillz/voice/posts/authority-accountability-alignment.md ~/Development/   # owner decides final home
rm -rf ~/.madskillz/voice/madskillz-sync ~/.madskillz/voice/voice.md
voicectl status --json | grep -E '"mode"|"dirty"'
```

Expected: `dirty: []` (both paths are gitignored).

- [ ] **Step 4: Full verification**

```bash
cd plugins/madskillz/skills/voice/cli && uv run pytest -q
bash ../scripts/install_voice_pipeline.test.sh
voicectl render blog | head -5
```

Expected: all tests pass; render shows `owner: bubthegreat`.

- [ ] **Step 5: Final commit + memory**

Write the memory file from Task 13 Step 4 (it references the migrated remote), then:

```bash
git status --short   # should be clean except nothing; memory lives outside the repo
```

---

## Self-review

**Spec coverage.**
- Layout / templates only → Task 11. Store layout + scaffold → Task 4.
- Configuration modes + `voice.*` keys → Tasks 2, 4 (`mode()`), 9 (`config` cmd).
- CLI table: `init` flags/`--create`/visibility → Task 5, 9; `pull`/`push` → 4, 9; `sync` → 6;
  `update-prep`/`update-apply` → 7; `status` fields → 6; `config` → 9; `migrate-to-repo` → 9;
  `gate` → 8; `backfill` unchanged (installer calls it, Task 12).
- Removed names (`sync_repo`, `sync_branch`, `VOICES_SUBPATH`, `NON_OVERLAY["voice.md"]`) → Task 3.
- Init flow (agent-driven) → Task 13 SKILL.md; installer non-interactive form → Task 12.
- Multi-machine: union + dedupe → Tasks 1, 4; conflict → 4; two-machine → 10.
- Privacy: visibility check + README + `corpusSync` key → Tasks 4, 5, 2. **Gap:** the spec's
  `corpusSync=false` behavior (do not commit corpus; status warning) has no task. Deliberate
  deferral - the key exists and reads `true`; enforcing `false` in `push()` (exclude
  `corpus.jsonl` from `git add`) and the status warning are a follow-up once someone needs it.
  SKILL.md (Task 13) states the key is reserved and not enforced.
- Error handling: offline prep/apply → Task 7; never mid-rebase → Task 4; hooks → unchanged.
- Owner migration → Task 14. CLAUDE.md exception + memory → Task 13/14.

**Placeholders.** None; every step has code or exact commands.

**Type consistency.** `store.init()` returns `dict` with `mode/action/seeded/backup/visibility/created`
and Task 9 prints those keys. `store.pull()` returns `int` 0/2 used by `update._pull_status()`
and `sync.run()`. `config.get_int/get_bool` used by `gate.py` and `sync.status_info()`.
`tests.test_store._make_synced_store` and `_git` are imported by Tasks 6, 7, 9, 10 - both are
defined at module scope in Task 4/5's test file.
