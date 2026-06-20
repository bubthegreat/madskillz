# Blog format — post arc, blog-notes, transcript

Shapes the `research-blog` skill produces. The **voice** lives in `blog-voice.md`; this file is
**structure**.

## The post (`blog/post-<slug>.md`)

Follow this arc (the voice file's signature arc, as sections):

1. **Hook** — a vivid wrong intuition, a dumb-on-purpose question, or a "so I asked…" cold open.
2. **The mental model I walked in with** — what I assumed; relatable and usually wrong.
3. **The record scratch** — the moment it turns out that's not how it works. The correction.
4. **What's actually going on** — the real science, plain and *correct*, wonder intact. A gloss for
   every technical term; a real source or an honest "read up on X" where background is needed.
5. **Why it's cool / how it reframed me** — the payoff: reality beat my guess.
6. **Kicker** — a punchy close; often "…and now I'm confused about *this* next."

Length: whatever the journey earns — usually 500–1200 words. No padding.

## blog-notes (`blog/blog-notes.md`)

One entry per genuinely-interesting question/correction, ranked by merit (best first):

```
## <short title>
- Question I asked: <verbatim-ish>
- What I assumed: <prior mental model>
- The correction: <what's actually true>
- Why it's interesting (merit): <surprise / hook strength / how much it reframed things>
- Source: <session turn | study artifact | transcript line>
- Status: strong | maybe | thin
```

Rank by merit; `thin` notes are kept but not necessarily used. Never invent a note to fill space.

## transcript (`journey/transcript.md`)

An append-friendly, speaker-tagged dialogue log — **substance only**:

```
# Journey transcript — <topic>/<short-name>
<!-- Provenance: the human<->assistant dialogue behind this study. NOT part of paper.md. -->

## <YYYY-MM-DD> <short context>
**Me:** <the question / direction / pushback, substance preserved>
**Assistant:** <the substantive answer / correction — not tool calls, not bookkeeping>
```

- Include the owner's questions, direction, and pushback; the substantive replies and corrections.
- Exclude tool-call noise, file diffs, and mechanical chatter — a record of the *thinking*, not a
  system log.
- Append across runs; never rewrite history. In backfill mode, reconstructed turns are marked
  `(reconstructed from artifacts)` and unrecoverable gaps are stated, never invented.
