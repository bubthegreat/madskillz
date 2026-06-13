# semverer-setup — Skill Design

**Date:** 2026-06-13
**Status:** Approved
**Home:** `plugins/madskillz/skills/semverer-setup/SKILL.md`

## Problem

Adopting [semverer](https://github.com/bubthegreat/semverer) (AST-driven automatic
semver bumping) in a Python project is a fixed, multi-step wiring job: add the dev
dependency, ensure pre-commit is active, register the auto-bump hook, snapshot the
baseline, install the in-repo usage skill, and gate CI on a stale version. Done by
hand it is easy to half-finish — e.g. the hook is added but `pre-commit install` was
never run, so it silently never fires.

semverer already ships two of the pieces itself: its own **usage** Agent Skill
(`semverer skill install` writes the "how to use semverer day-to-day" SKILL.md) and
its own **pre-commit hooks** (`.pre-commit-hooks.yaml`: `semverer` / `semverer-check`).
What's missing is the **bootstrap**: a repeatable, idempotent setup that wires those
pieces into a project — automatically for new projects, on request for existing ones.

This skill is that bootstrap. It is explicitly **not** the usage skill: the moment a
project is already configured, this skill no-ops and the bundled `semverer` usage
skill takes over.

## Decisions made

| Question | Decision |
|---|---|
| Install / automation strategy | **uv dev-dep + pre-commit.** `uv add --dev semverer`, register a `local` hook running `uv run semverer update`, `semverer init`. Mirrors how semverer configures itself (`language: system`, `uv run`). |
| Net-new vs existing detection | **By task context.** Net-new = scaffolding a new project this session (just ran `uv init`, project freshly created, or git repo has no commits) → set up automatically, no prompt. Otherwise existing → prompt once. |
| "Check once" behavior | Prompt **once per session** for existing projects; if declined, drop it for the rest of the session. **No marker file** is written. The durable "already handled" signal is the presence of `[tool.semverer]` config itself. |
| Optional setup steps included | Bootstrap pre-commit if absent; install the project-local usage skill (`semverer skill install --project`); add a CI check gate. |
| Optional steps excluded | **No `semverer audit`** pre-adoption history check. |
| Relation to the bundled `semverer` usage skill | Complement, no overlap. This skill's description is setup-only; it no-ops when `[tool.semverer]` already exists, leaving day-to-day usage to the `semverer` skill. |
| Name | `semverer-setup`. |
| Mechanical work | A bundled idempotent helper script (`scripts/setup.sh`) does the unambiguous wiring (steps 1–5); CI editing (step 6) is done by Claude per SKILL.md because CI files vary. |

## When it triggers

Description is **setup-scoped** so it never competes with the usage skill:

> Use when a Python project needs automatic semantic versioning *set up* — scaffolding
> a new Python package, or working in an existing Python package (has `pyproject.toml`)
> that does **not yet** have semverer configured. Wires in semverer as a uv dev-dep, a
> pre-commit auto-bump hook, the baseline, the project-local usage skill, and a CI
> check. Not for using semverer once it's configured — that's the bundled `semverer`
> skill.

**First action on invocation:** check for `[tool.semverer]` in `pyproject.toml` (and/or
the registered pre-commit hook). If already configured → **no-op and bow out.** This is
what keeps it from nagging on every Python edit and from colliding with the usage skill.

## Net-new vs existing flow

```
Python package found, semverer NOT configured
├── Scaffolding a new project this session?
│   (just ran `uv init` / project freshly created / git repo has no commits)
│      → NET-NEW: run setup automatically, no prompt. It's part of project setup.
└── Otherwise (established repo with real history)
       → EXISTING: prompt once — "Set up semverer automatic versioning? (y/n)"
         • yes → run setup
         • no  → drop it for the rest of the session (no marker file)
```

## Setup procedure (ordered, idempotent)

Every step guards on current state, so a re-run is a safe no-op.

1. `uv add --dev semverer`.
2. **Bootstrap pre-commit if absent** — if the project has no `.pre-commit-config.yaml`
   / no pre-commit usage: `uv add --dev pre-commit`, create the config, and run
   `uv run pre-commit install` so the git hook is actually active.
3. **Register the bump hook** in `.pre-commit-config.yaml` (skip if an `id: semverer`
   hook is already present):
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
4. `uv run semverer init` — establish the baseline (skip if `[tool.semverer.baseline]`
   already exists).
5. `uv run semverer skill install --project` — write the usage SKILL.md into the repo's
   `.claude/skills/`.
6. **CI check gate** — add a `uv run semverer check` step to the project's CI. Claude
   reads any existing workflow (e.g. `.github/workflows/*.yml`) and inserts the step; if
   there is no CI at all, Claude **asks before creating** a new workflow file (creating
   CI is a bigger commitment than a local hook).

## Components — script vs. Claude

- **`scripts/setup.sh`** — deterministic, re-runnable mechanical wiring for steps 1–5:
  `uv add` (semverer, and pre-commit if absent), append the `local` hook only if
  missing, `pre-commit install`, `semverer init` (if no baseline),
  `semverer skill install --project`. Accepts the project path; exits cleanly if
  semverer is already configured.
- **CI gate (step 6)** — Claude does this by hand, guided by SKILL.md, because CI files
  vary too much for a script to merge safely.

## Idempotency & edge cases

- **Already configured** → top-level no-op (both the skill and `setup.sh`).
- **Non-uv project** (no `uv.lock` / `[tool.uv]`) — since the chosen strategy is
  uv-based, the skill notes the project isn't uv-managed and asks before proceeding (or
  falls back to `pip install semverer`); exact fallback nailed down in the plan.
- **Non-semver version** (e.g. `1.4`, `1!2.3`, `1.2.3.4`) — `semverer init` surfaces
  this; the skill relays semverer's own message rather than forcing the version.
- **Multiple packages / monorepo** — out of scope for v1. The skill handles the
  single-package case and points at semverer's `packages` / `members` config docs if a
  multi-package layout is detected.

## Testing plan

Manual test matrix covering the cases that matter:

- net-new (fresh repo) → auto-setup, no prompt;
- existing repo → prompt **accepted** → full setup applied;
- existing repo → prompt **declined** → no changes, stays quiet for the session;
- already-configured project → no-op;
- non-uv project → asks before proceeding.

Optionally add a skill eval per `superpowers:writing-skills` / `skill-creator`
conventions for trigger accuracy (fires on setup scenarios, does **not** fire when
`[tool.semverer]` already present).

## Out of scope (for this skill / v1)

- No re-implementation of semverer usage guidance (the bundled `semverer` skill owns
  that).
- No monorepo / multi-package wiring.
- No `semverer audit` history check before adoption.
- No non-uv-first install path beyond a documented `pip` fallback.
- No automatic creation of CI from scratch without asking.
