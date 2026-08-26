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
overlay's prescriptive layer with the core into one doc. The live copies live in the user's
**voice store** - `~/.madskillz/voice/`, a clone of a private git repo the user owns - so every
machine converges on one core, one overlay set, one corpus. This skill ships only templates;
nobody's real profile is in the plugin.

## Getting the voice (any consumer skill)

```
voicectl render blog          # or research / chat / storycraft; -o FILE to save
```

If `voicectl` is missing, run `scripts/install_voice_pipeline.sh` first (once per machine).
Never read an overlay alone as "the voice," and never present a template as the owner.

## Updating the voice ("update my voice")

The CLI does everything deterministic; the model only judges traits:

1. `voicectl update-prep` - emits JSON: the new corpus entries since `Processed through` plus
   the path of the live core. `update-prep` pulls first; a `pull: conflict-remote-kept` result
   means another machine updated concurrently - the remote core is now the base, continue
   normally.
2. Judge per `references/voice-update.md`: is anything **genuinely new** about how the owner
   writes? Merge real findings into the live core's descriptive sections (write the full
   revised core to a temp file). A no-change pass is valid: apply the unchanged core anyway so
   the marker advances.
3. `voicectl update-apply <tempfile>` - validates and installs it atomically, bumping the
   marker.
4. `update-apply` pushes to the voice store on its own. If it reports `push failed`, run
   `voicectl sync` when back online; the local apply stands.

`voicectl status --json` shows mode, remote, markers, pending count, and config.

## Minting a new context voice

Copy `references/voice-overlay-template.md` to `~/.madskillz/voice/<name>.md`, set the
frontmatter (`extends: core`, `status: personal`), and write only the prescriptive rules for
that medium - the descriptive layer always comes from core. `voicectl push` when the owner has
reviewed it.

## Setting up a machine ("set up my voice")

Run `bash scripts/install_voice_pipeline.sh` once (installs `voicectl`, the hooks, and
templates). Then wire the voice store. The user never needs the flags; walk them through this:

1. `voicectl status --json`. If `mode` is `synced`, done - report `remote` and `contexts`.
2. Ask one question: **Where should your voice live?**
   - **Existing repo** - they paste a URL or `owner/name`.
   - **Create one for me** - default `<github-user>/voice` (`gh api user -q .login`).
   - **Local only** - no sync; say plainly that other machines will not see this voice.
3. Resolve `owner/name` to a URL: `git@github.com:owner/name.git` if `ssh -T git@github.com`
   succeeds, else `https://github.com/owner/name.git`.
4. `voicectl init --remote URL`. Exit 3 with a `refused:` line means one of:
   - `remote not found` - re-run with `--create` (github + `gh` only; other hosts: the user
     creates the repo, then re-run).
   - `is PUBLIC` - the corpus holds verbatim prompts. Offer `gh repo edit owner/name
     --visibility private --accept-visibility-change-consequences`, or `--allow-public` if
     the user insists.
   - `not a voice store` - the repo has other content. Ask for another repo.
5. `voicectl backfill`, then `voicectl push`.
6. Report `voicectl status`: `remote`, `mode`, corpus line count, `contexts`.

**Second machine:** same flow. Step 4 finds the existing store and clones it; if this machine
already had a local-only voice dir, `init` backs it up to `~/.madskillz/voice.bak-<ts>`, keeps
the remote profiles, and folds the local corpus in. Nothing is lost.

Per-machine tunables: `voicectl config` (`model`, `minCount`, `minInterval`, `corpusSync`).
`corpusSync=false` is reserved and not enforced yet; the corpus is always pushed.

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
- Offline: `update-prep` says `pull: offline` and works from the local core; `update-apply`
  applies locally and reports the unpushed state. `voicectl sync` later.
- Blog posts themselves are written by the `blog` skill; this skill only owns the voice.
