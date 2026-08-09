# Repo layout & config resolution

## Config resolution

Read `~/.claude/filmcraft/config.yaml` for:

```yaml
films_repo: ~/films     # path to the user's films git repo
director: <name>
```

If the file is missing or `films_repo` is unset, prompt the user for the path and offer to
`git init` it. Record the chosen path back into the config file. Never hardcode a path or
owner; this skill is usable by anyone.

## Per-film layout

Each film occupies one folder inside the films repo. `<film-slug>` is kebab-case.

```
<films-repo>/
  .gitignore             # MUST ignore generated/ and build/conformed/ — see below
  <film-slug>/
    film.yaml            # metadata + generation parameters
    shots.yaml           # the shot list — the core artifact
    bible/
      look.yaml          # film stock, lens, lighting, palette, grade, negative terms
      casting.yaml       # character lockups + plates, locations, voices
      beats.md           # beat sheet / scene breakdown
      plates/            # committed — reference stills are small and load-bearing
        elena-03.png
      voices/            # committed if small; git-lfs if not
    packet/              # generated prompt files (packet mode) — committed, they are text
    generated/           # RAW TAKES — GITIGNORED, never committed
      s01-001_t01.mp4
      generation-log.jsonl   # committed — the spend ledger is a record
    audio/
      bed.wav            # optional music/VO bed, mixed at assembly
    build/
      conformed/         # intermediate trims — gitignored
      <film-slug>.mp4    # the final cut — git-lfs, or left out entirely
      <film-slug>-contact-sheet.png
    notes/
      checkpoints.md     # log of user approvals, redirects, and take selections
```

Omit any subfolder that has no content. Never create empty placeholders.

## What is and is not committed

This is the one place filmcraft deliberately breaks from `storycraft`, which commits its
EPUB and PDF build artifacts. Video is three orders of magnitude larger: 50 clips at 720p
is roughly 500 MB–1 GB, and takes multiply that. Committing raw takes will wreck the repo.

| Path | Committed? | Why |
|---|---|---|
| `film.yaml`, `shots.yaml`, `bible/**` | Yes | Text, small, the actual source of the film |
| `packet/**` | Yes | Text prompts; the reproducible record of what was asked for |
| `bible/plates/**` | Yes | Small stills, and continuity depends on them |
| `generated/generation-log.jsonl` | Yes | The spend ledger |
| `generated/*.mp4` | **No — gitignore** | Raw takes, large, regenerable |
| `build/conformed/**` | **No — gitignore** | Intermediates |
| `build/<slug>.mp4` | git-lfs, or not at all | Ask the user; do not silently commit a large binary |

Write this `.gitignore` at the repo root on init:

```
generated/*.mp4
generated/*.mov
build/conformed/
```

If the user wants the final cut versioned, confirm git-lfs is configured before adding it.
If it is not, say so and leave the cut untracked rather than bloating the repo.

## `film.yaml` fields

| Key | Description |
|---|---|
| `title` | Film title |
| `slug` | Kebab-case folder name |
| `logline` | One-sentence premise |
| `director` | From config unless overridden |
| `target_runtime_seconds` | Planned cut length |
| `resolution` | `480p` \| `720p` \| `1080p` |
| `aspect_ratio` | e.g. `"16:9"` — verify support per `grok-api.md` |
| `fps` / `width` / `height` | Conform target for assembly |
| `model` | e.g. `grok-imagine-video-1.5` |
| `takes` | Default takes per shot |
| `audio_strategy` | `native` \| `post` \| `hybrid` |
| `budget_usd` | Hard spend cap — generation refuses to exceed it |
| `max_clip_seconds` | Model's clip ceiling (15 for 1.5) |
| `max_extend_chain` | Max extension hops before re-anchoring |
| `video_rates` | Optional per-resolution rate overrides |
| `status` | `co-design` \| `casting` \| `shot-list` \| `generating` \| `qa` \| `assembling` \| `done` |

## `shots.yaml` schema

```yaml
shots:
  - id: s02-004          # sNN-NNN; scene number must match `scene`
    scene: 2
    beat: "Elena realizes the pendant is a fake"
    location: study      # key into bible/casting.yaml locations
    mode: reference      # text | image | reference | extend
    extend_from: s02-003 # required when mode: extend
    refs:
      characters: [elena]
      voice: elena_vo
    size: MCU            # EWS WS MWS MS MCU CU ECU
    angle: eye           # eye low high dutch overhead worm
    move: slow push in
    screen_dir: L→R      # L→R | R→L | neutral | to-cam | from-cam
    axis_break: false    # true = crossing the 180° line on purpose
    duration: 8          # generation length, 1–15
    edit_in: 1.5         # cut points inside the generated clip
    edit_out: 4.7
    speaker: ELENA
    dialogue: "This isn't hers. It was never hers."
    prompt_extra: "rain-streaked window behind, practical lamp key from camera-left"
    takes: 3
    select: s02-004_t02.mp4   # set during QA
```

## Naming rules

- `<film-slug>`: kebab-case — lowercase letters, digits, hyphens. Validate before writing.
- Shot ids: `sNN-NNN`, zero-padded, scene-prefixed. `shot_check.py` enforces this.
- Takes on disk: `<shot-id>_t<NN>.mp4`. `assemble.py` globs this; deviating breaks the cut.

## Commit/push rule

Commit at each checkpoint with messages of the form `film: <slug> <what>`:

```
film: pendant look book v1
film: pendant casting plates
film: pendant shots s01
film: pendant cut v1
```

Never push. The user pushes manually.
