---
name: filmcraft
description: >-
  Use when the user wants to make a film, short, music video, or animated sequence with
  generative video — "make a movie," "storyboard this," "turn my story into a film,"
  "generate this scene with Grok," "build me a shot list," or "adapt my book into a
  short." Co-designs the look book and casting with the user, decomposes scenes into a
  validated shot list, locks character/location references so the same actor survives
  every cut, estimates spend before generating, drives the xAI Grok Imagine video API,
  then QAs continuity and cuts the result with ffmpeg. Adapts from a storycraft book or
  works standalone. Storage is a configurable repo the user owns; the skill commits but
  never pushes.
---

# filmcraft: a production crew for generative film

Turn a story into a **shot-listed, continuity-locked, assembled film** — co-designed with
the user, decomposed by a crew of specialist agents, generated clip by clip through the
Grok Imagine video API, and cut together with ffmpeg.

The skill addresses the recurring failures of AI-generated film: the protagonist's face
changing between cuts, wardrobe and lighting drifting scene to scene, dialogue that gets
clipped because it never fit the clip length, shot lists that violate basic film grammar,
and generation spend that runs away before anyone notices. Each failure has either a
deterministic check or a dedicated specialist.

## Relationship to the family

- `storycraft` writes prose books. filmcraft **adapts** one into a film — see
  `storycraft-handoff.md`. It also works standalone from a logline.
- `personas.md` defines the production crew (Director, Script Supervisor, DP, Production
  Designer, Grok Wrangler, Editor); filmcraft orchestrates them.
- `scripts/shot_check.py` and `scripts/estimate_cost.py` are deterministic gates. LLM
  judgment builds on their output, never the other way around.
- `scripts/grok_client.py` is the **only** file that knows the API wire format. Everything
  uncertain about xAI's surface is quarantined there and in `grok-api.md`.

## Integrity stance (non-negotiable)

1. Never fabricate a clip, a check, a continuity verdict, or a render. Report the real
   state or the real failure.
2. **Never generate without an explicit cost confirmation.** Generation is billed per
   second. `estimate_cost.py` runs first, the user sees the number, and `--yes` is
   required. A `budget_usd` overrun is a hard stop, not a warning.
3. Never claim a shot passed continuity QA it did not. Unresolved drift is surfaced at
   the checkpoint, not hidden.
4. The human approves every checkpoint. The skill commits but **never pushes**, and never
   invents story, characters, or canon the user did not approve.
5. **Lockups are verbatim.** A character lockup is pasted into prompts exactly as written.
   Paraphrasing a lockup recasts the character — treat any rewording as a canon change
   that needs user approval.
6. Raw generated clips are **never committed** (see `repo-layout.md`). Only the YAML,
   prompts, reference plates, and the final cut are versioned.

## Phase 0 — Setup / resume

Delegate to **`repo-layout.md`** for path resolution, config loading, and repo init.

Resolve the films repo from `~/.claude/filmcraft/config.yaml`. Pick an existing film slug
or create a new one. Load `film.yaml` + `bible/` + `shots.yaml`. The skill is fully
resumable from on-disk state — determine the last completed phase from `status` and what
is on disk, and continue without re-running completed phases.

## Phase 1 — Co-design (interactive)

Delegate to **`co-design.md`** for the full interactive protocol.

The Director works with the user through: logline → runtime target → genre/tone →
**look book** (film stock, lens package, lighting, palette, grade, negative terms) →
characters → locations → **audio strategy** → beat sheet. Writes `bible/look.yaml`,
`bible/casting.yaml`, and `bible/beats.md`.

Audio strategy is decided here, per film, and recorded as `audio_strategy` in `film.yaml`:
`native` (Grok's synchronized audio), `post` (silent generation, audio laid in during
assembly), or `hybrid`. See `co-design.md` for how to choose.

**Checkpoint:** the user approves the look book, casting, and beat sheet before any shot
is written. Do not proceed without it.

## Phase 2 — Casting & plates

Delegate to **`casting.md`**.

Before any shot is generated, lock a canonical reference for every character and location:
a **lockup** (the verbatim descriptor block) and a **plate** (the reference still). This is
the single highest-leverage step for continuity — every downstream shot either passes the
plate as a reference image or pastes the lockup verbatim.

**Checkpoint:** the user approves each plate. A rejected plate is regenerated before the
shot list depends on it.

