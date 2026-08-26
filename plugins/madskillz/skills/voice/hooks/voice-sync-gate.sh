#!/usr/bin/env bash
# madskillz voice-sync gate hook (SessionEnd) - thin shim over `voicectl gate`.
# The cheap tier of the two-tier materiality check: when enough new corpus messages have
# accumulated, voicectl detaches a headless "update my voice" agent. Tunables are `voicectl
# config` keys (model, minCount, minInterval) plus the env overrides
# VOICE_SYNC_LOCK_STALE_SECONDS and VOICE_SYNC_LAUNCH - see voicectl's gate module.
# Contract: never blocks session teardown, never errors (always exit 0), emits nothing to stdout.
cat >/dev/null 2>&1   # drain the SessionEnd event JSON
PATH="$HOME/.local/bin:$PATH"
command -v voicectl >/dev/null 2>&1 && voicectl gate >/dev/null 2>&1
exit 0
