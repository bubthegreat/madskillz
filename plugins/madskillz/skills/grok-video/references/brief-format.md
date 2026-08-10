# Brief format & lifecycle

A "brief" is one Markdown file that describes the video for one scene. The user reviews
briefs before any generation. `generate.py` reads them and turns approved ones into clips.

## Location

Briefs live in the book's `video/` folder, one subfolder per chapter. The subfolder name
matches the chapter file name without `.md`. Scene numbers are zero-padded, matching the
chapter naming rule in storycraft's `repo-layout.md`.

```
<stories-repo>/<book-slug>/
  video/
    style-block.md            # shared style prefix (see consistency.md)
    01-<chapter-slug>/
      01-brief.md             # brief for scene 1
      01.mp4                  # generated clip (added by generate.py)
      02-brief.md
      02.mp4
```

## Template

```markdown
---
chapter: 01-the-accusation
scene: 1
duration: 4
aspect_ratio: "16:9"
resolution: 480p
status: draft
request_id: ""
error: ""
---
## Scene
Mar counts her socks and writes in her notebook at her desk.

## Motion & camera
Slow push-in from the doorway to the desk. Mar looks up once.

## Mood / palette
Warm bedroom lamplight; cozy, slightly comic.

## Characters present
Mar (girl, about 9, ponytail, striped socks, determined).

## Audio
Quiet room tone; pencil scratching. No dialogue.

## What NOT to show
Do not show the sock goblin yet.
```

## Frontmatter fields

| Field | Meaning |
|---|---|
| `chapter` | Chapter stem, e.g. `01-the-accusation`. |
| `scene` | Scene number from `scene_split.py`. Numbering must match the script's output. |
| `duration` | Clip length in seconds, 1–15. Default 4 — short clips iterate faster and cost less. |
| `aspect_ratio` | Default `"16:9"`. The API also accepts `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`. |
| `resolution` | `480p` (default), `720p`, or `1080p`. |
| `status` | Lifecycle state. See below. |
| `request_id` | Filled by `generate.py` right after submitting, so a crash can resume by polling. |
| `error` | Filled by `generate.py` when generation fails. Empty otherwise. |

## Status lifecycle

`draft → approved → generated | failed`

- **draft** — written by the skill. Never sent to the API.
- **approved** — the user approved this brief. Only approved briefs are generated.
- **generated** — a real mp4 exists on disk next to the brief. Terminal state.
- **failed** — the API reported failure, or the download could not complete. The `error`
  field holds the reason. To retry, the user (or the skill, on the user's explicit say-so)
  flips the status back to `approved`.

**Approval rule.** The `status` field is the single source of truth. It moves from `draft`
to `approved` in exactly two ways: the user edits the file, or the user gives explicit
approval in chat and the skill flips it, naming each file it flipped. The skill never
infers approval from silence.

## Prompt assembly order

`generate.py` builds the API prompt from each brief in this fixed order:

1. The full text of `video/style-block.md`.
2. The **Scene** section.
3. The **Motion & camera** section.
4. The **Mood / palette** section.
5. The **Characters present** section.
6. The **Audio** section.
7. The **What NOT to show** section, prefixed with `Do not show: `.

Empty sections are skipped. The order is fixed so that prompts are reproducible and the
style block always leads, which keeps the look consistent across scenes.
