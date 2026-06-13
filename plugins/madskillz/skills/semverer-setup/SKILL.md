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
5. `uv run semverer skill install --project`
6. `uv run semverer init` — taken last so the baseline captures the hook config
   and the usage skill, leaving `semverer check` clean (only if there is no
   baseline yet)

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
