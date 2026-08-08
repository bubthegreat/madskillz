#!/usr/bin/env bash
# install_voice_pipeline.sh — one-shot, idempotent installer for the blog skill's
# voice-capture + auto-sync pipeline on this machine.
#
# What it sets up (see ../references/voice-update.md for the full design):
#   1. ~/.madskillz/voice/                      the voice dir
#   2. ~/.madskillz/voice/voice.md              live profile, seeded from the committed voice
#   3. ~/.claude/hooks/capture-voice.sh         global UserPromptSubmit corpus capture
#   4. ~/.claude/hooks/voice-sync-gate.sh       SessionEnd gate that launches background syncs
#   5. ~/.claude/settings.json                  hook wiring for 3 + 4 (never clobbers other hooks)
#   6. ~/.madskillz/voice/madskillz-sync        dedicated main-pinned clone the gate pushes from
#
# Idempotent: every step skips when already done; safe to re-run.
#
# Env overrides:
#   VOICE_DIR                 voice dir                    (~/.madskillz/voice)
#   CLAUDE_DIR                claude config dir            (~/.claude)
#   VOICE_REMOTE              remote for the sync clone    (origin of this checkout, else
#                                                           git@github.com:bubthegreat/madskillz.git)
#   VOICE_INSTALL_NO_CLONE=1  skip the sync-clone step     (tests / offline)
set -u

here="$(cd "$(dirname "$0")" && pwd)"
plugin_root="$(cd "$here/../../.." && pwd)"            # scripts -> blog -> skills -> plugin root
VOICE_DIR="${VOICE_DIR:-$HOME/.madskillz/voice}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
committed_voice="$here/../references/voices/science-blog.md"

say() { printf '%s\n' "$*"; }
ok=0; skipped=0
did()  { say "  + $*"; ok=$((ok+1)); }
skip() { say "  = $*"; skipped=$((skipped+1)); }

command -v python3 >/dev/null 2>&1 || { say "ERROR: python3 required"; exit 1; }

# --- 1. voice dir -------------------------------------------------------------------------------
if [ -d "$VOICE_DIR" ]; then skip "voice dir exists: $VOICE_DIR"; else
  mkdir -p "$VOICE_DIR" && did "created $VOICE_DIR"
fi

# --- 2. seed live profile -----------------------------------------------------------------------
if [ -f "$VOICE_DIR/voice.md" ]; then skip "live profile exists: $VOICE_DIR/voice.md"; else
  if [ -f "$committed_voice" ]; then
    cp "$committed_voice" "$VOICE_DIR/voice.md" && did "seeded live profile from committed science-blog voice"
  else
    say "ERROR: committed voice not found at $committed_voice"; exit 1
  fi
fi

# --- 3+4. install hook scripts ------------------------------------------------------------------
mkdir -p "$CLAUDE_DIR/hooks"
for h in capture-voice.sh voice-sync-gate.sh; do
  src="$plugin_root/hooks/$h" dst="$CLAUDE_DIR/hooks/$h"
  [ -f "$src" ] || { say "ERROR: hook source missing: $src"; exit 1; }
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then skip "hook current: $dst"; else
    cp "$src" "$dst" && chmod +x "$dst" && did "installed hook: $dst"
  fi
done

# --- 5. wire settings.json ----------------------------------------------------------------------
# Appends a UserPromptSubmit entry for capture-voice.sh and a SessionEnd entry for the gate,
# matching by script name so re-runs and hand-edits don't duplicate. Existing hooks untouched.
wired="$(SETTINGS="$CLAUDE_DIR/settings.json" python3 - <<'PY'
import json, os, sys

path = os.environ["SETTINGS"]
try:
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
except FileNotFoundError:
    settings = {}
except Exception as e:
    print(f"ERROR: cannot parse {path}: {e}")
    sys.exit(1)

hooks = settings.setdefault("hooks", {})
wanted = {
    "UserPromptSubmit": (
        "capture-voice.sh",
        'bash "$HOME/.claude/hooks/capture-voice.sh"',
    ),
    "SessionEnd": (
        "voice-sync-gate.sh",
        'VOICE_SYNC_REPO="$HOME/.madskillz/voice/madskillz-sync" VOICE_SYNC_AUTOREFRESH=1 '
        'bash "$HOME/.claude/hooks/voice-sync-gate.sh"',
    ),
}
added = []
for event, (marker, command) in wanted.items():
    entries = hooks.setdefault(event, [])
    present = any(
        marker in h.get("command", "")
        for e in entries
        for h in e.get("hooks", [])
    )
    if present:
        continue
    entries.append({"hooks": [{"type": "command", "command": command, "timeout": 10}]})
    added.append(event)

if added:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
print(",".join(added) if added else "none")
PY
)"
case "$wired" in
  ERROR*) say "$wired"; exit 1 ;;
  none)   skip "settings.json hooks already wired" ;;
  *)      did "settings.json: added hook(s): $wired" ;;
esac

# --- 6. dedicated sync clone --------------------------------------------------------------------
# A CLONE pinned to main, never a worktree (a worktree would lock main out of the primary
# checkout). Holds nothing precious; the gate hard-resets it to origin/main before each sync.
sync_repo="$VOICE_DIR/madskillz-sync"
if [ -n "${VOICE_INSTALL_NO_CLONE:-}" ]; then
  skip "sync clone skipped (VOICE_INSTALL_NO_CLONE)"
elif [ -d "$sync_repo/.git" ]; then
  skip "sync clone exists: $sync_repo"
else
  remote="${VOICE_REMOTE:-}"
  if [ -z "$remote" ]; then
    remote="$(git -C "$here" remote get-url origin 2>/dev/null || true)"
  fi
  [ -n "$remote" ] || remote="git@github.com:bubthegreat/madskillz.git"
  if git clone --branch main "$remote" "$sync_repo" >/dev/null 2>&1; then
    did "cloned sync repo: $remote -> $sync_repo (main)"
  else
    say "  ! sync clone FAILED ($remote) — auto-push disabled until it exists; re-run when online"
  fi
fi

say ""
say "voice pipeline: $ok change(s), $skipped already in place."
say "Backfill existing local history with: python3 $here/backfill_corpus.py"
