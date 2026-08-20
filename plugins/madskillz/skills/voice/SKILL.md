---
name: voice
description: >-
  Owns the owner's voice: a core "how I talk and think" profile plus per-context overlays (blog,
  research, chat, storycraft) and the voicectl CLI that captures, renders, updates, and syncs
  them. Use to get the owner's voice for any writing ("render my voice", "write as me"), to
  refresh the profile from how they actually write ("update my voice"), to mint a new context
  voice, or to install the capture/sync pipeline on a machine.
---

# voice: one core, many registers

The owner's voice lives in two layers:

- **Core** (`references/voices/core.md`) - identity, the descriptive layer (observed traits,
  tagged keep/tone-down), the register-independent AI-tells, and the provenance markers.
- **Overlays** (`references/voices/<context>.md`, `extends: core`) - thin prescriptive deltas
  for one medium: `blog`, `research`, `chat`, `storycraft`.

A writer never reads these separately: `voicectl render <context>` deterministically merges the
overlay's prescriptive layer with the core into one doc. Live working copies sit in
`~/.madskillz/voice/` (same filenames); the committed copies here are what non-local agents and
fresh machines seed from.

## Getting the voice (any consumer skill)

```
voicectl render blog          # or research / chat / storycraft; -o FILE to save
```

If `voicectl` is missing, run `scripts/install_voice_pipeline.sh` first (once per machine).
Never read an overlay alone as "the voice," and never present a template as the owner.

## Updating the voice ("update my voice")

The CLI does everything deterministic; the model only judges traits:

1. `voicectl update-prep` - emits JSON: the new corpus entries since `Processed through` plus
   the path of the live core.
2. Judge per `references/voice-update.md`: is anything **genuinely new** about how the owner
   writes? Merge real findings into the live core's descriptive sections (write the full
   revised core to a temp file). A no-change pass is valid: skip to step 4.
3. `voicectl update-apply <tempfile>` - validates and installs it atomically, bumping the
   marker.
4. `voicectl sync` - materiality-gated: pushes the live profiles to the committed library on
   `main` via the dedicated sync clone when the delta is material, otherwise does nothing.

`voicectl status --json` shows markers, pending counts, and the materiality verdict.

## Minting a new context voice

Copy `references/voice-overlay-template.md` to `references/voices/<name>.md`, set the
frontmatter (`extends: core`, `status: personal`), and write only the prescriptive rules for
that medium - the descriptive layer always comes from core. Seed the live copy with
`voicectl init`. The first commit of a new overlay is explicit and owner-reviewed, never an
auto-sync.

## Machine setup (once)

`bash scripts/install_voice_pipeline.sh` - idempotent. Creates `~/.madskillz/voice/`, seeds
live profiles from the committed voices, installs the `voicectl` uv tool, wires the
UserPromptSubmit capture hook and SessionEnd gate hook into `~/.claude/settings.json` (via the
shims in `hooks/`), and creates the dedicated main-pinned sync clone. Then fold in existing
local history: `voicectl backfill`.

## Integrity stance (non-negotiable)

1. **Observed, never invented.** Every descriptive trait traces to real owner messages; a pass
   that finds nothing new changes nothing.
2. **Descriptive vs prescriptive.** Capturing a tic as a tendency is not licensing it in prose;
   when the two conflict for published writing, prescriptive wins.
3. **AI-tells are register-independent.** They live in core and apply to every artifact written
   as the owner.
4. **The voice never bends the substance.** Correctness outranks every stylistic move.

## Edge cases

- "Update my voice" with nothing new in the corpus: say so; change nothing.
- Unknown render context: `voicectl render` lists the available ones; ask, don't guess.
- Sync clone missing/offline: `voicectl sync` fails loudly; live profiles stay authoritative.
- Blog posts themselves are written by the `blog` skill; this skill only owns the voice.
