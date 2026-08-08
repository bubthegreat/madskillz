#!/usr/bin/env bash
# Test backfill_corpus.py: mines history.jsonl + project transcripts, honors the profile's
# `Processed through:` marker, drops commands/tool-results, dedupes the same message recorded
# by both sources, and appends nothing on re-run. Uses temp VOICE_DIR/CLAUDE_DIR fixtures.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
script="$here/backfill_corpus.py"
fail=0
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
voice="$tmp/voice" claude="$tmp/claude"
mkdir -p "$voice" "$claude/projects/-tmp-proj"

cat >"$voice/voice.md" <<'EOF'
# fixture profile
- Processed through: 2026-07-01T00:00:00Z
EOF

# history: one real prompt after marker (ts 2026-07-02T00:00:00Z), one slash command,
# one shell passthrough, one real prompt BEFORE the marker
cat >"$claude/history.jsonl" <<'EOF'
{"display":"this new prompt should land in the corpus","timestamp":1782950400000}
{"display":"/caveman full","timestamp":1782950401000}
{"display":"! ls -la","timestamp":1782950402000}
{"display":"old prompt already folded in","timestamp":1750000000000}
EOF

# transcript: a real user turn, the SAME text/day as the history prompt (dupe), a tool_result
# list turn, and a meta turn
cat >"$claude/projects/-tmp-proj/sess.jsonl" <<'EOF'
{"type":"user","timestamp":"2026-07-03T10:00:00Z","message":{"content":"a transcript-only reply with real words"}}
{"type":"user","timestamp":"2026-07-02T00:00:05Z","message":{"content":"this new prompt should land in the corpus"}}
{"type":"user","timestamp":"2026-07-03T11:00:00Z","message":{"content":[{"type":"tool_result","content":"ignore me"}]}}
{"type":"user","timestamp":"2026-07-03T12:00:00Z","isMeta":true,"message":{"content":"meta noise"}}
EOF

# 1) first run: exactly 2 corpus lines (history prompt + transcript-only reply), sorted by ts
out="$(VOICE_DIR="$voice" CLAUDE_DIR="$claude" python3 "$script")"; rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: exit $rc"; echo "$out"; fail=1; }
corpus="$voice/corpus.jsonl"
[ "$(wc -l < "$corpus" 2>/dev/null)" = "2" ] || { echo "FAIL: expected 2 corpus lines"; cat "$corpus" 2>/dev/null; fail=1; }
grep -q "this new prompt should land" "$corpus" || { echo "FAIL: history prompt missing"; fail=1; }
grep -q "transcript-only reply" "$corpus" || { echo "FAIL: transcript turn missing"; fail=1; }
grep -q "old prompt" "$corpus" && { echo "FAIL: pre-marker prompt leaked in"; fail=1; }
grep -q "caveman" "$corpus" && { echo "FAIL: slash command leaked in"; fail=1; }
echo "$out" | grep -q "1 duplicate(s)" || { echo "FAIL: cross-source dupe not detected: $out"; fail=1; }
head -1 "$corpus" | grep -q "2026-07-02" || { echo "FAIL: corpus not ts-sorted"; fail=1; }

# 2) re-run appends nothing
out2="$(VOICE_DIR="$voice" CLAUDE_DIR="$claude" python3 "$script")"
echo "$out2" | grep -q "0 appended" || { echo "FAIL: re-run not idempotent: $out2"; fail=1; }
[ "$(wc -l < "$corpus")" = "2" ] || { echo "FAIL: corpus grew on re-run"; fail=1; }

[ "$fail" -eq 0 ] && echo "PASS: backfill_corpus.py" || { echo "backfill_corpus.py TESTS FAILED"; exit 1; }
