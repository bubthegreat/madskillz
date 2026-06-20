# story-studio: an agentic writing room for real books

**Date:** 2026-06-20
**Status:** Design approved (brainstorming) — pending written-spec review
**Branch:** writing-skills

## 1. Context

The owner wants to write real books — starting by turning a set of poorly-written,
ChatGPT-drafted goblin stories (written for his sons, who are now old enough to want a
"real book") into something good, and later writing new books (a "seer's son who escapes"
story; a "soul-cloning, death-fearing inventor" story). The pain points with the existing
material are concrete and recurring:

- **Self-inconsistency** — facts, names, places, and rules that drift over the story.
- **Weird language** — awkward, unnatural sentence-level prose.
- **Overused literary devices** — the same construction or image, again and again.
- **Robotic dialogue** — filler beats like *"And Jacob nodded"* substituting for real
  character interaction.

This is not the owner's *blog* voice. A book invents its **own** narrator voice and a
**roster of character voices**, defined per book. The only thing borrowed from the existing
`blog` skill is the **voice-profile file *format*** (an observed, evolving "how this entity
talks" document). `blog` is a standalone skill and is **not** modified or depended upon.

The owner is inspired by R.A. Salvatore (kinetic, legible action), Brandon Sanderson
(rule-bound magic systems; disciplined setup/payoff), and Robert Jordan (sprawling ensemble
and thread management). These inform the default/optional personas and the worldbuilding model.

The work mirrors the *structure* (not the membership) of the existing scientific skills:
an **orchestrator** drives an **engine** in a revise-loop, backed by a **reusable library**,
publishing to a configurable repo. That shape is proven here; this design reuses it.

## 2. Core principles (non-negotiable)

1. **The human is always the approver.** Personas *suggest* — twists, foreshadowing, a better
   line, a flagged inconsistency. Nothing is applied because a persona said so. It is the
   owner's book; the room advises.
2. **Feedback batches; it never interrupts.** Owner margin-notes and persona suggestions
   accumulate in a queue. Nothing changes on contact. A consolidation cycle
   (`/review-and-update`) turns the pile into **one adjudicated, severity-ranked revision
   plan** the owner approves/rejects/edits **item by item** before anything is applied.
3. **Voices are invented per book, never the owner's.** The narrator and every character get
   their own voice profile, authored for the book.
4. **Character prior states are never destroyed.** Evolution is append-only and anchored to
   story-time; earlier states are *scoped out* for earlier scenes, never overwritten.
5. **No fabrication, honest failure.** Never fake a critique, a citation, a character beat, a
   commit, or a push. If a tool is missing (`pandoc`, a TTS, repo access), say so; never fake
   success.

## 3. Goals and non-goals

**Goals**
- A modular set of skills that lets the owner write real books with an extensible room of
  agentic personas, enforcing character-driven consistency via a timeline-aware character model.
- A per-book folder format that stores the world bible, a canonical story timeline, a character
  roster (each character = base persona + voice + append-only timeline-anchored evolution), the
  manuscript (scenes tagged with story-time + POV), an accumulating notes queue, and exports.
- A **room** engine that runs the relevant personas over a manuscript, can **embody** a
  character at the correct story-time, and consolidates owner notes + persona suggestions into
  one adjudicated revision plan. Invocable standalone on any draft.
- A **reusable roles library** of mintable room roles (Magic-System Logician, Combat
  Choreographer, Science/Plausibility, …), shared across books.
- **EPUB + PDF** export via pandoc.
- A **dedicated, configurable writing repo** for in-progress books and future-book ideas, with
  direct push (the owner is the approver).

**Non-goals**
- Writing in the owner's personal voice (that is `blog`'s job; untouched here).
- Auto-publishing to any storefront or platform. The deliverable is files + exports.
- Generating audio (relevant only to `scientific-podcast`, a separate spec).
- Phase 2/3 capability (autonomous drafting; cross-book series continuity) — designed here,
  but **not built in the first plan** (see §10).

## 4. Architecture: three skills + a library + a shared folder format

Packaging "Option A" (chosen): maximally modular, each piece testable alone, the room reusable
on any draft, roles cleanly shareable across books.

