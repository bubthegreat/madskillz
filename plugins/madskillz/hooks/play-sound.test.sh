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

# --- Fixture: a PATH dir with the script's real deps but NO paplay ---
mkdir -p "$TMP/none"
ln -s "$(command -v bash)" "$TMP/none/bash"
ln -s "$(command -v cat)"  "$TMP/none/cat"

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
