# Visual consistency across scenes

Each scene is a separate API call. Nothing ties one call to the next, so characters and
style can drift between clips. This document is the v1 answer and the v2 seams.

## v1: the shared style block (implemented)

`video/style-block.md` is one short file, prepended verbatim to **every** prompt
(see the assembly order in `brief-format.md`). It holds:

1. **Art style** — one or two sentences, e.g. "Hand-drawn children's-book animation look.
   Soft ink lines, watercolor fills. No photorealism."
2. **Palette** — the book's palette in one sentence.
3. **Character sheet** — one visual sentence per recurring character, taken from
   `bible/characters.md`. Appearance only (build, hair, clothing, signature props) —
   no personality or plot.

Build it in Phase 2 from `bible/style-guide.md` and `bible/characters.md`. The user
reviews it **once**; after that, every clip inherits it. When the user wants a look
change, edit the style block, not the individual briefs — that keeps continuity
decisions in one place.

Keep it under ~120 words. The style block competes with the scene text for the model's
attention; a bloated block washes out the scene.

## v2 seams (documented, NOT implemented)

Do not build these in v1. They are recorded so a future implementer knows where they plug in.

### Image-to-video

The API accepts an `image` field: the model animates a supplied first frame. The brief
frontmatter reserves an `image:` key for this. When set to a path, `generate.py` would
upload that frame instead of relying on text alone. Best for scenes where a prior still
(or a chapter illustration from storycraft's illustration seam) already exists.

### Per-character reference images

The API accepts `reference_images`. The seam: a `video/refs/` folder with one canonical
image per character, listed in the style block, wired to the API field. This is the
strongest fix for character drift.

### Last-frame chaining

For consecutive scenes in one chapter: extract the final frame of clip N (ffmpeg) and
pass it as the `image` for clip N+1. Gives real shot-to-shot continuity. Needs ffmpeg
on PATH and careful handling when a middle scene fails or is regenerated.

### Voice

The API accepts `reference_audios` (up to 3 voices) for dialogue. Out of scope for v1;
briefs default to ambient audio and no dialogue.

### Stitching

Concatenating per-scene clips into one film per chapter (or a book trailer) is a plain
ffmpeg concat once clips exist. Deferred until the per-scene flow has proven itself.