```
plugins/madskillz/skills/
  story-studio/        # ORCHESTRATOR — frame/ingest, draft, run the room in a loop,
                       #   apply APPROVED changes, export EPUB/PDF, init/commit/push repo
  story-room/          # ENGINE — run relevant personas over a manuscript, embody characters
                       #   at correct story-time, consolidate notes+suggestions -> ONE
                       #   adjudicated revision plan. Never edits. Standalone-invocable.
  writing-roles/       # LIBRARY — reusable, mintable room roles (like ask-an-expert/experts/)
```

- **story-studio** owns the lifecycle: framing a new book or ingesting an existing one,
  orchestrating drafting (Phase 2), running `story-room` and applying only owner-approved
  revisions, exporting, and repo operations.
- **story-room** owns judgment: it selects the personas relevant to a pass, embodies
  characters, gathers margin-notes + suggestions, and returns a single adjudicated plan. It
  **never** mutates the manuscript. It can be pointed at any chapter to "just critique this."
- **writing-roles** owns reusable personas. A role is a markdown persona file (charter,
  what it watches for, how it reports). New roles can be minted on demand (mirrors
  `ask-an-expert`).

**Personas and roles are the same primitive.** Every persona — default or specialist — is a
charter file in `roles/`. `book.yaml`'s `active` list is the single source of truth for which
ones run on a given book. A sensible **default set** ships active (the §7 defaults); some of
those are *toggleable* for books where they do not apply (e.g. Science/Plausibility off for a
pure secondary-world fantasy); opt-in **specialists** (Magic-System Logician, Combat
Choreographer, …) ship inactive and are switched on per book. "Default" vs "opt-in" therefore
means *default-active* vs *default-inactive*, not two different mechanisms.

## 5. The per-book folder format (the contract everything reads/writes)

Lives in the configurable writing repo (§9).

```
<writing-repo>/
├── roles/                        # reusable room roles (shared across books)
│   ├── magic-system-logician.md
│   ├── combat-choreographer.md
│   └── science-plausibility.md
├── ideas/                        # seeds for future books
│   ├── seer-dad-escape.md
│   └── soul-clone-death.md
└── books/
    └── goblin-tales/
        ├── book.yaml             # title, genre, audience, status, active roles, narrator-voice ref
        ├── outline.md            # Architect's beat sheet / structure
        ├── bible/
        │   ├── world.md          # places, factions, history
        │   ├── magic-system.md   # costs / limits / laws (if any)
        │   ├── timeline.md        # THE SPINE: E01, E02, … canonical events in story-order
        │   └── glossary.md        # invented names/terms/pronunciations
        ├── voice/
        │   └── narrator.md        # invented narrator voice (NOT the owner's)
        ├── characters/
        │   └── mara/
        │       ├── character.md   # base persona (who she is at first appearance)
        │       ├── voice.md       # how Mara talks (voice-profile format)
        │       └── evolution.md   # append-only, timeline-anchored beats
        ├── manuscript/
        │   ├── ch01.md            # frontmatter: story_time, pov
        │   └── ch02.md
        ├── notes/
        │   ├── queue.md           # accumulating margin-notes + persona suggestions (un-adjudicated)
        │   └── revision-plans/    # one adjudicated plan per /review-and-update cycle
        │       └── cycle-01.md
        └── exports/
            ├── goblin-tales.epub
            └── goblin-tales.pdf
```

### 5.1 `book.yaml`
Records title, genre, target audience/age, status, the narrator-voice reference, and the
**list of active roles** drawn from `roles/`. (Goblin book → age-appropriateness reader on;
soul-clone book → Science/Plausibility + Magic-System Logician on.)

### 5.2 Scene frontmatter
Every manuscript scene/chapter declares its place on the timeline and its POV:

```yaml
---
story_time: after E12        # references bible/timeline.md event ids; may be "flashback before E04"
pov: Mara
---
```

`story_time` is set **explicitly, room-assisted**: when drafting, the room proposes the tag;
the owner confirms/edits. This is the only model of the three considered that handles
flashbacks and out-of-order reveals correctly.

## 6. The character model (the spine)

A character is **not** a static sheet. It is a persona an agent can **embody and act out**, so
the room can drop the character into a situation, observe what they would actually do, and the
critics flag inconsistencies or ask for clarification.

