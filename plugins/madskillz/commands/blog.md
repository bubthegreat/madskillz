---
description: Write a personal blog post in the owner's voice, or refresh the owner's voice profile from how they actually write.
argument-hint: [what to blog about, a study folder to blog, or "update my voice"]
---

Invoke the **`blog`** skill.

- "blog this" / "write up what I learned" / "turn this into a blog post" → write a post in the
  owner's voice (refreshing the voice profile first).
- "update my voice" / "refresh how I sound" → run only the voice updater, no post.
- Point it at a study folder to blog that study retroactively (it reads the study's artifacts,
  including `journey/transcript.md` if present).

Request: $ARGUMENTS

If nothing was provided above, ask what to blog — or whether to just update the voice profile.
