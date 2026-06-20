# Design: owner-keyed voices library + threshold sync + register-aware voice

**Date:** 2026-06-20
**Scope:** `plugins/madskillz/skills/blog` — give the `blog` skill a notion of multiple, named,
owner-specific voices; commit the owner's evolved voice into the repo so non-local agents can read
it; auto-sync local→repo only when changes accumulate; and restructure the voice content to separate
"how I talk" (fidelity) from "how I should write" (quality).

## Motivation

Today the skill has exactly two voice artifacts:
- a generic **seed/template** at `references/voice.md`, and
- a single **live, evolving** profile at `~/.claude/voice/voice.md` (user-local, fed by the capture
  corpus at `~/.claude/voice/corpus.jsonl`).

`~/.claude/` is not a git repo, so the evolved voice never leaves the machine — non-local agents
(cloud runs, other machines) can't benefit from it. The owner also expects to have **more than one
voice of their own** (this science-blog voice vs. a future kids'-goblin-book voice), and the skill
must never present the impersonal template as "me."

Protection target (confirmed): the owner's **own multiple voices (per-purpose)** and the **generic
template** — NOT other people's voices. The library is owner-centric, keyed by purpose.

## 1. Voices library (per-purpose, all the owner's)

```
plugins/madskillz/skills/blog/references/
├── voice.md            → re-labeled the TEMPLATE (never anyone's real voice)
└── voices/
    └── science-blog.md  → the owner's evolved science-blog voice (committed)
        (future: goblin-stories.md, seer-kid.md, …)
```

Each *real* voice carries frontmatter so it can't be confused with the template or another purpose:

```yaml
---
voice: science-blog
owner: bubthegreat
purpose: first-person learning-journey science/blog posts
status: personal      # 'personal' = a real owner voice · 'template' = the generic seed
---
```

`references/voice.md` is restamped at the top as **"TEMPLATE — copy this to mint a new named
voice; this is no one's actual voice."** and given `status: template` framing.

**Voice resolution order** (the anti-conflation logic the skill follows):
1. Local live `~/.claude/voice/voice.md` — freshest, evolves per session → used if present.
2. Repo `references/voices/science-blog.md` — committed owner voice → fallback for non-local agents
   / fresh machines.
3. `references/voice.md` (template) — only to *create* a new voice, never rendered as "me."

**First-run seeding** changes: a fresh local profile is seeded from the repo's
`voices/science-blog.md` (the real evolved voice), not from the generic template.

## 2. Threshold sync (local stays live; auto-push only when earned)

- Local `~/.claude/voice/voice.md` remains the continuously-evolving profile — unchanged, always
  fresh. No forced staleness.
- The live profile gains a new provenance marker `Repo-synced through: <ts>` alongside the existing
  `Processed through: <ts>`.
- During the voice-update step, **after** merging locally, a **materiality check** compares the live
  profile against the committed `voices/science-blog.md`. It syncs only when the delta is
  **material**:
  - a new section/subsection was added, OR
  - ≥3 new substantive traits merged since the last sync, OR
  - prescriptive guidance changed (not just a marker bump).
- On a material delta the skill: copies the merged profile into `voices/science-blog.md`, commits,
  pushes, and advances `Repo-synced through`. Otherwise it does nothing (no commit, no push).
- Net behavior: local is live every session; the repo (what non-local agents read) updates in
  meaningful chunks, automatically, without the owner ever saying "sync."

**Push target (owner-approved default):** commit + push to `main` of madskillz with message
`voice: sync <voice> profile (auto)`. Implemented as a single documented setting near the top of
`voice-update.md` so it can be flipped to a branch/PR later. The **first** sync during initial
rollout is performed as an explicit, visible commit (not silent).

**Deferred (v2, YAGNI for now):** a standalone scheduled/background hook that runs the materiality
assessment on its own. The in-skill check delivers the desired behavior with no daemon/auth
plumbing; revisit if the owner wants pushes independent of running the skill.

## 3. Register-aware voice content (talk vs. write; flag the tics)

Both the template and `science-blog.md` gain an explicit two-layer split, and the updater learns to
populate it:

- **Observed tendencies & verbal tics (descriptive — "how I actually talk").** Idiosyncratic /
  overused phrasing captured faithfully, each tagged `keep` (flavor) or `tone-down` (crutch) with a
  frequency note (e.g. reaches for "parallels" constantly; "freaking cool"; question-stacking). This
  is the **represent-me** layer.
- **Register guidance (prescriptive — "how that becomes good writing").** Rules for translating talk
  → strong prose: keep the flavor, drop the crutches; lowercase / typos / run-ons are *evidence of
  voice, not a license to write sloppily.* The **write-well-as-me** layer that prevents garbage
  output.
- **Updater rule change:** when the updater spots a recurring or overused phrase, it records it as a
  *tendency with an overuse flag + register note*, instead of blindly adding it as a style to
  imitate.

## Files touched

- `plugins/madskillz/skills/blog/SKILL.md` — voice resolution order; reference the named voice;
  first-run seeding from the repo voice; pointer to the voices library.
- `plugins/madskillz/skills/blog/references/voice-update.md` — `Repo-synced through` marker;
  materiality check + sync/commit/push step; push-target setting; updater rule for
  idiosyncrasy/register tracking.
- `plugins/madskillz/skills/blog/references/voice.md` — restamp as TEMPLATE; add the two-layer
  (descriptive/prescriptive) section structure.
- `plugins/madskillz/skills/blog/references/voices/science-blog.md` — NEW; the owner's evolved voice
  (seeded from the current `~/.claude/voice/voice.md`) with frontmatter + the two-layer structure.

## Out of scope

- Other people's voices / per-person keying (explicitly not a goal).
- The standalone background sync hook (v2).
- Any change to the global capture hook or corpus format.
- The future story-writing skill (separate project; this only leaves room for it).

## Success criteria

- The blog skill, asked to write/refresh, uses the owner's named voice and never the bare template
  as "me."
- A fresh/non-local environment with the repo checked out can read the owner's real voice from
  `voices/science-blog.md`.
- "update my voice" keeps the local profile fresh every run but only commits+pushes to the repo when
  the change is material.
- The voice file visibly separates faithful tics (for representation) from prescriptive guidance
  (for quality), and flags overused phrasing.
