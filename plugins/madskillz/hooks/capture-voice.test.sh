#!/usr/bin/env bash
# Test capture-voice.sh: appends a {ts,text} line for a real prompt, no-ops on an
# empty prompt, survives malformed input, always exits 0, writes nothing to stdout.
# Uses a temp HOME so no real corpus is touched.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
hook="$here/capture-voice.sh"
fail=0
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
corpus="$tmp/.madskillz/voice/corpus.jsonl"

# 1) real prompt -> exactly one corpus line carrying the text + a timestamp, no stdout
out="$(printf '%s' '{"prompt":"Hello voice","hook_event_name":"UserPromptSubmit"}' | HOME="$tmp" bash "$hook")"
rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: exit $rc on real prompt"; fail=1; }
[ -z "$out" ] || { echo "FAIL: hook wrote to stdout: $out"; fail=1; }
if [ -f "$corpus" ] && grep -q '"text": "Hello voice"' "$corpus" && grep -q '"ts"' "$corpus"; then :; else
  echo "FAIL: corpus line missing/incorrect"; fail=1; fi
[ "$(wc -l < "$corpus" 2>/dev/null)" = "1" ] || { echo "FAIL: expected exactly 1 corpus line"; fail=1; }

# 2) empty/whitespace prompt -> no new line appended
printf '%s' '{"prompt":"   "}' | HOME="$tmp" bash "$hook" >/dev/null
[ "$(wc -l < "$corpus" 2>/dev/null)" = "1" ] || { echo "FAIL: empty prompt should not append"; fail=1; }

# 3) malformed JSON -> still exit 0, no crash, no new line
printf '%s' 'not json at all' | HOME="$tmp" bash "$hook" >/dev/null; rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: exit $rc on malformed input"; fail=1; }
[ "$(wc -l < "$corpus" 2>/dev/null)" = "1" ] || { echo "FAIL: malformed input should not append"; fail=1; }

[ "$fail" -eq 0 ] && echo "PASS: capture-voice.sh" || { echo "capture-voice.sh TESTS FAILED"; exit 1; }