## Phase 3 — Scene → shot list

Delegate to **`shot-grammar.md`** for film language and decomposition rules, and
**`personas.md`** for the crew briefs.

The crew decomposes each beat into shots, writing `shots.yaml`. Every shot carries one
action, one camera move, and dialogue that fits its clip length. The crew runs
concurrently; the Director adjudicates.

## Phase 4 — Validate & budget (deterministic gates)

Run `shot_check.py`, then `estimate_cost.py` (see Scripts). Blockers must be resolved
before generation — they are exactly the errors that would waste money.

**Checkpoint:** present the validation report and the cost estimate together. The user
approves the spend before anything is generated.

## Phase 5 — Generate

Run `generate.py` (see Scripts). With `XAI_API_KEY` set it submits, polls, downloads takes,
and appends to the spend ledger. Without a key it writes a paste-ready prompt packet
instead — the manual fallback.

Generate scene by scene, not all at once, so continuity QA can catch drift before it
propagates. `extend`-mode shots depend on their source shot's clip, so a scene's shots
generate in order.

## Phase 6 — Continuity QA

Delegate to **`continuity-qa.md`**.

Extract frames from the delivered takes and compare against the plates and against the
previous shot. The Script Supervisor flags drift: wrong face, wrong wardrobe, wrong
lighting state, wrong prop, crossed axis. Drifted shots are re-taken, not accepted.

**Checkpoint:** the user selects takes. Selections are recorded as `select:` in
`shots.yaml`.

## Phase 7 — Assemble

Run `assemble.py` (see Scripts). Trims each selected take to its edit points, conforms
everything to one format, concatenates in shot order, mixes an audio bed if present, and
emits a contact sheet. Commit the final cut and the contact sheet.

## Scripts

All scripts use PEP 723 inline deps and must be run via `uv run`. Paths below are relative
to the skill directory.

**Validate the shot list** (Phase 4, before any spend):

```
uv run scripts/shot_check.py <film_dir>
```

Reports dialogue that cannot fit its clip, 180-degree/screen-direction violations, jump-cut
risk, scenes with no establishing shot, unknown or dangling references, over-deep extension
chains, and runtime drift. Exits non-zero on any blocker.

**Estimate cost** (Phase 4, and any time before generating):

```
uv run scripts/estimate_cost.py <film_dir> [--ledger]
```

Projects spend from durations × takes × per-second rate. `--ledger` adds actual spend so
far, reconstructed from `generated/generation-log.jsonl`. Exits non-zero if the estimate
exceeds `budget_usd`.

**Generate** (Phase 5):

```
uv run scripts/generate.py <film_dir> [--shots s01-001,s01-002] [--packet] [--yes]
```

`--yes` is required to spend. `--packet` forces prompt-packet output even when a key is
present. Without `XAI_API_KEY` it falls back to packet mode automatically.

**Assemble** (Phase 7):

```
uv run scripts/assemble.py <film_dir> [--dry-run]
```

`--dry-run` prints the ffmpeg commands without running them — use it to inspect the edit,
or on a machine without ffmpeg installed.

**Tests:**

```
uv run --with pytest --with pyyaml python -m pytest scripts/tests/ -q
```

## Edge cases

- **No films repo configured** → resolve per `repo-layout.md`; offer to create and init it.
- **No `XAI_API_KEY`** → packet mode. Say so plainly; do not present packet output as
  generated film.
- **API parameter rejected at generation time** → the wire format is quarantined in
  `grok_client.build_payload`. Fix it there and in `grok-api.md`; do not scatter workarounds.
- **Estimate exceeds `budget_usd`** → hard stop. Offer to trim takes, shorten shots, or drop
  to 480p, and re-estimate. Never generate past the cap.
- **A shot fails to generate** → log the real error and continue with the rest; report which
  shots failed. Never substitute a placeholder clip silently.
- **Continuity drift found in QA** → re-take the drifted shot. If drift persists across
  takes, re-anchor with a fresh reference-mode shot instead of extending.
- **ffmpeg missing** → report it and suggest `--dry-run`; do not claim a build happened.
- **User asks for a feature-length film** → say plainly what it costs. At ~$0.07/sec, a
  90-minute film is 900+ shots and thousands of dollars of generation. Recommend proving a
  short first.
- **Shot list and bible disagree** → the bible is canon. Surface the discrepancy rather
  than silently patching either side.
