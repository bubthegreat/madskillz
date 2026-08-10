# grok-video design — storycraft books → per-scene video clips via xAI API

**Date:** 2026-08-10
**Status:** approved, implementing

## Problem

Storycraft produces multi-chapter books in a stories repo. The owner wants short video
clips generated from those stories with Grok Imagine. Nothing in the repo does this today;
the closest prior art is storycraft's unimplemented illustration seam.

## Decisions (made with the owner)

| Question | Decision |
|---|---|
| How to reach Grok | xAI API with `XAI_API_KEY`. No browser automation. |
| Output shape | One clip per scene. A scene is a block between `---` lines in a chapter file. |
| Storage | Inside the stories repo: a per-book `video/` folder. Briefs and mp4s are committed, like `build/`. |
| Review gate | The skill drafts prompt briefs first. A human approves them. Only approved briefs are generated. |
| Defaults | 4 seconds, 480p, 16:9 — cheap and fast to iterate. The user opts into longer or sharper clips per brief. |

## API facts (verified 2026-08-10)

- `POST https://api.x.ai/v1/videos/generations` — model `grok-imagine-video-1.5`,
  fields `prompt`, `duration` (1–15 s), `aspect_ratio`, `resolution` (480p/720p/1080p).
  Optional: `image`, `reference_images`, `reference_audios`.
- Async. The POST returns `request_id`. Poll `GET /v1/videos/{request_id}`.
  Status is `pending`, `done`, `expired`, or `failed`.
- On `done`, the response holds a temporary `video.url`. Download it right away.
- Generation can take several minutes per clip.

## Shape

New skill at `plugins/madskillz/skills/grok-video/`:

- `SKILL.md` — six phases: preflight → scene inventory → style block → draft briefs →
  human review gate → generate + commit. Integrity stance mirrors storycraft and
  promote-study-to-public: never fake success, commit but never push.
- `references/brief-format.md` — brief template, `status` lifecycle
  (`draft → approved → generated | failed`), and the fixed prompt assembly order.
- `references/grok-api.md` — endpoint, polling, statuses, error handling.
- `references/consistency.md` — the shared style block (v1 continuity answer) and
  documented-but-unbuilt v2 seams: image-to-video, per-character reference images,
  last-frame chaining.
- `scripts/scene_split.py` — pure-stdlib scene parser; JSON inventory out.
- `scripts/generate.py` — submits approved briefs, saves `request_id` immediately,
  polls, downloads, flips status. Idempotent. `--dry-run`, `--max-clips` (default 5).

Book-side layout (extends the storycraft layout):

```
<stories-repo>/<book-slug>/video/
  style-block.md
  01-<chapter-slug>/
    01-brief.md
    01.mp4
```

The `status` field in each brief's frontmatter is the single source of truth for approval.
The skill may flip `draft → approved` only on an explicit user approval in chat.
`generate.py` only processes `approved` briefs, so a stray draft can never cost money.

## Out of scope (v2 seams, documented in consistency.md)

- Image-to-video and reference images for tighter character continuity.
- Last-frame chaining between consecutive scenes.
- Voice via `reference_audios`.
- Stitching clips into one film per chapter or a book trailer.
