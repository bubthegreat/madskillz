# Voice System — design spec (2026-08-19)

Productionize the owner-voice pipeline: promote it out of the blog skill into a dedicated
`voice` skill, split the single monolithic voice into a **core** profile (how the owner talks
and thinks) plus thin **per-context overlays** (blog, research, chat, storycraft), and port all
deterministic logic from bash/prose into a tested Python CLI (`voicectl`).

## Goals

- One source of truth for observed voice traits (core); contexts stay thin prescriptive deltas.
- Deterministic work (markers, merge, materiality, git sync, corpus capture) runs in tested
  Python, not in LLM prose or fragile bash.
- LLM does exactly one job: trait judgment (extract genuinely-new descriptive traits from new
  corpus messages).
- Existing workflow preserved: live files in `~/.madskillz/voice/`, committed copies in the
  repo, SessionEnd gate, materiality-gated auto-push to `main` from the dedicated sync clone.

## Non-goals

- No change to the corpus capture cadence or format (`{ts,text}` JSONL, append-only).
- No PR-based sync; push-to-main model stays.
- No new voice-consuming features; existing consumers just re-point.

## Layout

```
plugins/madskillz/skills/voice/
  SKILL.md                    # agent entry: render/update/status/mint usage
  references/
    voice-update.md           # LLM judgment guidance ONLY (trait extraction rules)
    voices/
      core.md                 # identity + descriptive layer + provenance markers
      blog.md                 # prescriptive overlay (comedy moves, signature arc)
      research.md             # overlay: formal register, clarity rules, no comedy
      chat.md                 # overlay: conversational register
      storycraft.md           # overlay: fiction narration
  cli/                        # uv package `voicectl` (pyproject + src + tests)
  hooks/
    capture-voice.sh          # thin shim -> voicectl capture
    voice-sync-gate.sh        # thin shim -> voicectl gate
  scripts/
    install_voice_pipeline.sh # idempotent installer (ports blog's installer)
  evals/evals.json            # agent-side update-flow eval
```

Live dir `~/.madskillz/voice/` keeps its shape: live `core.md` + `<context>.md` copies,
`corpus.jsonl`, `sync.log`, `.sync.lock`, `.last-sync-attempt`, sync clone `madskillz-sync/`,
plus `tool/` (copied CLI source the uv tool install points at). `voice.md` becomes a rendered
blog-output compatibility file for one release.

## File contract

Frontmatter: `voice`, `owner`, `purpose`, `status` (`personal|template`), and on overlays
`extends: core`. Core owns sections: identity preamble, `## Mechanics`,
`## Inquiry style`, `## Flagged overuse`, `## AI-tells` (all-register rules), and
`## Provenance & sync` (markers `Processed through:` / `Repo-synced through:` + Changelog).
Overlays own prescriptive sections for their medium. An overlay section whose heading exactly
matches a core heading and carries `<!-- override -->` on the line after the heading replaces
the core section; otherwise overlay sections append after core sections.

## Render (deterministic merge)

`voicectl render <context>`: parse core + overlay into (heading, body) section lists; apply
override/append rule; emit one markdown doc (frontmatter synthesized: voice = context name,
provenance from core) to stdout or `-o FILE`. Errors loudly on unknown context, missing core,
or an `<!-- override -->` with no matching core heading. No LLM involvement.

## CLI — `voicectl`

uv package in `skills/voice/cli/`. Python ≥3.11, stdlib only (argparse). Installed by the
installer: copy `cli/` to `~/.madskillz/voice/tool/` and `uv tool install --editable` it.

| Command | Behavior |
|---|---|
| `capture` | Read hook JSON on stdin, append `{ts,text}` to corpus. Never fails teardown: always exit 0, errors to sync.log. |
| `backfill` | Port of `backfill_corpus.py`: mine `~/.claude/history.jsonl` + `~/.claude/projects/*/` transcripts, dedupe, honor `Processed through`, idempotent. |
| `render <context>` | Deterministic merge (above). |
| `status [--json]` | Markers, pending corpus count, materiality verdict, lock state. |
| `gate` | SessionEnd cheap tier: pending ≥ MIN_COUNT and interval elapsed and no live lock → detach headless `claude -p "update my voice"` updater. Same tunables/env as today's bash. Always exit 0. |
| `sync [--dry-run]` | Deterministic materiality check; on material delta copy live → committed voice files in sync clone, bump `Repo-synced through` in both, `git add/commit/push origin main`. Refuses unless clone is on target branch. |
| `update-prep [--json]` | Emit new corpus entries since `Processed through` + current descriptive layer — the LLM's exact input. |
| `update-apply` | Take LLM output (revised descriptive sections + one changelog line) on stdin or file; validate frontmatter/required sections; atomic tmp+rename write to live core; bump `Processed through`. |
| `migrate` | One-time, idempotent: split committed + live monolith into core + blog overlay (see Migration). |

Materiality (deterministic, replaces prose judgment): sync fires when, versus the committed
copies, (a) a new section heading exists, or (b) ≥3 trait bullets changed/added in the
descriptive layer since `Repo-synced through`, or (c) any overlay (prescriptive) file changed.

## Hooks

`~/.claude/settings.json` entries switch to the shims; shims are one-liners so the settings
command stays stable while the CLI evolves. Contract unchanged: never block, never emit
stdout, exit 0.

## Migration (`voicectl migrate` + repo edits)

1. Split `blog/references/voices/science-blog.md` (including pending uncommitted content):
   descriptive layer + AI-tells + provenance → `voice/references/voices/core.md`; prescriptive
   blog sections → `voice/references/voices/blog.md`. Same split for live `voice.md`.
2. Mint `research.md`, `chat.md`, `storycraft.md` prescriptive-only overlays, seeded from the
   existing register/professional sections and consumer docs; owner reviews before first push.
3. Markers carry over verbatim; corpus untouched.
4. Blog skill: remove `references/voice.md`, `references/voice-update.md`,
   `references/voices/`, `scripts/` voice tooling; SKILL.md points at `voicectl render blog`.
   scientific-study / storycraft / peer-review docs re-point to their overlays.
5. Live `voice.md` becomes rendered-blog compat output for one release, then dies.
6. Installer swaps hook commands; old bash removed from repo after one deprecation commit.

## Error handling

- capture/gate: exit 0 unconditionally; log failures to `sync.log`.
- update-apply: schema/section validation before write; atomic rename; on invalid input, exit
  nonzero and leave live profile untouched.
- sync: branch guard (clone must be on push target), fetch/reset only under AUTOREFRESH like
  today; any git failure logs and aborts without partial state (markers bump only after push
  succeeds).
- render: loud errors (unknown context, missing files, orphan override).

## Testing

- pytest unit: section parse/merge, marker read/bump, materiality diff, capture JSON handling,
  backfill dedupe.
- pytest integration: sync against a tmp bare repo + clone; gate launch decision matrix
  (count/interval/lock) with `VOICE_SYNC_LAUNCH` override.
- Installer idempotency test (ports existing `.test.sh`).
- `evals/evals.json` covers the agent-side update flow (prep → judge → apply).

## Consumers

- blog skill: `voicectl render blog`.
- scientific-study: `voicectl render research`.
- storycraft: `voicectl render storycraft` feeds persona/style-guide.
- ad-hoc chat/social writing: `voicectl render chat`.
