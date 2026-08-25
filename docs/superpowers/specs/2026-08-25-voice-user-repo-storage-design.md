# Voice: user-owned repo storage — design spec (2026-08-25)

Make the `voice` skill usable by anyone, on any number of machines, without new infrastructure.
Today the skill and the owner's personal voice data are one thing: profiles are committed
inside the plugin repo, the sync path pushes to `bubthegreat/madskillz` `main`, and nothing
ever pulls. This spec separates the **skill** (code + templates, shipped in madskillz) from the
**voice store** (one private git repo the user owns) and makes that store the single source of
truth across machines.

Supersedes the storage parts of `2026-08-19-voice-system-design.md`; render/update/gate
behavior is unchanged except where stated.

## Problems being fixed

1. **Data inside the skill repo.** `voicectl sync` copies live profiles into
   `plugins/madskillz/skills/voice/references/voices/` and pushes to the plugin's `main`.
   Any other user's voice would land in the plugin. The dedicated `madskillz-sync` clone and
   the CLAUDE.md exception exist only to make that push work.
2. **No pull.** `init` never overwrites, `sync` copies live → committed unconditionally. Two
   machines clobber each other's trait updates.
3. **Corpus is per-machine, marker is global.** `Processed through` is one timestamp;
   machine B's older unprocessed prompts are skipped forever after machine A advances it.
4. **Owner hardcoded.** `owner: bubthegreat` in profiles, default remote in the installer,
   `VOICES_SUBPATH` pointing into the plugin tree.
5. Cruft: `voice.md` compat render, `posts/` in the voice dir.

## Goals

- Skill ships **templates only**; a user's real profiles never enter the plugin repo.
- One voice store per user, any git remote (GitHub private, GitLab, bare repo on a NAS).
  Auth is whatever `git` already has. No new services.
- N machines converge on one core, one overlay set, one corpus, one marker.
- Corpus (verbatim prompts) is treated as sensitive: private remote enforced by default.
- Existing consumers (`voicectl render <ctx>`) unchanged.

## Non-goals

- No hosted endpoint. Layout is chosen so one could sit behind the same CLI later.
- No PR-based review of voice changes; the store is single-user and pushes direct.
- No change to render/merge rules, corpus line format, or the LLM judgment guidance.

## Layout

### Skill (madskillz)

```
plugins/madskillz/skills/voice/
  SKILL.md
  references/
    voice-update.md
    voice-overlay-template.md
    voices/                 # TEMPLATES ONLY: status: template, owner: <handle>
      core.md               # section skeleton + AI-tells defaults, descriptive bullets empty
      blog.md  research.md  chat.md  storycraft.md
  cli/                      # voicectl (unchanged package layout)
  hooks/                    # shims, unchanged
  scripts/install_voice_pipeline.sh
```

### Voice store (user repo, cloned to `~/.madskillz/voice/`)

```
core.md                     # live core (status: personal, owner: <user>)
<context>.md                # live overlays
corpus.jsonl                # append-only {ts,text}; merge=union
.gitattributes              # corpus.jsonl merge=union
.gitignore                  # sync.log .sync.lock .last-sync-attempt tool/ *.tmp
README.md                   # generated: what this repo is, "private, contains prompts"
```

The live dir **is** the clone. Runtime files (`sync.log`, lock, stamp, `tool/`) stay in the
dir but are gitignored. The `madskillz-sync` clone is deleted.

## Configuration

`~/.madskillz/voice/.git` presence + `origin` define the store. Two modes:

- **Synced:** `origin` set. `pull`/`push` run at the points below.
- **Local-only:** no `.git` or no `origin`. Sync steps are no-ops that print one line
  (`sync: local-only mode (no remote); run 'voicectl init --remote URL' to sync`).

Tunables move from ad-hoc env to `voicectl config` (stored as `voice.*` keys in the store
clone's local git config: per-machine, never committed):

| key | default | meaning |
|---|---|---|
| `voice.model` | `opus` | model for the detached updater |
| `voice.minCount` | `15` | gate: pending messages before an update |
| `voice.minInterval` | `720` | gate: seconds between attempts |
| `voice.corpusSync` | `true` | commit/push `corpus.jsonl` |

Env vars (`VOICE_DIR`, `VOICE_SYNC_*`) remain as overrides for tests and power users.

## CLI changes

| Command | Behavior |
|---|---|
| `init [--remote URL] [--allow-public]` | If `--remote`: clone into `VOICE_DIR` (or, if the dir exists without `.git`, `git init` + `remote add` + fetch, then adopt existing files). Empty remote → first commit + push. Then seed any missing profile from the skill templates, replacing `owner: <handle>` with `git config user.name`. Write `.gitattributes`/`.gitignore`/`README.md` if missing. **Visibility check** (below). Without `--remote`: seed templates into a plain dir (local-only). Idempotent. |
| `pull` | `git pull --rebase --autostash origin <branch>`. Conflict on `corpus.jsonl` cannot happen (union). Conflict on any `.md`: abort rebase, keep **remote** version, print which files and exit 2. Never leaves the repo mid-rebase. |
| `push` | `git add -A` (minus gitignored) → commit `voice: update (<host>)` if dirty → `git push`. Rejected push → `pull` → retry once. Exit nonzero on failure; live files untouched. |
| `sync` | `pull` then `push`. Replaces today's materiality-gated copy. Materiality logic is deleted from `sync.py`; it survives only as the gate's spend check. |
| `update-prep` | Runs `pull` first (synced mode). If pull exits 2 (core conflict resolved to remote), prep continues against the remote core — the correct base. Then as today. |
| `update-apply` | As today, then `push`. Push failure after a successful apply is reported but the local apply stands; next `sync`/gate retries. |
| `status` | Adds `mode` (`synced`/`local-only`), `remote`, `ahead/behind`, `dirty`. Drops `material`/`materiality_reasons`. |
| `config [key [value]]` | Read/write the `voice.*` keys. |
| `migrate-to-repo --remote URL` | One-shot for existing installs: back up `VOICE_DIR` to `VOICE_DIR.bak-<ts>`, `git init` in place, add remote, drop `voice.md`, `posts/`, `madskillz-sync/`, first commit + push. Refuses if remote is non-empty and not a voice store (no `core.md` at root). |
| `gate` | Unchanged decision logic; reads tunables from `config`; no longer resets any repo. Detached updater's `cd` target becomes `VOICE_DIR`. |
| `backfill` | Unchanged; runs before first `push` in the installer so history seeds the store. |

`paths.sync_repo()`, `paths.sync_branch()`, `VOICES_SUBPATH`, and `NON_OVERLAY["voice.md"]`
are removed. `templates_dir()` is added: the skill's `references/voices/` (resolved from the
installed tool copy, `VOICE_DIR/tool/templates/`).

