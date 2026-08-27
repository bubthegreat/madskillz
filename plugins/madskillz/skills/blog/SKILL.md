---
name: blog
description: >-
  Use when the owner wants to write a personal blog post in their own voice — "blog this," "blog
  the journey," "write up what I learned," "turn this into a blog post," "make this fun to read."
  Standalone; invoked on its own. Writes and saves the post; the human publishes it. The voice
  itself (profile, updates, rendering) is owned by the `voice` skill.
---

# blog: write in my voice

Turns a topic or learning journey into a neat, funny, genuinely-illuminating blog post in the
owner's voice — sharing a learning journey so a curious general reader comes away feeling that
the topic is cool. Post structure lives in `references/blog-format.md`; the voice comes from the
`voice` skill.

## Integrity stance (non-negotiable)
1. **Correct even when funny.** Comedy never licenses a wrong explanation. If the understanding is
   simplified or uncertain, say so in voice.
2. **The journey is real.** Never invent a misconception, an aha, or a question the owner didn't have.
3. **Written as the owner, not putting claims in their mouth.** Consolidate their real words; flag
   anything inferred.
4. **No fabricated citations.** A real, resolvable source, or an honest "read up on X."

## Step 0 — Get the voice
Run `voicectl render blog` and follow the rendered profile (the `voice` skill's core + blog
overlay). If `voicectl` is missing, install the `voice` plugin from this marketplace
(`bubthegreat/voice-store`) and run its installer (`skills/voice/scripts/install_voice_pipeline.sh`
in that repo). If `voicectl status --json` reports
`mode: local-only` or `render` warns that the core has no observed traits, tell the user to run
"set up my voice" (the voice skill's setup flow) before writing as them. "Update my voice"
requests belong to the `voice` skill — follow its SKILL.md update flow; no post is written for
those.

## Step 1 — Gather what to blog
The live session, notes the owner gives, or an existing study's artifacts (`paper.md`,
`review/cycle-*`, `journey/transcript.md`) when pointed at one. Pull out the owner's real questions,
the corrections, and the aha moments — never invent them.

## Step 2 — Draft the post in the owner's voice
Using the rendered voice and the post arc in `references/blog-format.md`, write the post — funny,
vivid, factually/scientifically accurate. Honor the voice's two layers: render the owner faithfully
(descriptive) but follow the prescriptive/register guidance so conversational tics and overused
phrases don't leak into the prose. Gloss every technical term; keep the wonder; keep honest open
threads.

## Step 3 — Deliver
Save the post to the owner's blog folder (default `~/blog/<slug>/<slug>.md`, or a path the owner
gives) along with any rendered artifacts (PDF etc.) for that post, and show it. Finished posts are
the owner's documents — they do **not** live in `~/.madskillz/` (skill state) or any repo checkout.
The human publishes it. This skill does not post to any platform.

## Blogging an existing study (optional)
Point the skill at a study folder to blog it retroactively: reconstruct the journey from its
artifacts (`paper.md`, `review/cycle-*.md`, and `journey/transcript.md` if present). Label
reconstructed pieces; state gaps honestly; never invent dialogue. (Studies save their own dialogue
transcript as provenance — this skill only **reads** it; it is not coupled to `scientific-study`.)

## Edge cases
- No topic/journey → ask for one; never invent a learning journey.
- "Update my voice" → hand off to the `voice` skill's update flow; no post.
- A funny framing would require a wrong explanation → cut the joke, keep the correctness.
- Asked to auto-post to a platform → out of scope; deliver the markdown post.
