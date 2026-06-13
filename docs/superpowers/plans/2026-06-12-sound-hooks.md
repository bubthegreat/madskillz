# Sound Hooks (paplay) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Stop/Notification hooks in the madskillz plugin that play Windows system sounds from WSL2 via `paplay` — `tada.wav` when Claude finishes a turn, `Alarm01.wav` when Claude needs the user.

**Architecture:** A single parametrized bash script (`play-sound.sh`) takes a wav filename, drains the hook's stdin JSON, and plays `/mnt/c/Windows/Media/<wav>` backgrounded via `paplay`, always exiting 0. A plugin `hooks/hooks.json` maps `Stop`→tada and `Notification`→Alarm01 using `${CLAUDE_PLUGIN_ROOT}`. Deployed globally through the madskillz marketplace plugin (version bump + marketplace update).

**Tech Stack:** bash, `paplay` (PulseAudio/WSLg), Claude Code plugin hooks (`hooks/hooks.json`, auto-discovered).

Spec: `docs/superpowers/specs/2026-06-12-sound-hooks-design.md`

**Notes for the implementer:**
- This is a WSL2 machine. `paplay` is at `/usr/bin/paplay`; WSLg PulseAudio sink (`RDPSink`) is active; Windows sounds live at `/mnt/c/Windows/Media/*.wav`. All verified.
- A hook command must NEVER block the turn or emit a nonzero exit / stderr into the session. `play-sound.sh` backgrounds playback and always exits 0.
- Plugin hooks are auto-discovered from `hooks/hooks.json` at the plugin root; `plugin.json` does NOT need to reference them (superpowers/ralph-loop/hookify prove this).

---

### Task 1: Write `play-sound.sh` with a test (TDD)

**Files:**
- Create: `plugins/madskillz/hooks/play-sound.sh`
- Test: `plugins/madskillz/hooks/play-sound.test.sh`

- [ ] **Step 1: Write the failing test**

Create `plugins/madskillz/hooks/play-sound.test.sh`:

```bash
#!/usr/bin/env bash
# Test play-sound.sh: correct paplay invocation, stdin drain, always exit 0,
# graceful no-op when paplay is absent. Uses a fake paplay on PATH so no audio plays.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUT="$HERE/play-sound.sh"
fail() { echo "FAIL: $1"; exit 1; }

# --- Fixture: fake paplay that logs its args ---
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
LOG="$TMP/paplay.log"
cat >"$TMP/paplay" <<EOF
#!/usr/bin/env bash
echo "\$@" >>"$LOG"
EOF
chmod +x "$TMP/paplay"

# --- Test 1: plays the right file, drains stdin, exits 0 ---
echo '{"hook_event_name":"Stop"}' | PATH="$TMP:$PATH" bash "$SUT" tada.wav
rc=$?
[ "$rc" -eq 0 ] || fail "expected exit 0 with paplay present, got $rc"
sleep 0.3   # playback is backgrounded; wait for the fake to write
grep -q "/mnt/c/Windows/Media/tada.wav" "$LOG" || fail "paplay not called with tada.wav path (log: $(cat "$LOG"))"

# --- Test 2: no paplay on PATH -> still exit 0, no crash ---
echo '{}' | PATH="$TMP/none" bash "$SUT" Alarm01.wav
rc=$?
[ "$rc" -eq 0 ] || fail "expected exit 0 when paplay absent, got $rc"

# --- Test 3: no wav arg -> exit 0, no paplay call ---
: >"$LOG"
echo '{}' | PATH="$TMP:$PATH" bash "$SUT"
rc=$?
[ "$rc" -eq 0 ] || fail "expected exit 0 with no arg, got $rc"
sleep 0.1
[ ! -s "$LOG" ] || fail "paplay should not run with no wav arg (log: $(cat "$LOG"))"

echo "PASS"
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `bash plugins/madskillz/hooks/play-sound.test.sh`
Expected: nonzero exit, output `FAIL: ...` or a `No such file` error (the SUT does not exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `plugins/madskillz/hooks/play-sound.sh`:

```bash
#!/usr/bin/env bash
# madskillz sound hook: play a Windows system sound from WSL2 via WSLg PulseAudio.
# Arg 1: wav filename under /mnt/c/Windows/Media (e.g. tada.wav).
# Drains the hook's stdin JSON (does not parse it). Never blocks, never errors.
cat >/dev/null 2>&1   # drain stdin (hook event JSON), ignore contents

