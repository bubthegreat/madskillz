# Voice updater — keep "how the owner writes" current

Maintains an evolving profile of the owner's writing voice from their **actual messages**, refined
incrementally over time. Goal: a sharper "this is how the owner talks" with every pass — without
forcing a new finding when there isn't one.

## Files
- **Live profile:** `~/.claude/voice/voice.md` — the aggregate characterization the blog writer uses.
  Seeded from this skill's `references/voice.md` on first run.
- **Corpus:** `~/.claude/voice/corpus.jsonl` — append-only; one JSON object per owner message,
  `{ "ts": "<ISO8601>", "text": "<the message>" }`, written by the capture hook (see Setup).
- **Marker:** the live profile records `Processed through: <ts>` in its Provenance section — the
  timestamp of the last corpus entry already folded in.

## Update algorithm (one pass)
1. If `~/.claude/voice/voice.md` does not exist, create it by copying `references/voice.md`, and set
   its Provenance to include `Processed through: none` plus an empty `Changelog`.
2. Read `corpus.jsonl`; select entries whose `ts` is greater than the recorded marker (all of them
   if `none`). These are the **new** messages.
3. If there are no new entries → stop. The profile is current; change nothing.
4. Read the new messages as writing samples and ask: is there anything **genuinely new** about how
   the owner writes that the profile does not already capture? — recurring turns of phrase, sentence
   rhythm, humor moves, punctuation habits, hedges, favorite words, structure. Only real, repeated
   signals count; one-off wording is not a trait.
5. If something new and real is found, merge it into the relevant section of the live `voice.md`
   (tighten or extend wording; do not bloat) and add a one-line dated note to the `Changelog`. If
   nothing rises to that bar, add nothing — a no-change pass is a valid, honest outcome.
6. Set `Processed through:` to the `ts` of the newest entry just considered.

## Rules
- **Observed, never invented.** Every trait traces to real messages. Never add a flourish the owner
  has not shown.
- **Incremental, not a rewrite.** Refine the aggregate; do not restart it each pass.
- **Don't force findings.** Most passes add little or nothing; that is expected and fine.
- **Keep it usable.** The profile stays a tight, voice-defining brief — not a transcript dump.

## Setup — the capture hook (global, always-on)
The corpus is fed by a **global** `UserPromptSubmit` hook in `~/.claude/settings.json` that runs
`~/.claude/hooks/capture-voice.sh` on every prompt in every session — independent of any plugin, so it
records the owner's writing no matter which prompt or project they are in. The canonical script lives
in this repo at `hooks/capture-voice.sh` (tested by `hooks/capture-voice.test.sh`); install it by
copying to `~/.claude/hooks/capture-voice.sh` and adding the hook to `~/.claude/settings.json`. It
appends each message as `{ts,text}` to `~/.claude/voice/corpus.jsonl`, never blocking the prompt and
emitting no stdout. It is deliberately **not** a plugin hook — a plugin-scoped hook would only fire
when this plugin is loaded, and would double-record alongside the global one. The updater can also run
on demand over whatever messages are present in the current session.
