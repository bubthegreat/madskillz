# semverer-setup Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `semverer-setup` skill in the madskillz plugin that wires [semverer](https://github.com/bubthegreat/semverer) into a Python project (uv dev-dep + pre-commit auto-bump hook + baseline + project-local usage skill + CI check) — automatically for net-new projects, prompt-once for existing ones.

**Architecture:** A `SKILL.md` governs Claude's judgment (already-configured no-op, net-new-vs-existing detection, prompting, the CI step which varies too much to script). A bundled idempotent bash script `scripts/setup.sh` does the unambiguous mechanical wiring (steps 1–5) for the uv happy path. The script is tested with a `setup.test.sh` that puts fake `uv`/`semverer`/`pre-commit` binaries on `PATH` (same convention as the repo's `play-sound.test.sh`). Deployed through the madskillz marketplace plugin (version bump 0.3.0 → 0.4.0 + marketplace update).

**Tech Stack:** bash, uv, semverer CLI, pre-commit, Claude Code plugin skills (auto-discovered from `skills/`).

Spec: `docs/superpowers/specs/2026-06-13-semverer-setup-skill-design.md`

**Notes for the implementer:**
- semverer is real and on PyPI (`uv add --dev semverer` / `uv tool install semverer`); the semverer CLI provides `init`, `check`, `update`, and `skill install [--project|--user]`. semverer also ships its own *usage* skill — this skill must NOT re-implement that; it only **sets up** the project.
- Plugin skills are auto-discovered from `plugins/madskillz/skills/<name>/SKILL.md`; no registration in `plugin.json`/`marketplace.json` is needed (the existing `uv` and `scope-is-a-contract` skills prove this).
- Test convention in this repo: a sibling `*.test.sh` using fake binaries on `PATH` and a `fail()` helper that ends with `echo "PASS"`. No test framework. See `plugins/madskillz/hooks/play-sound.test.sh`.
- `setup.sh` does the **uv path only**. The non-uv fallback and the CI edit are Claude's job per `SKILL.md` — the script signals those gaps in its summary and via exit code `2`.
- The script must keep its `pyproject.toml` + `uv` preflight checks to shell builtins only (so the "uv missing" test can run with an empty `PATH`).

---

### Task 1: Write `setup.sh` with a test (TDD)

**Files:**
- Create: `plugins/madskillz/skills/semverer-setup/scripts/setup.sh`
- Test: `plugins/madskillz/skills/semverer-setup/scripts/setup.test.sh`

- [ ] **Step 1: Write the failing test**

Create `plugins/madskillz/skills/semverer-setup/scripts/setup.test.sh`:

