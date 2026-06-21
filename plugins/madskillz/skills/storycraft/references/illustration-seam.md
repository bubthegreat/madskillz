# Illustration seam (v2 hook)

> **Status: NOT IMPLEMENTED in v1.**
> This document records the intended extension point so a future implementer knows exactly where
> illustrations plug in and what the contract looks like. Nothing here is active.

## What is deferred

Illustrations — AI-generated or hand-drawn images embedded in the book — are **out of scope for v1**.
The fixed-layout illustrated PDF path (where images are placed at specific page positions) is also
**deferred to v2**.

v1 renders reflowable EPUB and typeset PDF with no images.

## The seam: `illustrate` in `book.yaml`

The `book.yaml` field `illustrate` is already defined in the schema (see `repo-layout.md`):

```yaml
illustrate: false   # v1 default — set true to activate illustration pipeline (v2+)
```

When `illustrate: false` (the v1 default), the renderer ignores any `art/` content and produces
text-only output. The field is present in the schema so that v2 can toggle it without a schema
migration.

## Intended v2 design (not implemented)

### Per-chapter art briefs

Each chapter would gain an `art/` subfolder alongside the chapter file:

```
chapters/
  01-opening.md
  art/
    01-brief.md       # art direction brief for this chapter's illustration(s)
    01-cover.png      # rendered image (added after generation)
```

`01-brief.md` would be produced by a future **Illustration Designer** persona — a subagent that
reads the chapter, the style guide, and any visual canon from the bible, then writes a structured
brief:

```markdown
# Art brief — chapter 01

## Scene
The goblin scouts huddled under a mushroom in the rain, Pip clutching the map.

## Mood / palette
Warm lamplight against cold blue-grey rain; slightly desaturated except the lantern glow.

## Style notes
Ink-line children's-book illustration; no photorealism; friendly, slightly comic.

## Characters present
Pip (small, eager, wide hat); Morg (tall, skeptical, arms folded).

## What NOT to show
Do not show the cave entrance — that is revealed in chapter 03.
```

The brief is committed and reviewed by the human before any image generation is triggered. The
human (or a future image-gen subagent) produces the image and places it in `art/`.

### Fixed-layout PDF

With illustrations active, the PDF target would switch from Typst's default typeset flow to a
**fixed-layout** template: each chapter spread is sized and images are anchored to specific
positions. The exact Typst template for this is **not designed yet** and is part of the v2 scope.

The EPUB path with illustrations would use an EPUB 3 fixed-layout manifest — also **not
implemented** and deferred.

### Render integration point

`scripts/render.py` already reads `book.yaml`. The v2 integration point is:

```python
# v2 hook (not implemented): read meta["illustrate"] and branch
if meta.get("illustrate"):
    render_illustrated(book_dir, out_dir, meta)   # fixed-layout path
else:
    render_text_only(book_dir, out_dir, meta)     # v1 path (current)
```

No code change is needed in v1; the `else` branch is the entire current implementation.

## Summary of what is and is not in scope

| Capability | v1 | v2 (deferred) |
|---|---|---|
| Text-only EPUB (reflowable) | Implemented | — |
| Text-only PDF (Typst, typeset) | Implemented | — |
| `illustrate` field in `book.yaml` schema | Defined (always `false`) | Activated |
| Per-chapter art briefs (`art/NN-brief.md`) | Not implemented | Illustration Designer persona |
| Fixed-layout illustrated PDF | Not implemented | v2 Typst template |
| Fixed-layout illustrated EPUB | Not implemented | v2 EPUB 3 fixed-layout |
| Image generation subagent | Not implemented | Out of scope for v2 design |
