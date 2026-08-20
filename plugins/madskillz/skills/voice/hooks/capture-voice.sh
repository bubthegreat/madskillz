#!/usr/bin/env bash
# madskillz voice-capture hook (UserPromptSubmit) - thin shim over `voicectl capture`.
# Appends the owner's prompt to ~/.madskillz/voice/corpus.jsonl. Contract: never blocks the
# prompt, never errors (always exit 0), emits nothing to stdout.
if command -v voicectl >/dev/null 2>&1; then
  voicectl capture >/dev/null 2>&1
else
  cat >/dev/null 2>&1   # drain stdin; capture silently unavailable until voicectl installed
fi
exit 0
