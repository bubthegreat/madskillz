---
name: research-blog
description: >-
  Use when the user wants to turn a research idea or study into a personal blog post in their own
  voice — "blog the journey," "write up what I learned," "turn this into a blog post," "make this
  fun to read," or "blog this study." Also saves the human<->assistant dialogue as a study
  transcript. Trigger on phrases like "blog the journey," "write up what I learned," "turn this
  into a blog post," or "blog this study." Writes the post and saves it; the human publishes it.
---

# research-blog: the learning journey, in your voice

Turn a research journey into a neat, funny, genuinely-illuminating **blog post written as the
owner** — first person, their voice — so a curious general reader comes away feeling that science is
cool. The arc is the journey itself: *I thought X -> turns out no -> here's what's actually going on
-> and it's cooler than my wrong version -> here's how it rewired me.* Alongside the post, save the
human<->assistant **dialogue** as study provenance, so it is clear which thinking was the owner's and
where the AI did the heavy lifting.

The voice lives in `references/blog-voice.md`; the output shapes in `references/blog-format.md`.

## Integrity stance (non-negotiable)
1. **The science is correct even when it's funny.** Comedy never licenses a wrong explanation. If the
   corrected understanding is itself simplified or uncertain, say so *in voice*.
2. **The journey is real.** Blog-notes come from actual questions/corrections — never an invented
   misconception or a fabricated aha. Reconstructed pieces (backfill) are labeled; gaps are stated.
3. **Written as the owner, not putting claims in their mouth.** Consolidate their real
   questions/feedback; flag anything you infer rather than quote.
4. **Honest open threads stay in.** "I still don't fully get Y" is a feature and it's true.
5. **No fabricated citations.** A real, resolvable source, or an honest "read up on X."

## Step 1 - Gather the journey and save the transcript
Identify the source(s): the live session, a study folder's artifacts (`paper.md`, `review/cycle-*`),
and/or a previously saved transcript. Write or append `journey/transcript.md` per
`references/blog-format.md` - the human<->assistant dialogue (questions, direction, pushback;
substantive replies and corrections), excluding tool-call noise. This transcript is study
provenance: committed with the study, **not** part of `paper.md`, and **not** subject to a privacy
gate (it is the owner's own dialogue).

## Step 2 - Mine blog-notes
Extract the owner's real questions, the misconceptions that got corrected, and the aha moments.
Consolidate, dedupe, and rank by interesting merit. Write/append `blog/blog-notes.md` in the shape in
`references/blog-format.md`. In a live study this accrues as the journey unfolds; standalone or in
backfill it is extracted on demand.

## Step 3 - Draft the post in the owner's voice
Using `references/blog-voice.md` and the post arc in `references/blog-format.md`, write
`blog/post-<slug>.md` - funny, vivid, and scientifically accurate. Use the highest-merit
blog-note(s) as the spine. Gloss every technical term; keep the wonder.

## Step 4 - Deliver
Show the post and where it is saved. The human publishes it. Re-run to regenerate. This skill does
not post to any platform.

## Retroactive / backfill mode
Given an existing study that lacks `journey/`/`blog/` (e.g. one predating this skill): reconstruct
the journey from whatever exists (a saved transcript, else the live session and the study artifacts),
and backfill the structure - create `journey/transcript.md` and `blog/`. Mark reconstructed turns
`(reconstructed from artifacts)`; if no real dialogue is recoverable, say so rather than inventing
one. This is "the research team puts together the missing pieces" so any prior study can be blogged.

## Relationship to the family
- Routed from the `research` command ("blog the journey / write up what I learned").
- `scientific-study` may hand off here after the PR (optional blog write-up) and may read
  `journey/transcript.md` for refinement context.
- Standalone (no study folder): write `transcript.md`, `blog-notes.md`, and the post under a local
  working dir (e.g. `./research-blog/<slug>/`); nothing is pushed to `jmresearch/research`.

## Edge cases
- No journey to draw on -> ask for a source; never invent a learning journey.
- Blog an existing / other-session study -> backfill mode; note where verbatim Q&A is missing.
- Science left unresolved -> the post is honest about the open question; no tidy fake resolution.
- Asked to auto-post to a platform -> out of scope; deliver the markdown post.
- A funny framing would require a wrong explanation -> cut the joke, keep the correctness.
