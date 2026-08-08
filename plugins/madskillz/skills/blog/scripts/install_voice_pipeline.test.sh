#!/usr/bin/env bash
# Test install_voice_pipeline.sh: creates the voice dir, seeds the live profile, installs both
# hooks, wires settings.json without clobbering existing hooks, and is idempotent on re-run.
# Uses a temp HOME; the sync-clone step is skipped via VOICE_INSTALL_NO_CLONE.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
installer="$here/install_voice_pipeline.sh"
fail=0
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/.claude"
cat >"$tmp/.claude/settings.json" <<'EOF'
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "node existing-tracker.js" } ] }
    ]
  },
  "theme": "dark"
}
EOF

# 1) first run installs everything
out="$(HOME="$tmp" VOICE_INSTALL_NO_CLONE=1 bash "$installer")"; rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: exit $rc on first run"; echo "$out"; fail=1; }
[ -f "$tmp/.madskillz/voice/voice.md" ] || { echo "FAIL: live profile not seeded"; fail=1; }
grep -q "voice: science-blog" "$tmp/.madskillz/voice/voice.md" 2>/dev/null \
  || { echo "FAIL: seeded profile is not the committed science-blog voice"; fail=1; }
for h in capture-voice.sh voice-sync-gate.sh; do
  [ -x "$tmp/.claude/hooks/$h" ] || { echo "FAIL: hook not installed/executable: $h"; fail=1; }
done

# 2) settings.json: valid JSON, both events wired, existing hook preserved
HOME="$tmp" python3 - <<'PY' || fail=1
import json, os, sys
with open(os.path.expanduser("~/.claude/settings.json"), encoding="utf-8") as f:
    s = json.load(f)
cmds = [h["command"] for ev in s["hooks"].values() for e in ev for h in e["hooks"]]
checks = {
    "existing hook preserved": any("existing-tracker.js" in c for c in cmds),
    "capture hook wired": any("capture-voice.sh" in c for c in cmds),
    "gate hook wired": any("voice-sync-gate.sh" in c for c in cmds),
    "gate uses dedicated sync repo": any("madskillz-sync" in c for c in cmds),
    "other settings kept": s.get("theme") == "dark",
}
bad = [name for name, okay in checks.items() if not okay]
for name in bad:
    print(f"FAIL: {name}")
sys.exit(1 if bad else 0)
PY

# 3) re-run is a no-op
out2="$(HOME="$tmp" VOICE_INSTALL_NO_CLONE=1 bash "$installer")"; rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: exit $rc on re-run"; fail=1; }
echo "$out2" | grep -q "0 change(s)" || { echo "FAIL: re-run not idempotent:"; echo "$out2"; fail=1; }
n=$(HOME="$tmp" python3 -c '
import json, os
s = json.load(open(os.path.expanduser("~/.claude/settings.json")))
print(sum(len(e["hooks"]) for ev in s["hooks"].values() for e in ev))')
[ "$n" = "3" ] || { echo "FAIL: expected 3 hook commands after re-run, got $n"; fail=1; }

[ "$fail" -eq 0 ] && echo "PASS: install_voice_pipeline.sh" || { echo "install_voice_pipeline.sh TESTS FAILED"; exit 1; }
