# Blog format — post arc and blog-notes

Shapes the `blog` skill produces. The **voice** lives in `voice.md` (seed) and the live profile at
`~/.madskillz/voice/voice.md`; this file is **structure**.

## The post

Follow this arc (the voice file's signature arc, as sections). These are **structural beats, not
labels** — never name a beat in the prose (no "record scratch moment", no "here's the hook").

1. **Hook** — a vivid wrong intuition, a dumb-on-purpose question, or a "so I asked…" cold open.
2. **Backstory** — why I was even on this, and enough plain-language grounding that a reader with
   **no background at all** can follow. Assume curiosity, never knowledge. If the topic needs a
   concept to make sense (what a black hole *is*, what "orbit" means here), build it before using it.
3. **The mental model I walked in with** — what I assumed; relatable and usually wrong.
4. **The turn** — where it turns out that's not how it works. Arrives naturally, in the flow of the
   story. **Not every journey has one** — some are "it's more subtle than I thought" or "it's true
   but for the wrong reason"; don't force a reversal that didn't happen.
5. **What's actually going on** — the real thing, plain and *correct*, wonder intact. This is the
   heart of the post: after a correction, **slow down and be fully descriptive** — unpack the
   mechanism step by step until a general reader actually gets it, not just believes it. A gloss for
   every technical term. **Real sources as inline hyperlinks, crediting the people who figured it
   out**, placed where each idea shows up — the reader should be able to walk the same journey
   through the sources; unlinked claims read as "trust me bro."
6. **Why it's cool / how it reframed me** — the payoff: reality beat my guess.
7. **Kicker** — a punchy close; often "…and now I'm confused about *this* next."

Length: whatever the journey earns — usually 500–1200 words. No padding, but backstory and the
post-correction explanation are **not** padding; cutting them to hit a word count is the failure mode.

**Posts based on a study must link the actual published study** (footer at minimum) so genuinely
interested readers can go read the full work, and **pull in the study's figures where they exist**
(`assets/`) at the matching narrative points, with captions in the owner's voice — copy the images
into the post's folder so it stays self-contained. Prefer the public location
(`jmresearch/research-public`) when the study has been promoted; otherwise link the study's home
repo and swap in the public link once it exists.

## blog-notes

One entry per genuinely-interesting question/correction, ranked by merit (best first):

```
## <short title>
- Question I asked: <verbatim-ish>
- What I assumed: <prior mental model>
- The correction: <what's actually true>
- Why it's interesting (merit): <surprise / hook strength / how much it reframed things>
- Source: <session turn | study artifact | note>
- Status: strong | maybe | thin
```

Rank by merit; `thin` notes are kept but not necessarily used. Never invent a note to fill space.