- **`character.md`** — base/defining persona (who they are at first appearance / story start).
- **`voice.md`** — how they talk (voice-profile format).
- **`evolution.md`** — an **append-only** log of change beats, each **anchored to a timeline
  event**, e.g.:

  ```
  ## at E12 — mother's death
  Grief, guardedness, flashes of anger at the world. Withdraws from the friend group.
  Why: she blames herself for being away when it happened.
  ```

### 6.1 State resolution (the one rule that makes flashbacks safe)
To embody or check a character in a scene, resolve:

```
effective_persona(scene) = character.md  +  every evolution beat whose anchor ≤ scene.story_time
```

So a post-death scene resolves to grief-Mara; a flashback whose `story_time` precedes the death
resolves back to *happy-teenager* Mara, because that beat is not yet in scope. Prior states are
never lost — they are simply out of scope for earlier story-time. This lets the Continuity
critic catch *both* "too cheerful three chapters after her mother died" *and* "this flashback
wrongly references the death."

### 6.2 Embodiment
`story-room` can spin up an agent handed the **resolved** persona + voice for a given scene's
`story_time`. Two uses: (a) **generation aid** — produce authentic in-character dialogue and
decisions; (b) **consistency check** — does the drafted scene match how this character, *as of
this story-time*, would actually behave?

## 7. The room: personas

Each persona is one of four types — **✍️ Writer**, **🧭 Suggester**, **🔍 Critic**,
**👓 Reader**. Suggesters/critics/readers never edit; they file into the notes queue.
The room runs only the personas **relevant to a given pass** (a dialogue-heavy chapter pulls the
Dialogue Director; a battle pulls the Combat Choreographer if the book has opted it in).

**Default personas**

| Persona | Type | Job | Pain solved |
|---|---|---|---|
| Narrator | ✍️ | Holds the book's authorial throughline + narrator voice; does the drafting (Phase 2). | — |
| Story Architect / dev editor | 🧭 | Outline, beats, arcs, stakes, pacing; proposes twists & tracks foreshadowing setup→payoff. | structure |
| Lorekeeper / Continuity | 🔍 | Owns the bible; flags contradictions in names/places/timeline/facts/magic rules. | self-inconsistency |
| Character & Dialogue Director | 🔍 | Distinct voice + motivation per character; flags filler beats; proposes real interaction. | "And Jacob nodded" |
| Line Editor / Prose Stylist | 🔍 | Sentence-level: awkward phrasing, clarity, rhythm; cuts purple prose. | weird language |
| Tic & Repetition Hunter | 🔍 | Whole-document view: overused words/devices/crutch phrases/structural tics. | repetitive devices |
| Science / Plausibility | 🔍 | Flags violations of real-world science egregious enough to break suspension of disbelief (soft, not a documentary). | immersion breaks |
| Beta Reader (genre fan) | 👓 | Reads as an enthusiastic fan of the genre/age; what landed, what dragged, what confused — and why. Tunable per book. | reader experience |
| Copy Editor | 🔍 | Final pass before export: grammar, punctuation, typos, formatting. | polish |

**Opt-in (default-inactive) roles** (from `roles/`, examples): Magic-System Logician (Sanderson
— internal rule integrity), Combat Choreographer (Salvatore — kinetic + legible fights),
Age-Appropriateness reader (the goblin book specifically), Series-Continuity keeper (across
books). New roles mintable on demand. Per §4, defaults and opt-ins are the same charter
primitive — they differ only in whether `book.yaml` ships them active.

Science/Plausibility guards against *external*-reality violations; the Magic-System Logician
guards *internal* rule integrity — complementary, not redundant.

## 8. Data flow: the feedback loop

```
              owner reads & drops margin-notes ┐
                                               ├─►  notes/queue.md  (accumulating, un-adjudicated)
        story-room personas file suggestions ──┘
                                               │
                       /review-and-update  ────┤  story-room consolidates the whole queue into
                                               │  notes/revision-plans/cycle-NN.md
                                               │  — ONE adjudicated, severity-ranked plan
                                               ▼
                       owner approves/rejects/edits each item
                                               ▼
              story-studio applies ONLY approved items, commits the cycle
              (commit per draft + per revision cycle; plan saved for visibility)
```

