# CLAUDE.md

Guidance for AI agents working in this repository.

## Parallel work / workspace isolation

For parallel work streams **in this repo**, use the clean superpowers worktree method
(`superpowers:using-git-worktrees`): isolated working dirs under `.worktrees/` (gitignored),
created via native tooling, all sharing this one repo. Do **not** create nested worktrees
inside the repo or pin a branch into a side worktree — that tangle is exactly what this
convention exists to prevent.

Two deliberate exceptions — do **not** "simplify" these into superpowers worktrees:

- **voice-sync** runs from a standalone *clone* at `~/.claude/voice/madskillz-sync` pinned to
  `main`. Its background-push hook (`~/.claude/hooks/voice-sync-gate.sh`) is hard-pinned to
  `main` (auto-reset + push to `main`); making it a worktree re-locks `main` out of the
  primary checkout. Keep it a clone.
- **`scientific-study`**'s `git-workflow` uses a bare clone + per-study worktrees against the
  *external* `jmresearch/research` repo for concurrency isolation across simultaneous research
  runs. That is intentional and stays as-is; superpowers' native worktree tool isolates the
  *current* project, not an external clone, so it does not apply there.
