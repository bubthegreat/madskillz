# Research skills: personal science-blog persona + journey transcript

**Date:** 2026-06-20
**Status:** Design approved (brainstorming) — pending written-spec review
**Branch:** scientific-peer-review

## 1. Context

The research family lives under `plugins/madskillz/`:

- `commands/research.md` — entry point; routes to *produce a study*, *review a draft*, or
  *ask an expert*.
- `skills/scientific-study/` — produces a publication-ready study and opens a PR to
  `jmresearch/research`; runs the agentic peer-review loop, a compliance gate, and uses repo
  templates (`references/repo-layout.md`).
- `skills/scientific-peer-review/` — the review engine.
- `skills/ask-an-expert/` — reusable domain-expert personas under `experts/`.

The family is explicitly designed to grow by adding routed sibling skills (the command says
"Study design, analysis, and reproducibility packaging will be routed from here as they are
added"; peer-review references "a future `scientific-writeup` skill"). This design adds one such
sibling.

**The ask.** A *blog persona* that writes a neat/funny/interesting personal blog post in the
project owner's voice about the cool idea being researched — sharing the *learning journey*
("here's something I misunderstood, here's the correction, here's why it's actually cooler than
my wrong version"). It mines the owner's real questions and feedback as **blog-notes**, ranks
them by interesting merit, and drafts a post the owner can publish to their own blog. Alongside
it, the owner wants their **actual chat dialogue saved as part of the study** so it is clear
which parts were theirs versus where the AI did the heavy lifting on research/presentation. The
capability must also work **retroactively**: take any existing study plus available history and
produce a blog post, backfilling the missing structure where needed.

## 2. Goals and non-goals

**Goals**
- A reusable, routed `research-blog` skill that turns a research journey into a first-person,
  funny-but-accurate blog post in the owner's voice.
- An editable **voice persona** capturing the owner's style, refinable over time.
- **Blog-notes**: the owner's genuine questions + the corrections/aha moments, consolidated,
  deduped, ranked by merit. Captured **both** live during a study and on demand standalone.
- A **journey transcript** (human↔assistant dialogue, not tool-call noise) saved as part of the
  study record for provenance and for study refinement.
- **Retroactive + backfill:** run against an existing study (even one predating this feature),
  reconstructing blog-notes from whatever artifacts/history exist and assembling the missing
  `journey/`+`blog/` pieces so the study becomes blog-compatible.
- Science correctness is non-negotiable even under comedic framing (family integrity stance).

**Non-goals (v1)**
- Auto-posting to any blog platform. The deliverable is a markdown post the human publishes.
- The always-on, every-turn transcript hook (see §6, Approach A2) — *offered* as a follow-up,
  not built in v1.
- Generating research findings. This skill reports the journey; it does not do the science.

## 3. Shape and file layout

```
plugins/madskillz/skills/research-blog/
  SKILL.md                      # gather journey + save transcript -> mine blog-notes -> draft in voice
  references/
    blog-voice.md               # the owner's style persona (editable, with provenance)
    blog-format.md              # post arc + blog-notes shape + transcript shape
  evals/evals.json              # triggering tests, matching the family pattern
```

Edits to existing files:
- `commands/research.md` — add a fourth route: *blog the journey / write up what I learned* →
  `research-blog`.
- `skills/scientific-study/references/repo-layout.md` — add the `journey/` and `blog/` study
  subfolders (§5).
- `skills/scientific-study/SKILL.md` — optional Step-7 handoff to `research-blog`, and an
  optional read of `journey/transcript.md` for refinement context (§8). Kept light to avoid
  over-coupling.

(No compliance-gate change: the transcript is the owner's own dialogue, committed as-is — see §7.)

## 4. What the skill does (SKILL.md steps)

1. **Gather the journey + save the transcript.** Identify the source(s): the live session,
   and/or a study folder's artifacts (`paper.md`, `review/cycle-*`), and/or a previously saved
   transcript. Write/refresh `journey/transcript.md` — the human↔assistant *dialogue* (the
   owner's questions, direction, pushback; the substantive replies and corrections) — excluding
   tool-call/mechanical noise.
2. **Mine blog-notes.** Extract the owner's real questions, the misconceptions that got
   corrected, and the aha moments. Consolidate, dedupe, and rank by **interesting merit** (hook
   potential, surprise, how much it reframed understanding). Append to `blog/blog-notes.md`.
   In-study this happens live as the journey unfolds; standalone it is extracted on demand.
3. **Draft the post in the owner's voice** (`references/blog-voice.md`), following the post arc
   in `references/blog-format.md`, with the science kept dead accurate.
4. **Deliver.** Present the post and where it is saved (`blog/post-<slug>.md`). The human
   publishes it. Re-run to regenerate; this skill does not post anywhere itself.

### Retroactive / backfill mode

Given an existing study (possibly created before this feature, lacking `journey/` and `blog/`):

- **Reconstruct** the journey from whatever exists — a saved transcript if present, otherwise the
  live session history and the study artifacts (`paper.md`, `review/cycle-*.md`, snapshots).
- **Backfill** the missing structure: create `journey/transcript.md` (from the best available
  history; if no real dialogue is recoverable, note that honestly rather than inventing one) and
  `blog/` with reconstructed blog-notes.
- Be explicit in the output about which pieces were reconstructed vs. captured live, and where
  verbatim Q&A texture is missing. Never fabricate a question or an aha moment to fill a gap
  (§9).

## 5. The voice persona (`blog-voice.md`)

First-person learning-journey; science-is-freaking-cool enthusiasm; accessible to a curious
general reader; funny but never at the expense of accuracy. Influences encoded as concrete,
nameable moves (not just a list of names):

- **Scott Adams / Dilbert** — deadpan, "the obvious truth nobody says out loud."
- **The Oatmeal (Matthew Inman)** — exuberant hyperbole, tangents, the occasional ALL-CAPS
  punchline, "here is why this thing is secretly amazing."
- **Allie Brosh / Hyperbole and a Half** — self-deprecating, emotionally honest, "I was a
  confident disaster and here is the exact moment it clicked."
- **Dave Chappelle** — conversational storytelling, comedic timing, callbacks, willing to sit
  in the genuinely weird/uncomfortable part.

**Signature arc:** *I thought X → record scratch, nope → here's what's actually going on (plain
+ correct) → and it's somehow cooler than my wrong version → here's how it rewired my brain.*

The file carries a **Provenance** note (created/updated dates + what each edit changed), like the
expert personas, so the voice can be tuned over time honestly.

## 6. Blog-format and transcript shapes (`blog-format.md`)

**Post arc:** hook → the wrong mental model I walked in with → the record-scratch correction →
what's actually going on (plain + correct, wonder intact) → why it's cool / how it reframed me →
kicker (often "…and now I'm confused about *this* next").

**blog-notes entry:**
```
## <short title>
- Question I asked: <verbatim-ish>
- What I assumed: <prior mental model>
- The correction: <what's actually true>
- Why it's interesting (merit): <surprise / hook / reframing>
- Source: <session turn | study artifact | transcript line>
- Status: strong | maybe | thin
```

**transcript shape:** an append-friendly dialogue log — speaker-tagged human/assistant turns,
substantive content only (questions, direction, explanations, corrections), tool-call and
mechanical bookkeeping excluded. It is provenance, not a verbatim system log.

## 7. Transcript capture mechanism (the one design fork)

- **Approach A1 — skill-driven (BUILD in v1).** `research-blog` (and `scientific-study` when it
  hands off) writes/refreshes `journey/transcript.md` when it runs. Because `scientific-study`
  runs the full flow, the transcript is captured and committed as part of the study on every
  run. No harness config.
- **Approach A2 — hook-driven (OFFER as follow-up, not v1).** A `Stop` hook in `settings.json`
  appends each exchange automatically every turn, independent of the model. True "always,"
  but it is harness configuration (via the update-config skill), broader than this family, and
  needs an explicit target path.
- **Decision: A3 — build A1 now, offer A2 later.**

**Storage and publishing (owner decision).** The transcript IS stored as part of the study
record and committed, because that transparency is desired ("makes clear what's mine vs. where
the AI did the heavy lifting"). It is **not** part of `paper.md` and the manuscript never
references it — it is a sibling provenance artifact, like `review/`. **No privacy gate applies
to it:** it is the owner's own dialogue in a private repo, committed as-is by explicit decision
(the dataset/asset compliance gate in §-`compliance-gate.md` still governs *research data and
third-party artifacts* as before — it simply does not screen the owner's transcript).

## 8. Family integration

- **Routing:** `commands/research.md` gains the blog route. Triggers: "blog the journey," "write
  up what I learned," "turn this into a blog post," "make this fun to read."
- **Study handoff:** `scientific-study` SKILL gets an optional Step 7 — after the PR, offer a
  blog write-up via `research-blog`. Light touch; the study does not depend on it.
- **Refinement context:** `scientific-study` may read `journey/transcript.md` to ground itself
  in what the human actually asked/wanted. Optional input, not required.
- **Backfill an existing study:** `research-blog` can upgrade an older study folder to the new
  layout (§4, Retroactive / backfill mode) — the "research team puts together the missing
  pieces" so any prior study can be blogged.
- **Repo layout additions** (`repo-layout.md`):
  ```
  <topic>/<research-short-name>/
    journey/
      transcript.md     # human<->assistant dialogue (provenance; NOT part of paper.md)
    blog/
      blog-notes.md     # ranked blog-notes
      post-<slug>.md    # drafted post(s) in the owner's voice
  ```
  Both folders are omitted when empty; never padded to imply coverage.

## 9. Integrity stance (non-negotiable, on-brand with the family)

1. **The science is correct even when it's funny.** Comedy never licenses a wrong explanation.
   If the corrected understanding is itself simplified or uncertain, the post says so *in voice*.
   (The family's "integrity/correctness outranks presentation," blog edition.)
2. **The journey is real.** Blog-notes come from actual questions/corrections in the source —
   never an invented misconception or a fabricated aha moment. In backfill mode, reconstructed
   pieces are labeled as reconstructed; a gap is stated, never filled with invention.
3. **Written *as* the owner, not putting claims in their mouth.** It consolidates their real
   questions/feedback and flags anything it is inferring rather than quoting.
4. **Honest open threads stay in.** "I still don't fully get Y" is a feature and it's true.
5. **No fabricated citations.** Any source named in a post is real and resolvable, or it is
   framed as "something to read up on," never as a fake reference (consistent with the rest of
   the family).

## 10. Edge cases

- **No journey to draw on** (no live session content, no study, no transcript) → ask for a
  source; never invent a learning journey.
- **Blog an existing study from another session** → retroactive/backfill mode (§4): reconstruct
  from that study's `paper.md` + `review/` + any saved transcript; note where verbatim Q&A
  texture is missing.
- **Existing study lacks `journey/`/`blog/`** → backfill the structure from available history;
  label reconstructed pieces; if no real dialogue is recoverable, say so rather than fabricating.
- **Standalone (no study folder)** → write `transcript.md`, `blog-notes.md`, and the post under
  a local working dir (e.g. `./research-blog/<slug>/`); nothing is pushed to `jmresearch/research`
  unless it later becomes a study.
- **Asked to auto-post to a blog platform** → out of scope in v1; deliver the markdown post.
- **The science in the journey was left unresolved** → the post is honest about the open
  question; it does not invent a tidy resolution.

## 11. Testing (per writing-skills)

- **Triggering evals** (`evals/evals.json`) matching the family pattern: blog-the-journey
  phrasings route here; study/review/expert phrasings do **not** mis-route here.
- **Behavior pressure tests:** (a) a journey with a *wrong* but funny intuition — verify the post
  stays scientifically correct and flags residual uncertainty; (b) a sparse journey — verify it
  does not fabricate questions/aha moments; (c) backfill mode on an artifact-only study — verify
  reconstructed pieces are labeled and gaps are stated honestly.
- These follow RED→GREEN→REFACTOR: baseline the failure without the guidance first.

## 12. Related (separate) work

A token/performance optimization review of the existing research family was produced in the same
session. Its **safe** edits (description trimming, redundant-boilerplate removal, report-format
split, cross-file de-duplication, edge-case trimming) are being applied now; the **tradeoff**
options (conditional readability tier, mechanical re-engagement, cycle/​panel reductions) are
deferred to a TODO for later assessment. That work is **independent** of this design; this spec
does not depend on it.

## 13. Revision — standalone `blog` skill + voice-updater (2026-06-20)

Per owner direction after the initial build:

- **Split out of the scientific-* family.** `research-blog` → standalone **`blog`** skill, invoked
  via its own `/blog` command, not routed from `/research`. Reverted: the `/research` blog route and
  the `scientific-study` Step-7 blog handoff.
- **Kept in `scientific-study`:** `journey/transcript.md` as a study-owned **provenance** step (now
  with no blog mention); dropped `blog/` from the study layout.
- **Voice-updater added.** The skill maintains an evolving voice profile at `~/.claude/voice/voice.md`
  (seeded from `references/voice.md`), refined incrementally from a corpus
  (`~/.claude/voice/corpus.jsonl`) fed by an always-on `UserPromptSubmit` capture hook. The updater
  summarizes only entries newer than a recorded marker, never forces a finding, and never invents a
  trait. See `skills/blog/references/voice-update.md`. Hook configured via the update-config skill.
- Renames: `references/blog-voice.md` → `references/voice.md`; added `references/voice-update.md`.
