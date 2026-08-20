---
voice: <name>
owner: <handle>
purpose: <what this context voice is for, in one line>
status: template
extends: core
---

# Voice: <name> - <one-line register description>

> **Copy this file to `references/voices/<name>.md`**, set `status: personal`, fill the
> frontmatter, and write only the **prescriptive** rules for this medium. The descriptive
> layer (how the owner actually talks) always comes from `core.md`; `voicectl render <name>`
> merges the two. Never present a template as the owner.

<Preamble: who the writer is in this register and what the artifact must achieve.>

## <Register rules>
- <How the core voice becomes good writing in this medium: what carries over, what switches
  off, structural moves, tone bounds.>
- <The AI-tells in core apply in every register - no need to restate them, but note anything
  this medium is especially prone to.>

<!-- To replace a core section instead of adding one, use the exact core heading and put
`<!-- override -->` as the first body line. -->
