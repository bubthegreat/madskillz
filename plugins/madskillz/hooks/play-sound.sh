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
