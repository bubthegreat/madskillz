#!/usr/bin/env bash
# madskillz voice-sync gate hook (SessionEnd) - thin shim over `voicectl gate`.
# The cheap tier of the two-tier materiality check: when enough new corpus messages have
# accumulated, voicectl detaches a headless "update my voice" agent. Tunables are env vars
# (VOICE_SYNC_MIN_COUNT, VOICE_SYNC_MIN_INTERVAL_SECONDS, VOICE_SYNC_LOCK_STALE_SECONDS,
# VOICE_SYNC_MODEL, VOICE_SYNC_REPO, VOICE_SYNC_BRANCH, VOICE_SYNC_AUTOREFRESH,
# VOICE_SYNC_LAUNCH) - see voicectl's gate module. Contract: never blocks session teardown,
# never errors (always exit 0), emits nothing to stdout.
cat >/dev/null 2>&1   # drain the SessionEnd event JSON
command -v voicectl >/dev/null 2>&1 && voicectl gate >/dev/null 2>&1
exit 0
