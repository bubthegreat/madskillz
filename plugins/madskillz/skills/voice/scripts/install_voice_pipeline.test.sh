#!/usr/bin/env bash
# Sandboxed test for install_voice_pipeline.sh: fresh install then idempotent re-run.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

export VOICE_DIR="$tmp/voice" CLAUDE_DIR="$tmp/claude"
export VOICE_INSTALL_NO_CLONE=1 VOICE_INSTALL_NO_TOOL=1

fail() { echo "FAIL: $*"; exit 1; }

out1="$(bash "$here/install_voice_pipeline.sh")"
[ -f "$VOICE_DIR/core.md" ] || fail "core.md not seeded"
[ -f "$VOICE_DIR/blog.md" ] || fail "blog.md not seeded"
[ -x "$CLAUDE_DIR/hooks/capture-voice.sh" ] || fail "capture hook missing"
[ -x "$CLAUDE_DIR/hooks/voice-sync-gate.sh" ] || fail "gate hook missing"
grep -q "capture-voice.sh" "$CLAUDE_DIR/settings.json" || fail "UserPromptSubmit not wired"
grep -q "voice-sync-gate.sh" "$CLAUDE_DIR/settings.json" || fail "SessionEnd not wired"

# seeded live profile must never be overwritten
echo "LOCAL EDIT" >> "$VOICE_DIR/core.md"
out2="$(bash "$here/install_voice_pipeline.sh")"
grep -q "LOCAL EDIT" "$VOICE_DIR/core.md" || fail "re-run clobbered live core.md"
echo "$out2" | grep -q "0 change(s)" || fail "re-run was not a no-op: $out2"

# settings wiring must not duplicate
n="$(grep -c "capture-voice.sh" "$CLAUDE_DIR/settings.json")"
[ "$n" -eq 1 ] || fail "duplicate capture hook wiring ($n)"

echo "PASS: install_voice_pipeline.test.sh"
