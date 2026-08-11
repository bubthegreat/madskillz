# Clips mode — the lightweight lane

Clips mode turns a storycraft book into one continuous per-scene video without the full
production pipeline. No shot list, no casting plates. One brief per scene, a human
approval gate, then generation builds the video **intentionally**: the first scene is a
fresh generation and every following scene **extends** the previous one from its final
frame, so motion and look flow scene to scene. Segments concatenate into one film with
no jump cuts. Use it to see a story move, iterate on look fast, or preview before
committing to a full film. `--independent` opts out of chaining for isolated clips.

## Clips mode vs full pipeline

| | Clips mode | Full pipeline |
|---|---|---|
| Input | A storycraft book's chapters | Beat sheet + shot list (`shots.yaml`) |
| Unit | One segment per scene (`---` breaks), extend-chained | One clip per shot |
| Continuity | Extend chain (last-frame continuation) + shared style block | Lockups + reference plates + QA |
| Cost control | 4s/480p defaults, `--max-clips` cap, approval gate | `estimate_cost.py` + `budget_usd` hard stop |
| Storage | The book's own stories repo, `video/` folder | Separate films repo |
| Output | Loose per-scene mp4s | An assembled, conformed cut |

**Routing rule.** "Make videos / clips from my story," "animate chapter 2" → clips mode.
"Make a film / short / movie," "build a shot list," anything that needs cuts that match →
full pipeline. When a clips-mode user starts asking for shot-to-shot continuity, dialogue
timing, or an assembled cut, say plainly that they have outgrown clips mode and offer the
full pipeline (adapt via `storycraft-handoff.md`; existing briefs inform the beat sheet).

## Storage

Clips mode stores everything in the **book's own stories repo** (from
`~/.claude/storycraft/config.yaml` — the storycraft config; filmcraft's films repo is not
involved):

```
<stories-repo>/<book-slug>/video/
  style-block.md
  01-<chapter-slug>/
    01-brief.md
    01.mp4
```

Briefs **and mp4s are committed**, mirroring how storycraft commits `build/` artifacts so
they sync via the repo. This is a deliberate exception to the full pipeline's
never-commit-raw-takes rule: clips-mode output is a handful of 4-second 480p files
(a few MB each), not fifty takes of 720p footage. If a book accumulates enough video to
strain the repo, that is the signal it has outgrown clips mode.

Commits use storycraft's message form: `book: <slug> video briefs ch.NN (draft)`,
`book: <slug> video ch.NN`. Never push.

## Phase C0 — Locate & preflight

Resolve the stories repo, pick the book, check it has `chapters/*.md`. Check
`XAI_API_KEY` (or `GROK_API_KEY`) is set; if not, say so now — briefs can still be drafted, but generation is
blocked until the key is exported. Resumable from on-disk state: existing briefs and mp4s
under `video/` show what is drafted, approved, and generated. Never redo finished work.

## Phase C1 — Scene inventory

```
uv run scripts/scene_split.py <book_dir> [chapter-prefix]
```

Show the user a table: chapter, scene number, first line, word count. The user picks
which chapters or scenes to animate. Do not assume "all of them" unless the user says so.
The script's scene numbering is canonical; briefs must use it.

## Phase C2 — Style block

Create or refresh `video/style-block.md` from `bible/style-guide.md` and
`bible/characters.md`: art style (one or two sentences), palette (one sentence), and one
visual sentence per recurring character — appearance only, no personality or plot. Keep
it under ~120 words; it competes with the scene text for the model's attention.

It is prepended verbatim to every prompt, so continuity decisions live in one place.
When the user wants a look change, edit the style block, not the individual briefs.

**Checkpoint:** the user approves the style block before briefs are drafted.

## Phase C3 — Draft briefs

For each chosen scene, write `video/<chapter-stem>/<SS>-brief.md` per
`clips-brief-format.md`, with `status: draft`. Draft from the scene's actual text plus
the bible: which characters appear, and what later plot the clip must not reveal (check
`bible/outline.md` — spoilers go in **What NOT to show**).

Defaults: 4 seconds, 480p, 16:9 — cheap and fast to iterate. Only raise duration or
resolution when the user asks.

Commit: `book: <slug> video briefs ch.NN (draft)`.

## Phase C4 — Human review gate (hard gate)

Present the briefs (or a digest plus file paths). The user edits the files directly or
gives approval in chat. On chat approval, flip each named brief to `status: approved` and
say which files were flipped. The `status` field is the single source of truth;
`clips_generate.py` only processes `approved` briefs, so a stray draft can never cost
money. Never infer approval from silence.

## Phase C5 — Generate

First show the cost summary and get a yes: "N clips × D seconds at R resolution.
Generate now?"

```
uv run scripts/clips_generate.py <book_dir> [--chapter NN-slug] [--max-clips N]
```

The script submits briefs in story order through `grok_client` (the wire-format
quarantine applies here too). The first scene is a fresh generation; each later scene is
submitted to `/v1/videos/extensions` with the previous segment's delivered URL, so it
continues from that segment's final frame. The `request_id` is saved into the brief
immediately; each segment downloads next to its brief; `mode: fresh|extend` is recorded
in the frontmatter. `--dry-run` prints the assembled prompts and which mode each scene
would use — useful at the C4 checkpoint.

Chain rules, stated honestly in the summary output:

- **Failure breaks the chain.** A failed or still-pending scene stops everything after
  it (`not attempted (chain broken upstream)`) — extending from a missing segment is
  impossible, and silently restarting fresh would break the intentional build.
- **Delivered URLs are temporary**, so chains cannot cross runs. A scene generated in an
  earlier run is skipped and the chain restarts fresh at the next scene. For one fully
  continuous film, generate the whole scene list in one run.
- Extensions add the brief's `duration` seconds to the film; `resolution` follows the
  chain root, so only the first (fresh) brief's `resolution` matters.
- Extensions use the base `grok-imagine-video` model — `grok-imagine-video-1.5` refuses
  extension (live-verified). `grok_client.EXTEND_MODEL` owns this.

Failed briefs keep `status: failed` and the API's error text until the user asks to
retry (flip back to `approved`).

**No assembly needed.** Extension output is cumulative (live-verified): each delivered
segment contains all footage so far, so the last chained segment is the whole film.
`clips_generate.py` copies it to `video/<book-slug>.mp4` automatically ("complete" when
every scene chained, "partial" when the chain stopped early). Per-scene mp4s are kept as
resumable checkpoints — scene N's file is the film through scene N.

Commit briefs + mp4s: `book: <slug> video ch.NN`. Never push.

## Continuity upgrades (use the full pipeline instead)

The extend chain plus the style block are clips mode's continuity tools, by design.
Per-character reference images, casting plates, multi-take QA, and voice all live in the
full pipeline (`casting.md`, `grok-api.md` modes table). If a clips-mode user needs
those, that is the outgrown-it signal — route to the full pipeline rather than bolting
plates onto briefs.