- **Margin-notes capture:** the owner can leave notes against scenes while reading; they land
  in `notes/queue.md` without forcing any change.
- **Persona suggestions:** flow into the same queue, so notes and suggestions are adjudicated
  together.
- **`/review-and-update`:** the consolidation cycle. Mirrors `scientific-peer-review`'s output
  shape (one adjudicated, severity-ranked revision plan) — the room proposes, the owner
  disposes, the studio applies.

## 9. Repo storage & export

- **Repo:** a dedicated writing repo, **target configurable per user** (e.g. `bub/writing`),
  not hardcoded — so anyone using `madskillz` sets their own. The studio inits the layout,
  commits **per draft and per revision cycle**, and **pushes directly** to a per-book branch
  (`book/<slug>`). **No PR gate** — solo creative work where the owner is already the approver.
- **Ideas:** future-book seeds live in `ideas/` (the seer and soul-clone pitches seed the
  first two).
- **Export:** `pandoc` produces **EPUB** (reflowable; e-reader default) and **PDF** (fixed
  layout; needs a LaTeX engine such as `tectonic`/`xelatex`). Missing toolchain → report and
  fall back (e.g. EPUB-only if no LaTeX), never fake an export.

## 10. Build phasing (this spec covers all of it; the first plan targets Phase 1)

- **Phase 1 — The Reviewer.** Ingest the existing goblin stories → build bible/characters/
  timeline (room-assisted, owner-confirmed) → tag scenes with `story_time` → run the room
  (Continuity, Line Editor, Tic Hunter, Dialogue Director, Beta Reader, Science/Plausibility,
  Copy Editor) including character-embodiment consistency checks → consolidate via
  `/review-and-update` → apply approved changes → export EPUB/PDF → repo init/commit/push.
  **Delivers a real, consistent, exportable book from work that already exists**, and de-risks
  the hard character/timeline/critic machinery. The folder format, character model, room
  engine, roles library, notes loop, repo + export all land here.
- **Phase 2 — The Writer (studio drafting).** Story Architect + autonomous chapter drafting to
  bible/characters/timeline + the draft→room→revise loop + suggestion-driven foreshadowing and
  twists. Writes the *new* books (seer, soul-clone).
- **Phase 3 — Depth.** More roles, richer character simulation, cross-book series continuity,
  nicer typesetting, an idea→book promotion workflow.

## 11. Error handling & edge cases

- **No existing text and no brief** → ask what book to work on; never invent a premise.
- **Scene with no resolvable `story_time`** → the room proposes one and asks the owner to
  confirm; it does not silently guess for flashbacks.
- **Character referenced but no character file** → the room flags it and offers to scaffold a
  base persona; it does not invent canon silently.
- **Conflicting bible facts** → surfaced as a Continuity finding in the queue; never
  auto-resolved.
- **A persona suggestion the owner rejects** → recorded as rejected in the cycle plan; not
  re-proposed every cycle (avoid nagging).
- **`pandoc`/LaTeX missing** → report; export what is possible (EPUB without LaTeX); never fake.
- **Repo target unset / no push access / offline** → stop with guidance; never fake a
  commit/push.
- **Asked to apply a change the owner did not approve** → refused; only approved items apply.
- **Asked to write in the owner's personal voice** → out of scope; that is `blog`.

## 12. Testing

- **Character state resolution** — unit-style fixtures: a character with beats at E04 and E12;
  assert a scene `after E12` resolves with both, a `flashback before E04` resolves to base only,
  a scene `after E04` resolves with the E04 beat only.
- **De-batched / room-assisted tagging** — given an untagged ingested chapter, the room proposes
  a `story_time` and POV that the owner can confirm.
- **Critic targeting** — the room selects only relevant personas per pass (dialogue chapter →
  Dialogue Director present; no Combat Choreographer unless opted-in and warranted).
- **Apply-only-approved** — a revision plan with approved + rejected items applies exactly the
  approved set and commits; rejected items are recorded, not applied.
- **Export** — a tiny sample book produces a valid EPUB; PDF when a LaTeX engine is present, and
  a clean reported fallback when it is not.
- **Skill triggering** — eval prompts (e.g. "turn my goblin stories into a real book", "review
  this chapter for consistency", "add a magic-system checker to this book") route to the right
  skill.
