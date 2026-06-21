# Phase 1 — Co-design protocol

The Showrunner leads an interactive conversation that turns a raw idea into an
approved story bible and outline. No prose is written until the user signs off at
the Checkpoint at the end of this phase.

**Integrity rule:** never invent, assume, or record premise, characters, or world
details the user has not explicitly approved. When unsure, ask — do not guess and
proceed.

---

## Ordered steps

### Step 1 — Premise

Ask the user for the core story idea. Aim for a one- or two-sentence logline that
captures the protagonist, the central conflict, and the stakes. If the initial idea
is too vague, ask a focused follow-up (e.g. "Who is the main character and what do
they want?") rather than guessing.

Do not record any premise in `bible/premise.md` until Step 8 (Bible Keeper writes).

### Step 2 — Audience, age range, and reading level

Establish:
- **Target audience** — who will read this (e.g. "children ages 6–9").
- **Reading level** — the vocabulary and sentence-complexity tier appropriate for
  that audience (e.g. "early chapter book", "middle grade", "YA").

These values feed `book.yaml: audience` and `book.yaml: reading_level` and govern
every downstream decision about vocabulary, chapter length, and theme intensity.

### Step 3 — Genre and tone

Agree on a genre (e.g. fantasy, adventure, mystery) and a tone (e.g. "funny, warm,
slightly irreverent" or "quiet, melancholy, literary"). Offer two or three tone
descriptors as a prompt if the user is unsure; confirm before moving on.

### Step 4 — POV and tense

Agree on:
- **Point of view** — third-person limited, first-person, omniscient, etc.
- **Narrative tense** — past or present (future is unusual; flag it).

Note any permitted deviations (e.g. a prologue told from a different POV).

### Step 5 — Target length

Establish the planned scope:
- **Chapter count** (`book.yaml: target_chapters`).
- **Words per chapter** (`book.yaml: target_words_per_chapter`).

Cross-check the outline complexity in Step 7 against this target. A 32-chapter
outline for a 5,000-word early chapter book is a structural problem — surface it
here, not later.

### Step 6 — Characters and world

Work with the user to develop:
- **Main characters** — role, personality, voice, and arc for each.
- **World / setting** — time, place, physical environment, and governing rules
  (magic system, technology limits, social norms, etc.).
- **Factions or communities** — any groups with stakes in the story.

Ask questions to surface gaps; do not invent details to fill them. A character the
user did not describe is not a character yet.

### Step 7 — Chapter-by-chapter outline

Produce a beat for every planned chapter. Each beat is 2–5 sentences covering:
- What happens.
- Who moves or changes.
- What narrative function the chapter serves (setup, escalation, turning point,
  resolution, etc.).

Verify the beats form a coherent arc at the target length. Flag pacing problems
(e.g. flat middle act, rushed climax) and propose structural fixes before moving on.

### Step 8 — Style guide

Produce the style guide covering:
- **Voice** — defining qualities: register, emotional temperature, humor level, pace.
- **Do list** — encouraged devices or patterns (e.g. "short punchy sentences in
  action scenes").
- **Don't list** — prohibited devices or patterns.
- **Banned phrases** — seed this list with common crutch phrases; add any the user
  names. Mandatory seed entries:
  - `"And X nodded"` (and variants: "nodded slowly", "just nodded")
  - `"suddenly"` used as a lazy escalation device
  - `"He/She smiled"` as a default filler beat
  - `"X turned to Y and said"` as a dialogue introducer

  The banned-phrase list is mirrored verbatim into `book.yaml: banned_phrases[]` and
  `bible/style-guide.md`; the Repetition & Device Auditor and Dialogue & Character
  Doctor enforce it mechanically in Phase 2.

---

## Showrunner → Bible Keeper handoff

At the end of Step 8 the Showrunner has produced a set of proposed content — not yet
canonical. The handoff is explicit:

1. **Showrunner emits** a structured proposal containing:
   - Logline and themes (for `bible/premise.md`).
   - Full character profiles (for `bible/characters.md`).
   - World, rules, and factions (for `bible/world.md`).
   - Chapter-by-chapter beats (for `bible/outline.md`).
   - An initial timeline of canonical events (for `bible/timeline.md`).
   - Style-guide content: voice, do/don't, and the complete banned-phrase list
     (for `bible/style-guide.md`).
   - All proper nouns and invented terms (for `bible/glossary.md`).
   - The `book.yaml` field values: `audience`, `reading_level`, `genre`, `tone`,
     `pov`, `tense`, `target_chapters`, `target_words_per_chapter`,
     `banned_phrases`, `illustrate`, `status: co-design`.

2. **Bible Keeper receives** the Showrunner proposal and writes each item into the
   correct file under `bible/` (see `references/story-bible.md` for exact file
   shapes) and writes `book.yaml`. The Bible Keeper does not edit or interpret the
   proposed content — it files exactly what the Showrunner produced. If anything
   is missing or ambiguous, the Bible Keeper surfaces it back to the Showrunner
   before writing, not after.

3. The Bible Keeper commits the result:

   ```
   book: <slug> bible v1
   ```

   where `<slug>` is the kebab-case book slug (see `references/repo-layout.md`).

---

## Checkpoint — user approval before any prose

After the `bible v1` commit, the Showrunner presents a summary to the user:

- The premise logline and themes.
- The character roster (name + one-line arc per character).
- The world in two or three sentences.
- The full chapter-by-chapter outline (all beats).
- Key style-guide decisions (POV, tense, tone, banned-phrase list).

Then ask explicitly: **"Does this look right? Approve to start drafting, or redirect
anything you want changed."**

**On approval:** set `book.yaml: status: drafting` (Bible Keeper writes the change),
commit `book: <slug> bible approved`, and hand off to Phase 2.

**On redirect:** the Showrunner revises the flagged elements, the Bible Keeper
updates `bible/*` accordingly, and the Checkpoint is re-presented. Repeat until the
user approves. Do not begin any chapter prose while the Checkpoint is open.

The Checkpoint is the gate between Phase 1 and Phase 2. Nothing in `chapters/` is
written, and no Drafter is invoked, until this gate is cleared.