````bash
#!/usr/bin/env bash
# Test setup.sh with fake uv/semverer/pre-commit on PATH (no real installs).
# Verifies: the wiring is run, the hook is written, init/skill/pre-commit are
# invoked, re-runs are idempotent, and preflight failures exit 2.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUT="$HERE/setup.sh"
fail() { echo "FAIL: $1"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BIN="$TMP/bin"; mkdir -p "$BIN"
LOG="$TMP/cmd.log"

# --- Fakes: log every call; `uv run X` execs X; semverer init writes a baseline
#     and skill install writes the usage skill. ---
cat >"$BIN/uv" <<EOF
#!/usr/bin/env bash
echo "uv \$*" >>"$LOG"
if [ "\$1" = "run" ]; then shift; exec "\$@"; fi
exit 0
EOF
cat >"$BIN/semverer" <<EOF
#!/usr/bin/env bash
echo "semverer \$*" >>"$LOG"
if [ "\$1" = "init" ]; then printf '\n[tool.semverer.baseline]\n' >>pyproject.toml; fi
if [ "\$1" = "skill" ] && [ "\$2" = "install" ]; then
  mkdir -p .claude/skills/semverer && printf 'skill\n' >.claude/skills/semverer/SKILL.md
fi
exit 0
EOF
cat >"$BIN/pre-commit" <<EOF
#!/usr/bin/env bash
echo "pre-commit \$*" >>"$LOG"
exit 0
EOF
chmod +x "$BIN/uv" "$BIN/semverer" "$BIN/pre-commit"

# --- Fixture: a minimal uv-style project ---
PROJ="$TMP/proj"; mkdir -p "$PROJ/src/demo"
cat >"$PROJ/pyproject.toml" <<'EOF'
[project]
name = "demo"
version = "0.1.0"
EOF
: >"$PROJ/src/demo/__init__.py"

# --- Test 1: first run does the full wiring ---
PATH="$BIN:$PATH" bash "$SUT" "$PROJ" >/dev/null 2>&1 \
  || fail "first run exited nonzero"
grep -q 'uv add --dev semverer' "$LOG" || fail "did not add semverer dev dep"
[ -f "$PROJ/.pre-commit-config.yaml" ] || fail "no .pre-commit-config.yaml created"
grep -q 'id: semverer' "$PROJ/.pre-commit-config.yaml" || fail "hook not in config"
grep -q 'pre-commit install' "$LOG" || fail "pre-commit install not run"
grep -q 'semverer init' "$LOG" || fail "semverer init not run"
grep -q 'semverer skill install --project' "$LOG" || fail "skill install not run"
[ -f "$PROJ/.claude/skills/semverer/SKILL.md" ] || fail "usage skill not installed"
grep -q 'tool.semverer.baseline' "$PROJ/pyproject.toml" || fail "baseline not written"

# --- Test 2: second run is idempotent (no dup hook, no re-init) ---
: >"$LOG"
PATH="$BIN:$PATH" bash "$SUT" "$PROJ" >/dev/null 2>&1 \
  || fail "second run exited nonzero"
n="$(grep -c 'id: semverer' "$PROJ/.pre-commit-config.yaml")"
[ "$n" -eq 1 ] || fail "hook duplicated on re-run (count=$n)"
! grep -q 'semverer init' "$LOG" || fail "re-ran semverer init despite existing baseline"

# --- Test 3: not a Python project -> exit 2 ---
mkdir -p "$TMP/empty"
PATH="$BIN:$PATH" bash "$SUT" "$TMP/empty" >/dev/null 2>&1
[ "$?" -eq 2 ] || fail "expected exit 2 for a dir with no pyproject.toml"

# --- Test 4: uv missing -> exit 2 (preflight uses builtins only) ---
PATH= bash "$SUT" "$PROJ" >/dev/null 2>&1
[ "$?" -eq 2 ] || fail "expected exit 2 when uv is absent"

echo "PASS"
````

- [ ] **Step 2: Run the test, verify it fails**

Run: `bash plugins/madskillz/skills/semverer-setup/scripts/setup.test.sh`
Expected: nonzero exit with `FAIL: ...` or a `No such file` error (the SUT does not exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `plugins/madskillz/skills/semverer-setup/scripts/setup.sh`:

````bash
#!/usr/bin/env bash
# semverer-setup: idempotently wire semverer into a uv-managed Python project.
# Usage: setup.sh [PROJECT_DIR]   (default: current directory)
#
# Does steps 1-5 of setup (semverer dev-dep, pre-commit auto-bump hook,
# baseline, project-local usage skill). CI wiring is left to the agent
# (see SKILL.md) because workflow files vary too much to edit safely here.
# Exit codes: 0 = done (or nothing to do), 2 = cannot proceed.
#
# Preflight (pyproject + uv checks) uses shell builtins only, so it behaves
# even with an empty PATH.
set -u

DIR="${1:-.}"
cd "$DIR" 2>/dev/null || { echo "ERROR: cannot enter '$DIR'"; exit 2; }

if [ ! -f pyproject.toml ]; then
  echo "ERROR: no pyproject.toml in '$DIR' — not a Python project. Nothing to do."
  exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: 'uv' not found. This project isn't uv-managed, or uv isn't installed."
  echo "       Set up uv first (see the uv skill), or install semverer by hand (pip install semverer)."
  exit 2
fi

HOOK_BLOCK='  - repo: local
    hooks:
      - id: semverer
        name: semverer (auto version bump)
        entry: uv run semverer update
        language: system
        files: \.py$
        pass_filenames: false'

needs_manual_hook=0

# 1. semverer as a dev dependency (uv add is idempotent)
echo "==> uv add --dev semverer"
uv add --dev semverer

# 2 & 3. pre-commit config + the auto-bump hook
if [ ! -f .pre-commit-config.yaml ]; then
  echo "==> creating .pre-commit-config.yaml with the semverer hook"
  uv add --dev pre-commit
  printf 'repos:\n%s\n' "$HOOK_BLOCK" > .pre-commit-config.yaml
elif ! grep -q 'id: semverer' .pre-commit-config.yaml; then
  echo "MANUAL: .pre-commit-config.yaml exists but has no 'id: semverer' hook."
  echo "MANUAL: add the semverer local hook under its 'repos:' (see SKILL.md)."
  needs_manual_hook=1
else
  echo "==> semverer hook already present in .pre-commit-config.yaml"
fi

# 4. activate the git hook
echo "==> uv run pre-commit install"
uv run pre-commit install

# 5. baseline (only if not already snapshotted)
if grep -q 'tool.semverer.baseline' pyproject.toml; then
  echo "==> baseline already present — skipping semverer init"
else
  echo "==> uv run semverer init"
  uv run semverer init
fi

# 6. project-local usage skill (overwrite is fine — idempotent)
echo "==> uv run semverer skill install --project"
uv run semverer skill install --project

echo
echo "semverer setup complete for '$DIR'."
[ "$needs_manual_hook" -eq 1 ] && \
  echo "NEXT (agent): add the semverer hook to the existing .pre-commit-config.yaml."
echo "NEXT (agent): add a 'uv run semverer check' gate to CI (see SKILL.md)."
exit 0
````

- [ ] **Step 4: Make both files executable**

Run: `chmod +x plugins/madskillz/skills/semverer-setup/scripts/setup.sh plugins/madskillz/skills/semverer-setup/scripts/setup.test.sh`

- [ ] **Step 5: Run the test, verify it passes**

Run: `bash plugins/madskillz/skills/semverer-setup/scripts/setup.test.sh`
Expected: `PASS`, exit 0.

- [ ] **Step 6: Commit**

```bash
git add plugins/madskillz/skills/semverer-setup/scripts/setup.sh plugins/madskillz/skills/semverer-setup/scripts/setup.test.sh
git commit -m "feat: add semverer-setup wiring script with tests"
```

---

### Task 2: Write `SKILL.md`

**Files:**
- Create: `plugins/madskillz/skills/semverer-setup/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `plugins/madskillz/skills/semverer-setup/SKILL.md` with exactly this content:

`````markdown
---
name: semverer-setup
description: >-
  Use when a Python project needs automatic semantic versioning *set up* —
  scaffolding a new Python package, or working in an existing Python package
  (has pyproject.toml) that does not yet have semverer configured. Wires in
  semverer as a uv dev-dependency, a pre-commit auto-bump hook, the baseline,
  the project-local usage skill, and a CI check. Not for using semverer once
  it is configured — that is the bundled `semverer` skill.
---

# semverer-setup: bootstrap automatic semver versioning

This skill wires [semverer](https://github.com/bubthegreat/semverer) into a
Python project so its version bumps automatically from public-API changes. It
is the **setup** counterpart to the `semverer` *usage* skill — once a project
is configured, this skill does nothing and the usage skill takes over.

## Step 0 — Is it already set up?

Check the project's `pyproject.toml` for `[tool.semverer.baseline]` (or an
`id: semverer` hook in `.pre-commit-config.yaml`). **If present, stop — it is
already configured.** Do not prompt and do not re-run setup; the bundled
`semverer` skill governs day-to-day use.

## Step 1 — Net-new or existing?

- **Net-new** — you are scaffolding the project this session (you just ran
  `uv init`, the project was created moments ago, or `git log` shows no
  commits): proceed to setup automatically. It is part of standard project
  setup; no prompt.
- **Existing** — an established repo with real history: ask once —
  > "This Python package has no automatic semver versioning. Set up semverer
  > (uv dev-dep + pre-commit auto-bump + CI check)?"
  - **Yes** → run setup.
  - **No** → drop it for the rest of this session. Write no marker file and do
    not ask again this session.

## Step 2 — Run the wiring script

The mechanical, idempotent steps live in a bundled script. Run it against the
project root:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/semverer-setup/scripts/setup.sh" .
```

It does, each step guarded so re-runs are safe:

1. `uv add --dev semverer`
2. bootstrap pre-commit if absent (`uv add --dev pre-commit` plus a
   `.pre-commit-config.yaml` carrying the semverer `local` hook)
3. ensure the auto-bump hook is registered
4. `uv run pre-commit install`
5. `uv run semverer init` (only if there is no baseline yet)
6. `uv run semverer skill install --project`

Read its output:

- Exit code **2** means it could not proceed — no `pyproject.toml`, or `uv` is
  missing (see *Edge cases*).
- A **`MANUAL:`** line means an existing `.pre-commit-config.yaml` needs the
  semverer hook added by hand. Add this block under its `repos:` (a second
  `- repo: local` entry is valid YAML):

  ```yaml
    - repo: local
      hooks:
        - id: semverer
          name: semverer (auto version bump)
          entry: uv run semverer update
          language: system
          files: \.py$
          pass_filenames: false
  ```

## Step 3 — Add the CI check gate

The script does not touch CI (workflows vary too much). Add a stale-version
gate yourself:

- If the project already has CI (e.g. `.github/workflows/*.yml`), add a step
  to the test/lint job:

  ```yaml
        - name: semverer (version check)
          run: uv run semverer check
  ```

- If there is **no** CI at all, ask before creating a workflow — that is a
  bigger commitment than a local hook. If the user agrees, create
  `.github/workflows/semverer.yml` running `uv run semverer check`.

## Edge cases

- **Not uv-managed** (no `uv.lock` / `[tool.uv]`, or `uv` not installed): the
  script exits `2`. Tell the user the project is not uv-managed and either set
  up uv first (see the `uv` skill) or fall back to `pip install semverer` plus
  the same pre-commit hook by hand.
- **Version not semver** (`1.4`, `1!2.3`, `1.2.3.4`): `semverer init` reports
  it and exits without forcing a change — relay its message; the user picks a
  compliant starting version, then re-run setup.
- **Multiple packages / monorepo:** out of scope here. Point the user at
  semverer's `[tool.semverer] packages` / `members` config.

## Don't

- Don't re-implement semverer usage guidance — the bundled `semverer` skill
  owns `check` / `update` / `init` day-to-day.
- Don't hand-edit `[tool.semverer.baseline]`; it is machine-managed.
- Don't nag: one prompt per session for existing projects.
`````

- [ ] **Step 2: Verify the frontmatter parses and the path is right**

Run:
```bash
python3 -c "import sys,re; t=open('plugins/madskillz/skills/semverer-setup/SKILL.md').read(); m=re.match(r'^---\n(.*?)\n---\n', t, re.S); assert m, 'no frontmatter'; import yaml; d=yaml.safe_load(m.group(1)); assert d['name']=='semverer-setup', d; print('OK', d['name'])"
```
Expected: `OK semverer-setup`. (If PyYAML is unavailable, instead just confirm the file starts with `---`, has a `name: semverer-setup` line, and a `description:` line.)

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/semverer-setup/SKILL.md
git commit -m "feat: add semverer-setup SKILL.md (detection, flow, CI guidance)"
```

---

### Task 3: End-to-end smoke test against a real uv project (manual)

**Files:** none (verification only). Requires real `uv` + network access to PyPI.

- [ ] **Step 1: Create a throwaway uv library project**

```bash
cd "$(mktemp -d)" && uv init --lib semverer_smoke && cd semverer_smoke && git init -q && git add -A && git commit -qm init
```
Expected: a `src/semverer_smoke/` package with a `pyproject.toml`.

- [ ] **Step 2: Run the real wiring script**

Run: `bash /home/bub/Development/madskillz/plugins/madskillz/skills/semverer-setup/scripts/setup.sh .`
Expected: the `==>` step lines for add / pre-commit / init / skill install, ending with `semverer setup complete` and the CI `NEXT (agent)` line. Exit 0.

- [ ] **Step 3: Verify the project is actually configured**

```bash
grep -q 'tool.semverer.baseline' pyproject.toml && echo "baseline OK"
grep -q 'id: semverer' .pre-commit-config.yaml && echo "hook OK"
test -f .claude/skills/semverer/SKILL.md && echo "usage skill OK"
uv run semverer check; echo "check exit: $?"
```
Expected: `baseline OK`, `hook OK`, `usage skill OK`, and `check exit: 0` (version already matches the just-snapshotted baseline).

- [ ] **Step 4: Verify idempotency on the real project**

Run: `bash /home/bub/Development/madskillz/plugins/madskillz/skills/semverer-setup/scripts/setup.sh .`
Expected: `baseline already present — skipping semverer init`, `semverer hook already present`, still exactly one `id: semverer` in `.pre-commit-config.yaml`. Exit 0.

- [ ] **Step 5: Clean up**

Run: `cd / && rm -rf "$OLDPWD"` (or just delete the temp project dir). No commit — this task only verifies.

---

### Task 4: Bump plugin version, deploy, verify discovery

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json` (version `0.3.0` → `0.4.0`)

- [ ] **Step 1: Bump the plugin version**

In `plugins/madskillz/.claude-plugin/plugin.json`, change `"version": "0.3.0"` to `"version": "0.4.0"`.

Result:
```json
{
  "name": "madskillz",
  "description": "Bub's personal skills bundle",
  "version": "0.4.0",
  "author": { "name": "Bub Taylor", "email": "bubthegreat@gmail.com" }
}
```

- [ ] **Step 2: Commit and push**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore: bump madskillz plugin to 0.4.0 (adds semverer-setup skill)"
git push -u origin feat/semverer-setup-skill
```

- [ ] **Step 3: Refresh the marketplace cache**

Run: `claude plugin marketplace update madskillz`
Expected: "Successfully updated"; the installed plugin picks up 0.4.0.

- [ ] **Step 4: Verify the skill shipped to the cache**

Run: `ls ~/.claude/plugins/cache/madskillz/madskillz/*/skills/semverer-setup/`
Expected: `SKILL.md` and `scripts/` listed.

- [ ] **Step 5: Verify a new session sees the skill**

Run: `cd /tmp && claude -p "List your available skills and tell me yes/no: is there a 'madskillz:semverer-setup' skill?"`
Expected: yes. (If skills are not introspectable via `-p`, instead confirm Step 4's files exist and that Claude Code logged no skill-load errors at startup.)

---

## Self-Review (completed)

- **Spec coverage:**
  - Strategy "uv dev-dep + pre-commit" → Task 1 `setup.sh` (`uv add --dev semverer` + `local` hook running `uv run semverer update`).
  - Trigger / setup-scoped description + already-configured no-op → Task 2 SKILL.md frontmatter + Step 0.
  - Net-new (auto) vs existing (prompt once, no marker) → Task 2 Step 1.
  - Setup steps: dev-dep, bootstrap pre-commit if absent, register hook, `init`, `skill install --project` → Task 1 script + tests.
  - CI check gate (Claude-driven, ask before creating CI) → Task 2 Step 3.
  - Audit explicitly excluded → not present in any task (correct).
  - Edge cases (non-uv exit 2 + fallback, non-semver version, monorepo) → Task 1 preflight/exit-2 + Task 2 Edge cases; non-uv exit-2 covered by Task 1 Test 4.
  - Idempotency → Task 1 Test 2 + Task 3 Step 4.
  - Testing matrix (auto/accept/decline/no-op/non-uv) → Task 1 tests (mechanical) + Task 3 (real) + Task 2 prose for the prompt/decline judgment paths.
  - Deploy via version bump + marketplace update → Task 4.
- **Placeholder scan:** No TBD/TODO; every file's full content is shown; commands have expected output.
- **Type/name consistency:** Skill name `semverer-setup`, dir `plugins/madskillz/skills/semverer-setup/`, script `scripts/setup.sh`, hook id `semverer`, baseline marker substring `tool.semverer.baseline`, and the `uv run semverer update`/`check` commands are identical across the script, the test, and SKILL.md. `${CLAUDE_PLUGIN_ROOT}/skills/semverer-setup/scripts/setup.sh` matches the created path.
- **Decline/no-op paths are judgment, not script:** correctly left to SKILL.md (no test asserts them); the script's tested contract is the mechanical wiring + preflight exits.
