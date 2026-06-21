#!/usr/bin/env bash
# madskillz voice-capture hook (UserPromptSubmit): append the owner's prompt to the
# voice corpus so the `blog` skill's voice-updater can learn how they actually write.
# Reads the event JSON on stdin; appends one JSON line {ts,text} to
# $VOICE_DIR/corpus.jsonl (default ~/.madskillz/voice/corpus.jsonl). Never blocks the prompt,
# never errors (always exit 0), emits nothing to stdout.
dir="${VOICE_DIR:-${HOME}/.madskillz/voice}"
mkdir -p "$dir" 2>/dev/null
payload="$(cat 2>/dev/null)"            # drain the hook event JSON
command -v python3 >/dev/null 2>&1 || exit 0

printf '%s' "$payload" | VOICE_CORPUS="$dir/corpus.jsonl" python3 -c '
import sys, json, os, datetime
try:
    data = json.load(sys.stdin)
    text = data.get("prompt", "")
    if not isinstance(text, str) or not text.strip():
        sys.exit(0)
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "text": text,
    }
    path = os.environ["VOICE_CORPUS"]
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass
' >/dev/null 2>&1
exit 0
