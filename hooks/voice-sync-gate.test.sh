#!/usr/bin/env bash
# Tests for voice-sync-gate.sh — exercises the gate's launch decision without spawning a real
# agent, via the VOICE_SYNC_LAUNCH override (which the gate runs synchronously instead of detaching).
# Run: bash hooks/voice-sync-gate.test.sh   (exit 0 = all pass)
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/voice-sync-gate.sh"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); printf '  ok   - %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL - %s\n' "$1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (want '$3', got '$2')"; fi; }

# Build a throwaway voice dir with a profile (marker) + a corpus of N entries after the marker.
# Usage: setup <num_entries>
setup() {
  TMP="$(mktemp -d)"
  MARKER="2026-01-01T00:00:00Z"
  printf 'Repo-synced through: %s\n' "$MARKER" > "$TMP/voice.md"
  : > "$TMP/corpus.jsonl"
  local i=0
  while [ "$i" -lt "$1" ]; do
    # ts strictly after the marker so it counts as "new"
    printf '{"ts": "2026-02-01T00:%02d:00Z", "text": "msg %d"}\n' "$((i % 60))" "$i" >> "$TMP/corpus.jsonl"
    i=$((i+1))
  done
  SENTINEL="$TMP/launched"
}

run_gate() { ( cd "$TMP" && env VOICE_DIR="$TMP" VOICE_SYNC_LAUNCH="touch '$SENTINEL'" "$@" bash "$GATE" </dev/null ); }
launched() { [ -f "$SENTINEL" ] && echo yes || echo no; }

echo "voice-sync-gate tests"

# 1) Below threshold → no launch.
setup 14
run_gate VOICE_SYNC_MIN_COUNT=15 VOICE_SYNC_MIN_INTERVAL_SECONDS=0
check "below threshold does not launch" "$(launched)" "no"
rm -rf "$TMP"

# 2) At threshold → launch, lock released, attempt stamp written.
setup 15
run_gate VOICE_SYNC_MIN_COUNT=15 VOICE_SYNC_MIN_INTERVAL_SECONDS=0
check "at threshold launches"            "$(launched)" "yes"
check "lock released after launch"       "$([ -f "$TMP/.sync.lock" ] && echo present || echo gone)" "gone"
check "attempt stamp written"            "$([ -f "$TMP/.last-sync-attempt" ] && echo yes || echo no)" "yes"
rm -rf "$TMP"

# 3) Above threshold → launch.
setup 40
run_gate VOICE_SYNC_MIN_COUNT=15 VOICE_SYNC_MIN_INTERVAL_SECONDS=0
check "above threshold launches"         "$(launched)" "yes"
rm -rf "$TMP"

# 4) Throttle: fresh attempt stamp blocks a launch even when count is high.
setup 40
touch "$TMP/.last-sync-attempt"   # "just attempted"
run_gate VOICE_SYNC_MIN_COUNT=15 VOICE_SYNC_MIN_INTERVAL_SECONDS=720
check "throttle blocks recent re-launch" "$(launched)" "no"
rm -rf "$TMP"

# 5) Fresh lock blocks a launch (sync already running).
setup 40
touch "$TMP/.sync.lock"
run_gate VOICE_SYNC_MIN_COUNT=15 VOICE_SYNC_MIN_INTERVAL_SECONDS=0 VOICE_SYNC_LOCK_STALE_SECONDS=1800
check "fresh lock blocks launch"         "$(launched)" "no"
rm -rf "$TMP"

# 6) Stale lock is cleared and launch proceeds (stale-window 0 => any existing lock is dead).
setup 40
touch "$TMP/.sync.lock"
run_gate VOICE_SYNC_MIN_COUNT=15 VOICE_SYNC_MIN_INTERVAL_SECONDS=0 VOICE_SYNC_LOCK_STALE_SECONDS=0
check "stale lock cleared, launches"     "$(launched)" "yes"
rm -rf "$TMP"

# 7) Marker respected: entries at/older than the marker don't count.
setup 0
printf '{"ts": "2025-06-01T00:00:00Z", "text": "old, before marker"}\n' >> "$TMP/corpus.jsonl"  # before marker
i=0; while [ "$i" -lt 5 ]; do printf '{"ts": "2026-03-01T00:0%d:00Z", "text": "new %d"}\n' "$i" "$i" >> "$TMP/corpus.jsonl"; i=$((i+1)); done
run_gate VOICE_SYNC_MIN_COUNT=15 VOICE_SYNC_MIN_INTERVAL_SECONDS=0
check "only-5-new (1 old ignored) no launch" "$(launched)" "no"
rm -rf "$TMP"

echo
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
