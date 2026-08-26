#!/usr/bin/env bash
# Sandboxed test for install_voice_pipeline.sh: hooks + settings wiring, idempotent re-run,
# targeted VOICE_SYNC_ dead-var rewrite (custom vars survive), duplicate-entry WARN reporting,
# and the old sync-clone gate command gets rewritten. Store init/backfill/push change-counting
# is exercised by the pytest suite; see task report for how the string parsing was verified
# against voicectl's real output.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fail() { echo "FAIL: $*"; exit 1; }

get_command() {
  # $1 = settings.json path, prints the first SessionEnd hook's command
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["hooks"]["SessionEnd"][0]["hooks"][0]["command"])' "$1"
}

# --- scenario 1: stale sync-clone command is rewritten to the plain command; idempotent re-run
c1="$tmp/claude1"
mkdir -p "$c1"
cat > "$c1/settings.json" <<'JSON'
{"hooks": {"SessionEnd": [{"hooks": [{"type": "command",
 "command": "VOICE_SYNC_REPO=\"$HOME/.madskillz/voice/madskillz-sync\" VOICE_SYNC_AUTOREFRESH=1 bash \"$HOME/.claude/hooks/voice-sync-gate.sh\"", "timeout": 10}]}]}}
JSON

out1="$(VOICE_DIR="$tmp/voice1" CLAUDE_DIR="$c1" VOICE_INSTALL_NO_TOOL=1 VOICE_INSTALL_NO_INIT=1 bash "$here/install_voice_pipeline.sh")"
[ -x "$c1/hooks/capture-voice.sh" ] || fail "capture hook missing"
[ -x "$c1/hooks/voice-sync-gate.sh" ] || fail "gate hook missing"
grep -q "capture-voice.sh" "$c1/settings.json" || fail "UserPromptSubmit not wired"
grep -q "VOICE_SYNC_REPO" "$c1/settings.json" && fail "old gate command not rewritten"
cmd1="$(get_command "$c1/settings.json")"
[ "$cmd1" = 'bash "$HOME/.claude/hooks/voice-sync-gate.sh"' ] || fail "rewrite did not produce the plain command: $cmd1"
echo "$out1" | grep -q "SessionEnd:rewritten" || fail "expected rewrite notice: $out1"

out2="$(VOICE_DIR="$tmp/voice1" CLAUDE_DIR="$c1" VOICE_INSTALL_NO_TOOL=1 VOICE_INSTALL_NO_INIT=1 bash "$here/install_voice_pipeline.sh")"
echo "$out2" | grep -q "0 change(s)" || fail "re-run was not a no-op: $out2"
n="$(grep -c "capture-voice.sh" "$c1/settings.json")"
[ "$n" -eq 1 ] || fail "duplicate capture hook wiring ($n)"

# --- scenario 2: only the two dead assignments are stripped; a custom VOICE_SYNC_ var survives
c2="$tmp/claude2"
mkdir -p "$c2"
cat > "$c2/settings.json" <<'JSON'
{"hooks": {"SessionEnd": [{"hooks": [{"type": "command",
 "command": "VOICE_SYNC_MODEL=sonnet VOICE_SYNC_REPO=\"x\" bash \"$HOME/.claude/hooks/voice-sync-gate.sh\"", "timeout": 10}]}]}}
JSON

out3="$(VOICE_DIR="$tmp/voice2" CLAUDE_DIR="$c2" VOICE_INSTALL_NO_TOOL=1 VOICE_INSTALL_NO_INIT=1 bash "$here/install_voice_pipeline.sh")"
echo "$out3" | grep -q "SessionEnd:rewritten" || fail "expected rewrite notice: $out3"
cmd2="$(get_command "$c2/settings.json")"
[ "$cmd2" = 'VOICE_SYNC_MODEL=sonnet bash "$HOME/.claude/hooks/voice-sync-gate.sh"' ] || fail "custom var was not preserved: $cmd2"

# --- scenario 3: two matching entries -> WARN reported, only the first is rewritten, neither
# entry is deleted
c3="$tmp/claude3"
mkdir -p "$c3"
cat > "$c3/settings.json" <<'JSON'
{"hooks": {"SessionEnd": [
  {"hooks": [{"type": "command",
   "command": "VOICE_SYNC_REPO=\"x\" bash \"$HOME/.claude/hooks/voice-sync-gate.sh\"", "timeout": 10}]},
  {"hooks": [{"type": "command",
   "command": "bash \"$HOME/.claude/hooks/voice-sync-gate.sh\"", "timeout": 10}]}
]}}
JSON

out4="$(VOICE_DIR="$tmp/voice3" CLAUDE_DIR="$c3" VOICE_INSTALL_NO_TOOL=1 VOICE_INSTALL_NO_INIT=1 bash "$here/install_voice_pipeline.sh")"
echo "$out4" | grep -q "WARN: SessionEnd: 1 extra voice-sync-gate.sh hook entries" || fail "expected WARN line: $out4"
n3="$(grep -c "voice-sync-gate.sh" "$c3/settings.json")"
[ "$n3" -eq 2 ] || fail "a duplicate entry was deleted ($n3)"
cmd3="$(get_command "$c3/settings.json")"
[ "$cmd3" = 'bash "$HOME/.claude/hooks/voice-sync-gate.sh"' ] || fail "first (matched) entry was not rewritten: $cmd3"

echo "PASS: install_voice_pipeline.test.sh"
