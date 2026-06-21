# Voice updater — keep "how the owner writes" current

Maintains an evolving profile of the owner's writing voice from their **actual messages**, refined
incrementally over time. Goal: a sharper "this is how the owner talks" with every pass — without
forcing a new finding when there isn't one. The profile separates **descriptive** ("how I talk",
for fidelity) from **prescriptive** ("how I should write", for quality); the updater feeds the
descriptive layer.

## Files
- **Live profile:** `~/.madskillz/voice/voice.md` — the working copy the blog writer uses; evolves every
  session. Carries frontmatter (`voice`, `owner`, `purpose`, `status: personal`).
- **Voices library:** `references/voices/<name>.md` — the **committed** copy of each named,
  per-purpose owner voice (e.g. `science-blog.md`). What non-local agents read. The generic
  `references/voice.md` (`status: template`) is **only** a starting shape — never treated as "me."
- **Corpus:** `~/.madskillz/voice/corpus.jsonl` — append-only; one JSON object per owner message,
  `{ "ts": "<ISO8601>", "text": "<the message>" }`, written by the capture hook (see Setup).
- **Markers** (in the live profile's Provenance section):
  - `Processed through: <ts>` — last corpus entry folded into the live profile.
  - `Repo-synced through: <ts>` — last corpus entry whose changes were pushed to the voices library.

## Update algorithm (one pass)
1. If `~/.madskillz/voice/voice.md` does not exist, seed it: copy the owner's committed voice
   `references/voices/<name>.md` if one exists (preferred — inherits the real, evolved voice); else
   copy `references/voice.md` (the template). Set Provenance to `Processed through: none`,
   `Repo-synced through: none`, plus an empty `Changelog`.
2. Read `corpus.jsonl`; select entries whose `ts` is greater than `Processed through`. These are the
   **new** messages.
3. If there are no new entries → skip to step 7 (the live profile is current; nothing to merge).
4. Read the new messages as writing samples and ask: is there anything **genuinely new** about how
   the owner writes that the profile does not already capture? — recurring turns of phrase, sentence
   rhythm, humor moves, punctuation habits, hedges, favorite words, structure. Only real, repeated
   signals count; one-off wording is not a trait.
5. If something new and real is found, merge it into the **descriptive** layer (tighten or extend; do
   not bloat) and add a one-line dated note to the `Changelog`. Apply the register rule below: tag
   each trait **keep** (flavor) or **tone-down** (crutch), and when the owner reaches for a phrase
   too often, record it under **Flagged overuse** as a tendency to vary in prose — never as a style
   to imitate. If nothing rises to that bar, add nothing — a no-change pass is valid and honest.
6. Set `Processed through:` to the `ts` of the newest entry just considered.
7. **Repo sync (materiality-gated):** see below. Keeps the committed voices library current for
   non-local agents without pushing on every pass.

## Repo sync — local stays live, push only when earned
The live profile is always fresh; the committed copy updates in meaningful chunks.

**Settings** (edit here):
- `Repo checkout` — path to the madskillz checkout to commit into. Default: `~/Development/madskillz`
  (override per environment; if no checkout is found, skip the sync and note it).
- `Voice file` — `plugins/madskillz/skills/blog/references/voices/<name>.md` within that checkout.
- `Push target` — **`main`** (owner-approved default). To switch to a branch/PR, change it here.
- `Commit message` — `voice: sync <name> profile (auto)`.

**Materiality check** — compare the live profile against the committed `Voice file`. Sync **only** if
the delta is material:
- a new section/subsection was added, OR
- ≥3 new substantive traits merged since `Repo-synced through`, OR
- prescriptive guidance changed (not just a marker bump).

Otherwise do nothing — no commit, no push.

**On a material delta:** copy the live profile into the `Voice file`, set `Repo-synced through:` to
the current `Processed through:` ts (in both copies), then in `Repo checkout`:
`git add <Voice file> && git commit -m "<Commit message>" && git push origin <Push target>`.
The **first** sync of a newly-committed voice is done as an explicit, visible commit (not silent);
after that the gated auto-sync runs as part of this step.

## Rules
- **Observed, never invented.** Every trait traces to real messages. Never add a flourish the owner
  has not shown.
- **Register-aware.** The descriptive layer is faithful to how the owner *talks* (including crutches
  and overused phrases — flag them); the prescriptive layer governs how that becomes good *writing*.
  Capturing a tic as a tendency is not the same as licensing it in prose.
- **Incremental, not a rewrite.** Refine the aggregate; do not restart it each pass.
- **Don't force findings.** Most passes add little or nothing; that is expected and fine.
- **Keep it usable.** The profile stays a tight, voice-defining brief — not a transcript dump.

## Background auto-sync — the SessionEnd gate (optional)
To sync without ever running the skill by hand, install the **gate hook** `hooks/voice-sync-gate.sh`
(tested by `hooks/voice-sync-gate.test.sh`) as a **SessionEnd** hook. It is the cheap tier of the
materiality check: on each session end it counts new corpus entries since `Repo-synced through` and,
only when that count ≥ `VOICE_SYNC_MIN_COUNT` (default 15) **and** at least
`VOICE_SYNC_MIN_INTERVAL_SECONDS` (default 720 = 12 min) have passed since the last attempt, it
**detaches** a headless `claude -p "update my voice"` (model `opus`) that runs this updater plus the
materiality-gated push. A lockfile prevents overlapping runs; the gate never blocks session teardown
and writes only to `~/.madskillz/voice/sync.log`. Tunables are env vars (see the script header).

Install: copy `hooks/voice-sync-gate.sh` to `~/.claude/hooks/`, make it executable, and add a
`SessionEnd` hook to `~/.claude/settings.json`. Recommended command (pushes from a dedicated
`main`-pinned worktree and keeps it current):
`VOICE_SYNC_REPO="$HOME/.madskillz/voice/madskillz-sync" VOICE_SYNC_AUTOREFRESH=1 bash "$HOME/.claude/hooks/voice-sync-gate.sh"`.

Notes:
- The background agent runs **least-privilege** via `--allowedTools` (read/edit the voice file, run
  the skill, git, python) — deliberately **not** `--permission-mode bypassPermissions`. A denied
  tool just fails the sync quietly; the unattended agent never performs unapproved actions.
- It pushes to `Push target` (default `main`). Make sure the voices-library infrastructure is on that
  branch first, or an early background push lands the voice file without its supporting skill files.
- **`VOICE_SYNC_REPO` should be a *dedicated* clone pinned to the push branch** — never a roaming
  working checkout, and **a clone, not a worktree** (a worktree would re-lock `main` out of your
  primary checkout). Create one with `git clone <your madskillz remote> ~/.madskillz/voice/madskillz-sync`
  checked out on `main`.
- **`VOICE_SYNC_AUTOREFRESH=1`** makes the gate `fetch` + `reset --hard origin/<branch>` that repo
  before launching, so the push always fast-forwards. It is guarded: it **refuses** unless the repo
  is actually on the target branch, so it can never reset a working checkout. `reset --hard` is safe
  here only because the dedicated repo holds nothing precious (the live profile is the source of
  truth). Do **not** enable it against a non-dedicated checkout.

## Setup — the capture hook (global, always-on)
The corpus is fed by a **global** `UserPromptSubmit` hook in `~/.claude/settings.json` that runs
`~/.claude/hooks/capture-voice.sh` on every prompt in every session — independent of any plugin, so it
records the owner's writing no matter which prompt or project they are in. The canonical script lives
in this repo at `hooks/capture-voice.sh` (tested by `hooks/capture-voice.test.sh`); install it by
copying to `~/.claude/hooks/capture-voice.sh` and adding the hook to `~/.claude/settings.json`. It
appends each message as `{ts,text}` to `~/.madskillz/voice/corpus.jsonl`, never blocking the prompt and
emitting no stdout. It is deliberately **not** a plugin hook — a plugin-scoped hook would only fire
when this plugin is loaded, and would double-record alongside the global one. The updater can also run
on demand over whatever messages are present in the current session.
