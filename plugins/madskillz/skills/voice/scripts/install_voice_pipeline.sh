#!/usr/bin/env bash
# install_voice_pipeline.sh - one-shot, idempotent installer for the voice skill on this machine.
#
# What it sets up:
#   1. ~/.madskillz/voice/tool/                 copy of voicectl, installed as a uv tool
#      ~/.madskillz/voice-templates/            profile templates, beside the store (never inside it)
#   2. ~/.claude/hooks/capture-voice.sh         global UserPromptSubmit shim -> voicectl capture
#   3. ~/.claude/hooks/voice-sync-gate.sh       SessionEnd shim -> voicectl gate
#   4. ~/.claude/settings.json                  hook wiring for 2 + 3 (never clobbers other hooks)
#   5. ~/.madskillz/voice/                      the voice store: `voicectl init` (clone/adopt/create)
#   6. corpus backfill + first push
#
# Env:
#   VOICE_DIR                 voice dir                       (~/.madskillz/voice)
#   CLAUDE_DIR                claude config dir               (~/.claude)
#   VOICE_REMOTE              git URL of your private voice repo; unset = local-only
#   VOICE_CREATE=1            create VOICE_REMOTE (github.com + gh) if it does not exist
#   VOICE_ALLOW_PUBLIC=1      allow a public remote (the corpus holds verbatim prompts)
#   VOICE_INSTALL_NO_TOOL=1   skip the uv tool install (tests / offline)
#   VOICE_INSTALL_NO_INIT=1   skip init/backfill/push (tests)
set -u

here="$(cd "$(dirname "$0")" && pwd)"
skill_root="$(cd "$here/.." && pwd)"
VOICE_DIR="${VOICE_DIR:-$HOME/.madskillz/voice}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
export VOICE_DIR CLAUDE_DIR

say() { printf '%s\n' "$*"; }
ok=0; skipped=0
did()  { say "  + $*"; ok=$((ok+1)); }
skip() { say "  = $*"; skipped=$((skipped+1)); }

if [ "${BASH_VERSINFO[0]}" -lt 4 ] || { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -lt 4 ]; }; then say "ERROR: bash >= 4.4 required"; exit 1; fi

command -v python3 >/dev/null 2>&1 || { say "ERROR: python3 required"; exit 1; }
command -v git >/dev/null 2>&1 || { say "ERROR: git required"; exit 1; }

# --- 1. voicectl tool + templates -----------------------------------------------------------
# The tool copy lives inside the store dir but outside its tracked files (tool/ is gitignored)
# so it never dangles when the skill checkout moves. The templates go BESIDE the store dir:
# anything inside it is the user's own data, which `voicectl init` renames aside when it
# adopts a remote store.
tool_dir="$VOICE_DIR/tool"
templates_dir="$(dirname "$VOICE_DIR")/voice-templates"
if [ -n "${VOICE_INSTALL_NO_TOOL:-}" ]; then
  skip "voicectl install skipped (VOICE_INSTALL_NO_TOOL)"
elif ! command -v uv >/dev/null 2>&1; then
  say "  ! uv not found - voicectl not installed; install uv and re-run"
else
  rm -rf "$tool_dir"
  mkdir -p "$tool_dir"
  cp -r "$skill_root/cli/pyproject.toml" "$skill_root/cli/voicectl" "$tool_dir/"
  mkdir -p "$templates_dir"
  cp "$skill_root/references/voices/"*.md "$templates_dir/"
  did "installed profile templates ($templates_dir)"
  if uv tool install --force --quiet "$tool_dir" 2>/dev/null; then
    did "installed voicectl (uv tool) from $tool_dir"
  else
    say "  ! uv tool install failed - voicectl unavailable"
  fi
fi

# --- 2+3. hook shims ---------------------------------------------------------------------------
mkdir -p "$CLAUDE_DIR/hooks"
for h in capture-voice.sh voice-sync-gate.sh; do
  src="$skill_root/hooks/$h" dst="$CLAUDE_DIR/hooks/$h"
  [ -f "$src" ] || { say "ERROR: hook source missing: $src"; exit 1; }
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then skip "hook current: $dst"; else
    cp "$src" "$dst" && chmod +x "$dst" && did "installed hook: $dst"
  fi
done

