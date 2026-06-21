---
name: blog
description: >-
  Use when the owner wants to write a personal blog post in their own voice, or to refresh/update
  that voice profile from how they actually write — "blog this," "blog the journey," "write up what
  I learned," "turn this into a blog post," "make this fun to read," "update my voice," "refresh how
  I sound." Standalone; invoked on its own. Writes and saves the post; the human publishes it.
---

# blog: write in my voice, and keep my voice current

A standalone skill that (1) maintains an evolving profile of **how the owner actually writes**, and
(2) writes neat, funny, genuinely-illuminating blog posts in that voice — sharing a learning journey
so a curious general reader comes away feeling that the topic is cool.

Two things in one:
- **Voice profile** — an aggregate "this is how the owner talks," seeded once and then refined over
  time from the owner's real messages (see `references/voice-update.md`).
- **Blog writer** — turns a topic or learning journey into a post in that voice
  (`references/blog-format.md`).

### Voices — which file is "me"
The owner can have **several named, per-purpose voices**, each a real `status: personal` profile in
the voices library: `references/voices/<name>.md`. This skill's voice is **`science-blog`**. The
generic `references/voice.md` is a `status: template` only — the starting shape for minting a new
voice, **never** presented as the owner.

**Voice resolution order** (use the first that exists; never fall through to the template *as* "me"):
1. **Live profile** `~/.madskillz/voice/voice.md` — freshest, evolves per session.
2. **Committed voice** `references/voices/science-blog.md` — the shared source of truth non-local
   agents read; the fallback on a fresh machine.
3. **Template** `references/voice.md` — only to *create* a new named voice, never rendered as "me."

## Integrity stance (non-negotiable)
1. **Correct even when funny.** Comedy never licenses a wrong explanation. If the understanding is
   simplified or uncertain, say so in voice.
2. **The journey is real.** Never invent a misconception, an aha, or a question the owner didn't have.
3. **Written as the owner, not putting claims in their mouth.** Consolidate their real words; flag
   anything inferred.
4. **The voice is observed, not invented.** Update the profile only from things the owner actually
   wrote; never fabricate a stylistic trait. A pass that finds nothing new changes nothing.
5. **No fabricated citations.** A real, resolvable source, or an honest "read up on X."

## Step 0 — Refresh the voice (always, before writing)
Run the voice updater per `references/voice-update.md`: ensure `~/.madskillz/voice/voice.md` exists
(seed it from the owner's committed `references/voices/science-blog.md` on first run — falling back to
the `references/voice.md` template only if no committed voice exists), read the corpus entries newer
than the recorded marker, and if there is something genuinely new about how the owner writes, merge it
into the profile (descriptive layer, with keep/tone-down tags) and advance the marker. Then run the
**materiality-gated repo sync**: when the change is material, push the updated profile to the voices
library so non-local agents benefit; otherwise leave the repo untouched. If nothing is new, leave it
unchanged. This step can also be run **on its own** ("update my voice") with no post written.

## Step 1 — Gather what to blog
The live session, notes the owner gives, or an existing study's artifacts (`paper.md`,
`review/cycle-*`, `journey/transcript.md`) when pointed at one. Pull out the owner's real questions,
the corrections, and the aha moments — never invent them.

## Step 2 — Draft the post in the owner's voice
Using the resolved voice (per the resolution order above — live profile, else committed
`references/voices/science-blog.md`; never the bare template *as* "me") and the post arc in
`references/blog-format.md`, write the post — funny, vivid, factually/scientifically accurate. Honor
the voice's two layers: render the owner faithfully (descriptive) but follow the prescriptive/register
guidance so conversational tics and overused phrases don't leak into the prose. Gloss every technical
term; keep the wonder; keep honest open threads.

## Step 3 — Deliver
Save the post (default `~/.madskillz/voice/posts/<slug>.md`, or a path the owner gives) and show it. The
human publishes it. This skill does not post to any platform.

## Blogging an existing study (optional)
Point the skill at a study folder to blog it retroactively: reconstruct the journey from its
artifacts (`paper.md`, `review/cycle-*.md`, and `journey/transcript.md` if present). Label
reconstructed pieces; state gaps honestly; never invent dialogue. (Studies save their own dialogue
transcript as provenance — this skill only **reads** it; it is not coupled to `scientific-study`.)

## Edge cases
- No topic/journey → ask for one; never invent a learning journey.
- "Update my voice" with nothing new in the corpus → say so; change nothing (don't force a finding).
- First ever run → seed the live profile from `references/voice.md`, then proceed.
- A funny framing would require a wrong explanation → cut the joke, keep the correctness.
- Asked to auto-post to a platform → out of scope; deliver the markdown post.
