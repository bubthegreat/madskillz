#!/usr/bin/env bash
# madskillz voice-sync gate hook (SessionEnd).
#
# The CHEAP tier of a two-tier materiality check (see skills/blog/references/voice-update.md):
# a deterministic pre-filter that decides whether it is even worth spending an LLM. When enough
# new messages have accumulated AND we haven't tried recently, it launches a DETACHED headless
# agent ("update my voice") that does the real judgment + merge + materiality-gated push.
#
# Contract: never blocks session teardown, never errors (always exit 0), emits nothing to stdout.
#
# Tunables (env overrides, with defaults):
#   VOICE_SYNC_MIN_COUNT             new corpus msgs since last sync to trigger   (15)
#   VOICE_SYNC_MIN_INTERVAL_SECONDS  min seconds between launch attempts          (720 = 12 min)
#   VOICE_SYNC_LOCK_STALE_SECONDS    a lock older than this is treated as dead    (1800 = 30 min)
#   VOICE_SYNC_MODEL                 model for the background agent               (opus)
#   VOICE_SYNC_REPO                  repo checkout to commit/push from            (~/Development/madskillz)
#   VOICE_DIR                        voice dir                                    (~/.claude/voice)
#   VOICE_SYNC_LAUNCH                test/override: run this synchronously instead of detaching
set -u

cat >/dev/null 2>&1   # drain the SessionEnd event JSON on stdin

VOICE_DIR="${VOICE_DIR:-$HOME/.claude/voice}"
PROFILE="$VOICE_DIR/voice.md"
CORPUS="$VOICE_DIR/corpus.jsonl"
LOCK="$VOICE_DIR/.sync.lock"
STAMP="$VOICE_DIR/.last-sync-attempt"
LOG="$VOICE_DIR/sync.log"

MIN_COUNT="${VOICE_SYNC_MIN_COUNT:-15}"
MIN_INTERVAL="${VOICE_SYNC_MIN_INTERVAL_SECONDS:-720}"
LOCK_STALE="${VOICE_SYNC_LOCK_STALE_SECONDS:-1800}"
MODEL="${VOICE_SYNC_MODEL:-opus}"
REPO="${VOICE_SYNC_REPO:-$HOME/Development/madskillz}"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$LOG" 2>/dev/null; }

command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$CORPUS" ] || exit 0
[ -f "$PROFILE" ] || exit 0

now=$(date -u +%s 2>/dev/null || echo 0)

# --- Throttle: launched too recently? -----------------------------------------------------------
if [ -f "$STAMP" ]; then
  last=$(stat -c %Y "$STAMP" 2>/dev/null || echo 0)
  if [ $(( now - last )) -lt "$MIN_INTERVAL" ]; then
    exit 0
  fi
fi

# --- Lock: a sync already in flight (and not stale)? --------------------------------------------
if [ -f "$LOCK" ]; then
  lockt=$(stat -c %Y "$LOCK" 2>/dev/null || echo 0)
  if [ $(( now - lockt )) -lt "$LOCK_STALE" ]; then
    log "skip: sync already running"
    exit 0
  fi
  log "clearing stale lock"
  rm -f "$LOCK" 2>/dev/null
fi

# --- Count new corpus entries since 'Repo-synced through' ----------------------------------------
count=$(PROFILE="$PROFILE" CORPUS="$CORPUS" python3 -c '
import sys, json, re, os
marker = ""
try:
    with open(os.environ["PROFILE"], encoding="utf-8") as f:
        m = re.search(r"Repo-synced through:\s*(\S+)", f.read())
        if m and m.group(1).lower() != "none":
            marker = m.group(1)
except Exception:
    pass
n = 0
try:
    with open(os.environ["CORPUS"], encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ts = json.loads(line).get("ts", "")
            except Exception:
                continue
            if ts > marker:
                n += 1
except Exception:
    pass
print(n)
' 2>/dev/null)
[[ "${count:-}" =~ ^[0-9]+$ ]] || count=0

if [ "$count" -lt "$MIN_COUNT" ]; then
  exit 0
fi

# --- Gate passed: record the attempt, take the lock, launch the agent ----------------------------
touch "$STAMP" 2>/dev/null
touch "$LOCK" 2>/dev/null
log "gate passed: $count new msgs >= $MIN_COUNT — launching background sync (model=$MODEL)"

# Test/override hook: run synchronously, then release the lock.
if [ -n "${VOICE_SYNC_LAUNCH:-}" ]; then
  eval "$VOICE_SYNC_LAUNCH"
  rm -f "$LOCK" 2>/dev/null
  exit 0
fi

command -v claude >/dev/null 2>&1 || { log "skip: claude not found"; rm -f "$LOCK" 2>/dev/null; exit 0; }

# Detach so SessionEnd never waits on the LLM. The agent runs the blog skill's voice-update +
# materiality-gated push; the lock is released when it finishes (success or failure).
#
# LEAST-PRIVILEGE (deliberate): the unattended agent is restricted to exactly the tools the voice
# sync needs — read/edit the voice file, invoke the skill, git, python. Every other tool is denied.
# A denied tool just fails the sync quietly; the agent never performs unapproved actions. We do NOT
# use --permission-mode bypassPermissions: an unattended agent must not have a blank cheque.
nohup bash -c '
  cd "'"$REPO"'" 2>/dev/null || cd "$HOME"
  claude -p "update my voice" --model "'"$MODEL"'" --add-dir "'"$VOICE_DIR"'" \
    --allowedTools Read Edit Write Skill Glob Grep "Bash(git:*)" "Bash(python3:*)" >>"'"$LOG"'" 2>&1
  rm -f "'"$LOCK"'" 2>/dev/null
' >/dev/null 2>&1 &
disown 2>/dev/null || true
exit 0