# --- 4. settings.json --------------------------------------------------------------------------
# Adds the two hook entries, matched by script name. An existing gate entry that still carries
# the dead VOICE_SYNC_REPO / VOICE_SYNC_AUTOREFRESH assignments has only those two stripped -
# any other env on the command (e.g. a hand-added VOICE_SYNC_MODEL=...) survives. The first
# matching entry per event wins; extra matching entries are never touched or deleted, just
# reported so the owner can clean them up by hand.
wired_full="$(SETTINGS="$CLAUDE_DIR/settings.json" python3 - <<'PY'
import json, os, re, sys

path = os.environ["SETTINGS"]
try:
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
except FileNotFoundError:
    settings = {}
except Exception as e:
    print(f"ERROR: cannot parse {path}: {e}")
    sys.exit(1)

DEAD_VAR_RE = re.compile(r'(?:^|\s)VOICE_SYNC_(?:REPO|AUTOREFRESH)=(?:"[^"]*"|\S+)')

hooks = settings.setdefault("hooks", {})
wanted = {
    "UserPromptSubmit": ("capture-voice.sh", 'bash "$HOME/.claude/hooks/capture-voice.sh"'),
    "SessionEnd": ("voice-sync-gate.sh", 'bash "$HOME/.claude/hooks/voice-sync-gate.sh"'),
}
changed = []
warnings = []
for event, (marker, command) in wanted.items():
    entries = hooks.setdefault(event, [])
    found = None
    total = 0
    for e in entries:
        for h in e.get("hooks", []):
            if marker in h.get("command", ""):
                total += 1
                if found is None:
                    found = h  # first match wins; later matches only counted, never edited
    if found is None:
        entries.append({"hooks": [{"type": "command", "command": command, "timeout": 10}]})
        changed.append(f"{event}:added")
    elif found["command"] != command:
        cleaned = DEAD_VAR_RE.sub("", found["command"]).strip()
        if cleaned != found["command"]:
            found["command"] = cleaned
            changed.append(f"{event}:rewritten")
    if total > 1:
        warnings.append(
            f"WARN: {event}: {total - 1} extra {marker} hook entries in settings.json - "
            f"remove duplicates by hand"
        )

if changed:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")

for w in warnings:
    print(w)
print(",".join(changed) if changed else "none")
PY
)"
# The python block prints any WARN lines first, then the added/rewritten summary as the last
# line - split them so the WARN lines are surfaced verbatim and the case below only sees the
# summary.
wired="$(printf '%s\n' "$wired_full" | tail -n1)"
warn_lines="$(printf '%s\n' "$wired_full" | sed '$d')"
[ -n "$warn_lines" ] && say "$warn_lines"
case "$wired" in
  ERROR*) say "$wired"; exit 1 ;;
  none)   skip "settings.json hooks already wired" ;;
  *)      did "settings.json: $wired" ;;
esac

# --- 5+6. the voice store ------------------------------------------------------------------------
PATH="$HOME/.local/bin:$PATH"
if [ -n "${VOICE_INSTALL_NO_INIT:-}" ]; then
  skip "store init skipped (VOICE_INSTALL_NO_INIT)"
elif ! command -v voicectl >/dev/null 2>&1; then
  say "  ! voicectl not on PATH - store init skipped; re-run after installing uv"
else
  init_args=()
  if [ -n "${VOICE_REMOTE:-}" ]; then
    init_args+=(--remote "$VOICE_REMOTE")
    [ -n "${VOICE_CREATE:-}" ] && init_args+=(--create)
    [ -n "${VOICE_ALLOW_PUBLIC:-}" ] && init_args+=(--allow-public)
  fi
  if out="$(voicectl init "${init_args[@]}" 2>&1)"; then
    say "$out" | sed 's/^/    /'
    if printf '%s\n' "$out" | grep -q "action: already"; then
      skip "voice store already wired ($VOICE_DIR)"
    else
      did "voice store ready ($VOICE_DIR)"
    fi
    if bfout="$(voicectl backfill 2>&1)"; then
      if printf '%s\n' "$bfout" | grep -qF ' 0 appended -> '; then
        skip "backfill: no new lines"
      else
        did "$bfout"
      fi
    fi
    if [ -n "${VOICE_REMOTE:-}" ]; then
      if pout="$(voicectl push 2>&1)"; then
        if printf '%s\n' "$pout" | grep -qF "nothing to push"; then
          skip "$pout"
        else
          did "$pout"
        fi
      else
        say "  ! push failed: $pout"
      fi
    else
      say "  ! local-only: set VOICE_REMOTE (or ask Claude to 'set up my voice') to sync across machines"
    fi
  else
    say "  ! voicectl init failed:"; say "$out" | sed 's/^/    /'
  fi
fi

say ""
say "voice pipeline: $ok change(s), $skipped already in place."
