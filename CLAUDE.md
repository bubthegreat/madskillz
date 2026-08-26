# CLAUDE.md

Guidance for AI agents working in this repository.

## Parallel work / workspace isolation

For parallel work streams **in this repo**, use the clean superpowers worktree method
(`superpowers:using-git-worktrees`): isolated working dirs under `.worktrees/` (gitignored),
created via native tooling, all sharing this one repo. Do **not** create nested worktrees
inside the repo or pin a branch into a side worktree — that tangle is exactly what this
convention exists to prevent.

One deliberate exception — do **not** "simplify" this into a superpowers worktree:

- **`scientific-study`**'s `git-workflow` uses a bare clone + per-study worktrees against the
  *external* `jmresearch/research` repo for concurrency isolation across simultaneous research
  runs. That is intentional and stays as-is; superpowers' native worktree tool isolates the
  *current* project, not an external clone, so it does not apply there.
