#!/usr/bin/env bash
# Sandboxed test for install_voice_pipeline.sh: hooks + settings wiring, idempotent re-run,
# and the old gate command gets rewritten. Store init is exercised by the pytest suite.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

export VOICE_DIR="$tmp/voice" CLAUDE_DIR="$tmp/claude"
export VOICE_INSTALL_NO_TOOL=1 VOICE_INSTALL_NO_INIT=1

fail() { echo "FAIL: $*"; exit 1; }

mkdir -p "$CLAUDE_DIR"
cat > "$CLAUDE_DIR/settings.json" <<'JSON'
{"hooks": {"SessionEnd": [{"hooks": [{"type": "command",
 "command": "VOICE_SYNC_REPO=\"$HOME/.madskillz/voice/madskillz-sync\" VOICE_SYNC_AUTOREFRESH=1 bash \"$HOME/.claude/hooks/voice-sync-gate.sh\"", "timeout": 10}]}]}}
JSON

out1="$(bash "$here/install_voice_pipeline.sh")"
[ -x "$CLAUDE_DIR/hooks/capture-voice.sh" ] || fail "capture hook missing"
[ -x "$CLAUDE_DIR/hooks/voice-sync-gate.sh" ] || fail "gate hook missing"
grep -q "capture-voice.sh" "$CLAUDE_DIR/settings.json" || fail "UserPromptSubmit not wired"
grep -q "VOICE_SYNC_REPO" "$CLAUDE_DIR/settings.json" && fail "old gate command not rewritten"
echo "$out1" | grep -q "SessionEnd:rewritten" || fail "expected rewrite notice: $out1"

out2="$(bash "$here/install_voice_pipeline.sh")"
echo "$out2" | grep -q "0 change(s)" || fail "re-run was not a no-op: $out2"
n="$(grep -c "capture-voice.sh" "$CLAUDE_DIR/settings.json")"
[ "$n" -eq 1 ] || fail "duplicate capture hook wiring ($n)"

echo "PASS: install_voice_pipeline.test.sh"
