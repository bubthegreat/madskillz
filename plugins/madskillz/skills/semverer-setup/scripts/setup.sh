#!/usr/bin/env bash
# semverer-setup: idempotently wire semverer into a uv-managed Python project.
# Usage: setup.sh [PROJECT_DIR]   (default: current directory)
#
# Performs the local wiring (each step idempotent): adds semverer as a uv
# dev-dep, ensures a pre-commit auto-bump hook, snapshots the baseline, and
# installs the project-local usage skill. CI wiring is left to the agent
# (see SKILL.md) because workflow files vary too much to edit safely here.
# Exit codes: 0 = done (or nothing to do), 1 = a wiring command failed,
# 2 = cannot proceed (no pyproject.toml, or uv not installed).
#
# Preflight (pyproject + uv checks) uses shell builtins only, so it behaves
# even under a minimal PATH.
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

# Run a wiring command, announcing it; abort (don't report success) if it fails.
run() { echo "==> $*"; "$@" || { echo "ERROR: '$*' failed — setup incomplete."; exit 1; }; }

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
run uv add --dev semverer

# 2 & 3. pre-commit config + the auto-bump hook
if [ ! -f .pre-commit-config.yaml ]; then
  echo "==> creating .pre-commit-config.yaml with the semverer hook"
  printf 'repos:\n%s\n' "$HOOK_BLOCK" > .pre-commit-config.yaml
elif ! grep -q 'id: semverer' .pre-commit-config.yaml; then
  echo "MANUAL: .pre-commit-config.yaml exists but has no 'id: semverer' hook."
  echo "MANUAL: add the semverer local hook under its 'repos:' (see SKILL.md)."
  needs_manual_hook=1
else
  echo "==> semverer hook already present in .pre-commit-config.yaml"
fi

# 4. ensure pre-commit is available, then activate the git hook
run uv add --dev pre-commit
run uv run pre-commit install

# 5. project-local usage skill — installed BEFORE the baseline so init captures
#    it; otherwise the new SKILL.md looks like a pending change and `semverer
#    check` would demand a bump the instant setup finishes.
run uv run semverer skill install --project

# 6. baseline, taken LAST so it snapshots the fully-wired tree (hook config +
#    usage skill) and `semverer check` is clean right after setup.
#    Only if not already snapshotted.
if grep -q 'tool.semverer.baseline' pyproject.toml; then
  echo "==> baseline already present — skipping semverer init"
else
  run uv run semverer init
fi

echo
echo "semverer setup complete for '$DIR'."
[ "$needs_manual_hook" -eq 1 ] && \
  echo "NEXT (agent): add the semverer hook to the existing .pre-commit-config.yaml."
echo "NEXT (agent): add a 'uv run semverer check' gate to CI (see SKILL.md)."
exit 0