wav="${1:-}"
[ -n "$wav" ] || exit 0
command -v paplay >/dev/null 2>&1 || exit 0

paplay "/mnt/c/Windows/Media/${wav}" >/dev/null 2>&1 &
exit 0
```

- [ ] **Step 4: Make it executable**

Run: `chmod +x plugins/madskillz/hooks/play-sound.sh plugins/madskillz/hooks/play-sound.test.sh`

- [ ] **Step 5: Run the test, verify it passes**

Run: `bash plugins/madskillz/hooks/play-sound.test.sh`
Expected: `PASS`, exit 0.

- [ ] **Step 6: Real audio smoke check (optional, manual)**

Run: `echo '{}' | bash plugins/madskillz/hooks/play-sound.sh tada.wav`
Expected: exit 0; the tada sound plays through the speakers.

- [ ] **Step 7: Commit**

```bash
git add plugins/madskillz/hooks/play-sound.sh plugins/madskillz/hooks/play-sound.test.sh
git commit -m "feat: add play-sound.sh hook script for madskillz"
```

---

### Task 2: Register the hooks in `hooks/hooks.json`

**Files:**
- Create: `plugins/madskillz/hooks/hooks.json`

- [ ] **Step 1: Write the hooks config**

Create `plugins/madskillz/hooks/hooks.json`:

```json
{
  "description": "madskillz sound cues: tada when Claude finishes, Alarm01 when Claude needs you",
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/play-sound.sh\" tada.wav"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/play-sound.sh\" Alarm01.wav"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python3 -c "import json,sys; json.load(open('plugins/madskillz/hooks/hooks.json'))" && echo OK`
Expected: `OK` (no traceback).

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/hooks/hooks.json
git commit -m "feat: register Stop/Notification sound hooks in madskillz plugin"
```

---

### Task 3: Bump version, deploy, verify

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json` (version `0.2.0` → `0.3.0`)

- [ ] **Step 1: Bump the plugin version**

In `plugins/madskillz/.claude-plugin/plugin.json`, change `"version": "0.2.0"` to `"version": "0.3.0"`.

Result:

```json
{
  "name": "madskillz",
  "description": "Bub's personal skills bundle",
  "version": "0.3.0",
  "author": { "name": "Bub Taylor", "email": "bubthegreat@gmail.com" }
}
```

- [ ] **Step 2: Commit and push**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore: bump madskillz plugin to 0.3.0 (adds sound hooks)"
git push
```

- [ ] **Step 3: Refresh the marketplace cache**

Run: `claude plugin marketplace update madskillz`
Expected: "Successfully updated"; installed plugin auto-updates 0.2.0 → 0.3.0.

- [ ] **Step 4: Verify the hooks shipped to the cache**

Run: `ls ~/.claude/plugins/cache/madskillz/madskillz/*/hooks/`
Expected: `hooks.json` and `play-sound.sh` listed.

- [ ] **Step 5: Verify a new session merges the hooks**

Run: `cd /tmp && claude -p "Run /hooks and tell me: is there a Stop hook and a Notification hook from the madskillz plugin? yes/no for each."`
Expected: yes for both. (If `/hooks` is not introspectable via `-p`, instead inspect the cached `hooks.json` from Step 4 and confirm Claude Code logged no hook-load errors at startup.)

- [ ] **Step 6: Functional test (manual, interactive session)**

In a fresh interactive `claude` session: finish a turn → hear `tada`. Trigger a permission prompt (e.g. ask Claude to run a command that needs approval) → hear `Alarm01`.
Expected: both sounds fire on the right events; no added latency or errors.

---

## Self-Review (completed)

- **Spec coverage:** Event mapping (Stop/Notification) → Task 2. `play-sound.sh` behavior, stdin drain, exit-0/guards, backgrounding → Task 1. Version bump + deploy + discovery verification → Task 3. Error-handling spec points (missing paplay, missing wav, no stderr) → Task 1 tests 2 & 3 plus the implementation's guards and `2>/dev/null`. All spec sections covered.
- **Placeholder scan:** No TBD/TODO; all code shown in full; commands have expected output.
- **Type/name consistency:** Script name `play-sound.sh`, arg = wav filename, path prefix `/mnt/c/Windows/Media/` consistent across Task 1 impl, Task 1 tests, and Task 2 hooks.json. `${CLAUDE_PLUGIN_ROOT}/hooks/play-sound.sh` matches the created file location.
