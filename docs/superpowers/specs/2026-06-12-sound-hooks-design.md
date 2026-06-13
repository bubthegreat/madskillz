# Sound Hooks (paplay) — Design Spec

**Date:** 2026-06-12
**Status:** Approved
**Deploy vehicle:** madskillz plugin (global via marketplace)

## Goal

Play a Windows system sound when Claude Code finishes a turn (a "done" cue) and a
different, more insistent sound when Claude is waiting on the user for permission or
input (a "needs you" cue). Applied globally on this WSL2 machine through the madskillz
plugin so it deploys and versions the same way as the skills.

## Environment facts (verified)

- WSL2 with WSLg present; PulseAudio RDP sink active (`PULSE_SERVER=unix:/mnt/wslg/PulseServer`, `Default Sink: RDPSink`).
- `paplay` installed at `/usr/bin/paplay`; plays `.wav` directly through WSLg to Windows audio.
- Windows system sounds available on the mounted C drive at `/mnt/c/Windows/Media/*.wav`.
- `paplay /mnt/c/Windows/Media/tada.wav` and `.../Alarm01.wav` both played, exit 0 (smoke-tested).
- Claude Code plugins auto-discover `hooks/hooks.json` at the plugin root; commands use `${CLAUDE_PLUGIN_ROOT}`. Confirmed by superpowers/ralph-loop/hookify plugins, none of which reference hooks from `plugin.json`.

## Event mapping

| Event | When it fires | Sound |
|---|---|---|
| `Stop` | Claude finishes responding (turn end) | `tada.wav` |
| `Notification` | Claude needs permission or has been idle waiting for input | `Alarm01.wav` |

No `SubagentStop` (would be noisy). No per-event branching on the hook's stdin JSON —
each event maps to one fixed sound. The stdin JSON is drained and ignored.

## Architecture

madskillz plugin gains a `hooks/` directory. Two events map to one parametrized script.

### Components

1. **`plugins/madskillz/hooks/play-sound.sh`**
   - Argument: a wav filename (e.g. `tada.wav`), resolved under `/mnt/c/Windows/Media/`.
   - Drains stdin (the hook event JSON) so the upstream process never blocks on a full pipe; does not parse or branch on it.
   - Plays `paplay /mnt/c/Windows/Media/<wav>` **backgrounded** (`&`), with stderr redirected to `/dev/null`.
   - **Always exits 0**, immediately. A hook must never block the turn or surface an error into the session.
   - Guard: if `paplay` is not on `PATH`, exit 0 silently (no sound, no error).

2. **`plugins/madskillz/hooks/hooks.json`**
   - `Stop` → `bash "${CLAUDE_PLUGIN_ROOT}/hooks/play-sound.sh" tada.wav`
   - `Notification` → `bash "${CLAUDE_PLUGIN_ROOT}/hooks/play-sound.sh" Alarm01.wav`

3. **`plugins/madskillz/.claude-plugin/plugin.json`**
   - Version bump `0.2.0` → `0.3.0`.

### Data flow

- Turn ends → `Stop` event → Claude Code runs the plugin Stop hook → `play-sound.sh tada.wav` → `paplay` backgrounded → script returns exit 0 instantly.
- Claude needs permission/input → `Notification` event → `play-sound.sh Alarm01.wav` → exit 0.

## Error handling

- Missing sink / missing `paplay` / missing wav file → script still exits 0, no stderr noise (paplay stderr → `/dev/null`, missing-paplay guard).
- Backgrounding `paplay` guarantees zero added turn latency; the script does not wait for playback.

## Testing

- **Unit (manual):** run `play-sound.sh tada.wav` directly with a piped JSON stub on stdin → exit 0, sound plays; run with `paplay` masked → exit 0, no error.
- **Integration (post-deploy):** finish a turn → hear tada; trigger a permission prompt → hear Alarm01.
- **Discovery:** after `claude plugin marketplace update madskillz`, confirm the cache contains `hooks/hooks.json`; confirm a new session merges the Stop/Notification hooks.

## Deployment

1. Add `hooks/play-sound.sh` (+x) and `hooks/hooks.json`.
2. Bump `plugin.json` to `0.3.0`.
3. Commit, push.
4. `claude plugin marketplace update madskillz` (auto-updates installed version).
5. Verify cache has `hooks/hooks.json`; new session loads hooks; functional test both sounds.

## Known tradeoff

`Stop` fires at every turn end, so tada plays after every reply, including one-liners.
This is "sound when finished" as requested. Easily reverted later by removing the `Stop`
entry from `hooks.json`. Recorded as a deliberate choice, not a surprise.

## Out of scope (YAGNI)

- Env-var or config-file customization of sound choices (edit `hooks.json` to change).
- Per-event branching on hook stdin JSON.
- `SubagentStop` sound.
- Volume control / playback throttling / debounce.
