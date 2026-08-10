---
name: grok-video
description: >-
  Use when the user wants to turn a storycraft book or chapter into short video clips —
  "make videos from my story," "animate chapter 2," "grok video," "turn my book into
  clips." Splits chapters into scenes at `---` breaks, drafts one prompt brief per scene,
  gets human approval, then generates per-scene mp4s with xAI's Grok Imagine video API
  (needs XAI_API_KEY). Stores briefs and mp4s in the book's video/ folder; commits but
  never pushes. Not for writing prose (storycraft) or still illustrations.
---

# grok-video: per-scene video clips from a storycraft book

Turn a finished (or in-progress) storycraft book into short video clips. One clip per
scene. The user reviews every prompt brief before a single API credit is spent.

The pipeline: locate the book → inventory its scenes → agree a shared style block →
draft one brief per scene → **human approval gate** → generate, download, commit.

## Relationship to the family

- **storycraft** writes the books this skill animates. It owns the stories repo layout
  and the `~/.claude/storycraft/config.yaml` config; this skill reuses both and adds a
  per-book `video/` folder.
- `scripts/scene_split.py` and `scripts/generate.py` are deterministic tools this skill
  invokes; LLM judgment (drafting briefs) builds on their output.
- `references/consistency.md` documents the v2 seams (image-to-video, reference images,
  last-frame chaining, voice, stitching). Do not implement them in v1.

## Integrity stance (non-negotiable)

1. Never fake a generation, a download, or an API response. Report the real state or the
   real failure, including the API's own error text.
2. Money gate: nothing is submitted to the API without an explicit user approval of the
   briefs **and** a per-run cost confirmation. `generate.py` only processes briefs with
   `status: approved`, so a stray draft can never cost money.
3. The skill may flip a brief from `draft` to `approved` only in direct response to an
   explicit user approval in chat, and it names each file it flipped.
4. Commit at checkpoints with `book: <slug> <what>` messages. **Never push.**
5. Never mark a brief `generated` unless the mp4 really exists on disk.

## Phase 0 — Locate the book & preflight

Resolve the stories repo from `~/.claude/storycraft/config.yaml` (storycraft's config —
do not create a second config file). If it is missing, resolve it the same way
storycraft's `repo-layout.md` does. Pick the book slug with the user.

Preflight checks, in order, before any drafting work:

1. The book folder exists and has `chapters/*.md`.
2. `XAI_API_KEY` is set (`echo ${XAI_API_KEY:+set}`). If unset, tell the user now —
   briefs can still be drafted, but generation will be blocked until the key is exported.

The skill is resumable from on-disk state: existing briefs and mp4s under `video/` show
what is drafted, approved, and generated. Never redo finished work.

## Phase 1 — Scene inventory

```
uv run plugins/madskillz/skills/grok-video/scripts/scene_split.py <book_dir> [chapter-prefix]
```

Show the user a table: chapter, scene number, first line, word count. The user picks
which chapters or scenes to animate. Do not assume "all of them" unless the user says so.

## Phase 2 — Style block

Create or refresh `video/style-block.md` from `bible/style-guide.md` and
`bible/characters.md`, following `references/consistency.md` (art style, palette, one
visual sentence per character; under ~120 words). Present it to the user for review.
This file is prepended to every prompt, so it is the one place continuity decisions live.

**Checkpoint:** the user approves the style block before briefs are drafted.

## Phase 3 — Draft briefs

For each chosen scene, write `video/<chapter-stem>/<SS>-brief.md` per
`references/brief-format.md`, with `status: draft`. Draft from the scene's actual text
plus the bible: which characters appear, and what later plot the clip must not reveal
(check `bible/outline.md` — put spoilers in **What NOT to show**).

Defaults: 4 seconds, 480p, 16:9 — cheap and fast to iterate. Only raise duration or
resolution when the user asks.

Commit: `book: <slug> video briefs ch.NN (draft)`.

## Phase 4 — Human review gate (hard gate)

Present the briefs (or a digest plus file paths). The user edits the files directly or
gives approval in chat. On chat approval, flip each named brief to `status: approved` and
say which files were flipped. Unapproved briefs stay `draft` and are never generated.

## Phase 5 — Generate

First show the cost summary and get a yes:

> N clips × D seconds at R resolution. Generate now?

Then:

```
uv run plugins/madskillz/skills/grok-video/scripts/generate.py <book_dir> [--chapter NN-slug] [--max-clips N]
```

The script submits each approved brief, saves the `request_id` into the brief
immediately, polls until done, downloads the mp4 next to the brief, and flips the
status. It is idempotent — re-running skips generated clips and resumes pending ones.
Details and failure handling: `references/grok-api.md`.

Report the script's real per-scene summary. If some clips failed, say exactly which and
why; failed briefs keep `status: failed` until the user asks to retry (flip back to
`approved`).

Commit briefs + mp4s: `book: <slug> video ch.NN`. Never push.

## Scripts

Both use PEP 723 inline deps; run via `uv run`.

- `scene_split.py <book_dir> [chapter-prefix]` — JSON scene inventory. Splits at `---`
  lines, skipping YAML frontmatter and fenced code blocks. Its numbering is canonical;
  briefs must use it.
- `generate.py <book_dir> [--chapter NN-slug] [--dry-run] [--max-clips N] [--base-url URL]`
  — the generator. `--dry-run` prints the assembled prompts and touches nothing (use it
  to sanity-check prompts at the Phase 4 checkpoint). `--max-clips` defaults to 5.

## Edge cases

- **No stories repo / no book** → resolve per storycraft's `repo-layout.md`; this skill
  does not create books, it animates existing ones. Route "write me a story" to storycraft.
- **Missing `XAI_API_KEY`** → draft briefs if the user wants, but say clearly that
  generation is blocked until the key is exported. Never pretend a clip was made.
- **Scene numbering drift** (chapter edited after briefs were drafted) → re-run
  `scene_split.py`; if scenes moved, surface the mismatch and re-draft affected briefs
  with the user rather than silently regenerating.
- **Clip still pending after timeout** → the brief keeps its `request_id`; re-running
  `generate.py` resumes polling without paying twice.
- **User asks for illustrations** → that is storycraft's illustration seam, not this
  skill; explain and route.
- **User asks to stitch clips into one film** → v2 seam (`references/consistency.md`);
  say it is not built yet.
