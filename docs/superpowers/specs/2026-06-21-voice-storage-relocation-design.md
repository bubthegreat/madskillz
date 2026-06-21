# Voice storage relocation: `~/.claude/voice` → `~/.madskillz/voice`

**Date:** 2026-06-21
**Status:** approved → implementing
**Plugin version:** 0.10.1 → **0.11.0**

## Problem

The background voice-sync (the SessionEnd gate → detached headless `claude -p "update my voice"`) was
**silently failing**. The capture hook works (the corpus stays current), but the headless agent could
never advance the profile: its markers sat frozen for a day while ~100 corpus messages piled up.

## Root cause

The headless agent runs **least-privilege** (deliberately *not* `--permission-mode
bypassPermissions`). The harness **sensitive-file guard blocks every write under `~/.claude/`**, so
the agent can never edit `~/.claude/voice/voice.md` — and the dedicated sync clone living at
`~/.claude/voice/madskillz-sync` means its `git commit` writes are blocked too. The gate keeps
"passing" and launching, but each run dies at the first write. (Interactive sessions are unaffected —
the user can approve the prompt the headless agent cannot.)

## Decision

Move the **voice data and the sync clone out of `~/.claude/`** to **`~/.madskillz/voice/`**, which is
not on the sensitive-file guard list. The **hook scripts stay in `~/.claude/hooks/`** (that's where
Claude Code loads them) — only data + the clone move.

**Validated up front:** a headless least-privilege probe (`Write` to `~/.madskillz/voice/.guardtest`)
**succeeded**, confirming `~/.madskillz/` is writable by the unattended agent. The sync repo is a
**standalone clone** (`git-common-dir == .git`), so its migration is a plain `mv` — no
`git worktree move`.

Rejected alternative: keep defaults at `~/.claude/voice` and override only via env in `settings.json`.
A half-fix — it leaves the repo scripts/docs lying about the path and gives `capture-voice.sh` no env
support.

## Changes

### Canonical (this repo → PR, version bump 0.11.0)
- `hooks/voice-sync-gate.sh` — default `VOICE_DIR` → `$HOME/.madskillz/voice` (+ comment refs).
- `plugins/madskillz/hooks/capture-voice.sh` — now honors `VOICE_DIR` (default `$HOME/.madskillz/voice`),
  passing the corpus path to python via `VOICE_CORPUS`; replaces the two hardcoded `~/.claude/voice`
  paths. Gives it parity with the gate.
- `plugins/madskillz/hooks/capture-voice.test.sh` — expects the new default path.
- `hooks/voice-sync-gate.test.sh` — unchanged (already drives `VOICE_DIR` via the test harness).
- `plugins/madskillz/skills/blog/{SKILL.md, references/voice-update.md, references/blog-format.md}` —
  all `~/.claude/voice/…` → `~/.madskillz/voice/…`; fixed the stale "`git worktree add`" line to a
  **clone** (matching `CLAUDE.md`'s rationale).
- `CLAUDE.md` — voice-sync clone path updated.
- `plugins/madskillz/.claude-plugin/plugin.json` — `0.10.1` → `0.11.0`.

### Local machine (so this box works immediately; not in the repo)
1. `mkdir -p ~/.madskillz/voice`; move `voice.md`, `corpus.jsonl`, `sync.log`, `.last-sync-attempt`,
   `.sync.lock`, `posts/` (if any) and the `madskillz-sync` clone from `~/.claude/voice/`; delete the
   probe file; remove the emptied `~/.claude/voice/`.
2. Copy updated hooks → `~/.claude/hooks/{voice-sync-gate.sh, capture-voice.sh}`.
3. `~/.claude/settings.json` SessionEnd cmd: `VOICE_SYNC_REPO` → `…/.madskillz/voice/madskillz-sync`
   (+ explicit `VOICE_DIR="$HOME/.madskillz/voice"`). UserPromptSubmit needs no change (new default).

## Validation

- Re-run both hook test suites (must stay green).
- End-to-end: force the gate synchronously (`VOICE_SYNC_LAUNCH`) against the migrated layout and
  confirm the headless agent writes `voice.md` and commits in the new location with no guard denial.

## Risks / mitigations

- **A SessionEnd fires mid-migration.** Low risk: the gate is throttled (12 min) and lock-guarded, and
  the live `voice.md` is the source of truth, so a mistimed run fails safe (no-op). Do data move +
  hooks + settings together.
- **`~/.madskillz/` later becomes guarded.** Unlikely (custom dir, validated now); the env-overridable
  `VOICE_DIR` leaves an escape hatch.
- **Historical specs** under `docs/superpowers/specs/2026-06-20-*` still reference `~/.claude/voice`;
  left as dated provenance. This spec is the record of the move; `voice-update.md` is the live authority
  any voice-consuming skill should follow.
