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

# --- Test 4: uv missing -> exit 2. Use a PATH dir holding only bash (the
#     preflight uses builtins only), so uv is unfindable but bash still runs.
#     (An empty PATH would also stop bash itself from launching.) ---
mkdir -p "$TMP/none"
ln -s "$(command -v bash)" "$TMP/none/bash"
PATH="$TMP/none" bash "$SUT" "$PROJ" >/dev/null 2>&1
[ "$?" -eq 2 ] || fail "expected exit 2 when uv is absent"

echo "PASS"