## Multi-machine semantics

- **Corpus:** `merge=union` in `.gitattributes`. Both machines' appends survive; order is
  by file position, and every reader already filters by `ts`, so interleaving is fine.
  Union can duplicate a line both sides added identically (e.g. a corpus copied to two
  machines before migration); `corpus.entries()` therefore dedupes on `(ts, text)`.
- **Core / overlays:** updates are serialized by `pull` before `update-prep` and `push` after
  `update-apply`. The race window is one LLM run. If two machines still collide, the loser's
  push is rejected, its `pull` hits a core conflict, remote wins, exit 2. Nothing is lost:
  the loser's new corpus lines merged via union, so the next update on either machine
  re-judges them (its `Processed through` is the remote's, which predates them).
- **Marker:** single `Processed through` in the shared core, meaningful because the corpus is
  shared. With `voice.corpusSync=false` the marker is **per-remote, corpus per-machine** and
  older local messages can be skipped; the CLI prints this warning when the key is set and
  `status` shows `corpus: local (lossy across machines)`.

## Privacy

- `init --remote` runs a visibility check: for `github.com` remotes, `gh repo view --json
  visibility` (if `gh` present); otherwise skipped with a printed notice. `PUBLIC` → refuse
  unless `--allow-public`. Other hosts: trust the user, print the notice.
- Generated `README.md` states the repo holds verbatim prompts and must stay private.
- `voice.corpusSync=false` keeps prompts off the remote at the cost above.

## Installer

`install_voice_pipeline.sh` steps become: voice dir → uv tool (copies `cli/` **and**
`references/voices/` into `tool/templates/`) → hooks + settings wiring (unchanged) →
`voicectl init [--remote "$VOICE_REMOTE"]` → `voicectl backfill` → `voicectl push`.
`VOICE_REMOTE` unset = local-only, with a printed hint. The `madskillz-sync` step is removed.
Settings.json `SessionEnd` command loses `VOICE_SYNC_REPO`/`VOICE_SYNC_AUTOREFRESH`; the
installer rewrites an existing entry that still carries them (matched by script name).

## Owner migration

1. Create private `bubthegreat/voice` (empty).
2. `voicectl migrate-to-repo --remote git@github.com:bubthegreat/voice.git`.
3. In madskillz: replace `references/voices/*.md` with templates (descriptive bullets and
   changelog removed, `status: template`, `owner: <handle>`); delete the CLAUDE.md
   `voice-sync` exception; update the `voice-system-voicectl` memory.
4. Re-run the installer on each machine; on the second machine `init --remote` clones the
   store and its local corpus is backfilled + pushed (union merge).

## Error handling

- `pull`/`push` never leave a half-rebase; on any git failure the working tree is restored
  (`rebase --abort`, autostash pop) and the command exits nonzero with the git stderr.
- Offline: `pull` fails fast (fetch error) → `update-prep` continues against the local core
  with a printed warning; `update-apply` applies locally and reports the unpushed state.
- `capture`/`gate` keep the hook contract: exit 0, nothing on stdout, errors to `sync.log`.
- `render` unchanged.

## Testing

- pytest, against tmp bare repos: `init` (empty remote, existing remote, existing dir
  adoption, local-only), `pull`/`push` (clean, rejected-then-rebased, core conflict → remote
  wins + exit 2, corpus union on concurrent appends from two clones), `sync` idempotence,
  `migrate-to-repo` (backup created, cruft dropped, refuses foreign non-empty remote),
  visibility check with a stubbed `gh`, `config` round-trip, `status` fields.
- Gate decision matrix unchanged; `VOICE_SYNC_LAUNCH` override kept.
- Installer idempotency test extended for the `init`/`backfill`/`push` steps
  (`VOICE_INSTALL_NO_CLONE` becomes "no remote").
- Two-machine integration test: two clones of one bare repo, interleaved
  capture → update-apply on each, assert both converge on identical `core.md` and a corpus
  containing every line from both.

## Consumers

Unchanged: `voicectl render blog|research|chat|storycraft`. SKILL.md "Machine setup" gains
the `VOICE_REMOTE` line and a "second machine" paragraph.
