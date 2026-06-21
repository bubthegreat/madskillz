# story-studio: an agentic writing room for real books

**Date:** 2026-06-20
**Status:** Design refined (round 2: full rough-edge sweep) — pending written-spec review; implementation parked as a TODO
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

**Goblin Tales specifically** is to become a *single real novel* (not an anthology of separate
stories) that **weaves in some of the world's history**. Its timeline therefore carries both
deep-history events and in-narrative events on one ordered spine (§5.4).

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
- A **Phase-1 ingestion path from ChatGPT chat logs** that separates story prose from
  prompts/model chatter, stitches it in order, and splits it into manuscript scenes (§10.1).
- A **fresh target narrator voice** (calibrated to audience + inspirations) the Line Editor
  edits *toward* — never extracted from the bad source — plus a **preserved "loved lines"** list
  of bits the kids already love, kept verbatim where possible.
- A **`locked` marker** on scenes/passages: critics may observe locked content but never propose
  rewrites to it.
- A small **command surface** (`/story`, `/note`, `/review-and-update`, `/export`) — §4.1.
- A **unified timeline spine** (deep-history + in-narrative events) that character beats,
  flashbacks, and knowledge-state all anchor to (§5.4, §6).
- **Real-book export** with front matter (title page, dedication, table of contents) and metadata
  from `book.yaml`.
- **EPUB + PDF** export via pandoc.
- A **dedicated, configurable writing repo** for in-progress books and future-book ideas, with
  direct push to `main` (the owner is the approver).

**Non-goals**
- Writing in the owner's personal voice (that is `blog`'s job; untouched here).
- Auto-publishing to any storefront or platform. The deliverable is files + exports.
- Generating audio (relevant only to `scientific-podcast`, a separate spec).
- **Illustrations** — kids'-book art/layout is a Phase-3 concern; Phase 1 ships text → EPUB/PDF.
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
charter file in `roles/`. `book.yaml`'s `active_roles` list is the single source of truth for
which ones run on a given book. A sensible **default set** ships active (the §7 defaults); some of
those are *toggleable* for books where they do not apply (e.g. Science/Plausibility off for a
pure secondary-world fantasy); opt-in **specialists** (Magic-System Logician, Combat
Choreographer, …) ship inactive and are switched on per book. "Default" vs "opt-in" therefore
means *default-active* vs *default-inactive*, not two different mechanisms.

### 4.1 Command surface

Four commands front the skills (mirrors the scientific family's `/research` umbrella):

| Command | Skill | Does |
|---|---|---|
| `/story` | story-studio | Umbrella entry — start a new book, resume one, scaffold the folder, or ingest existing source. Routes to the right step. |
| `/note <text>` | story-studio | Capture a margin-note while reading. Anchors to the scene currently in context (optionally a quoted line: `/note ch03 "…" <text>`); appends to `notes/queue.md`. **Never** triggers a change — it just records. |
| `/review-and-update` | story-room → story-studio | Run the consolidation cycle: room consolidates the whole queue into one adjudicated plan; owner approves/rejects/edits item-by-item; studio applies only approved items and commits. |
| `/export` | story-studio | Assemble the manuscript (+ front matter) → EPUB/PDF via pandoc. |

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
        ├── book.yaml             # title, author, dedication, genre, audience, status, active roles, voice ref
        ├── outline.md            # Architect's beat sheet / structure
        ├── source/               # Phase-1 ingestion: raw ChatGPT logs + extraction provenance
        │   ├── raw/              # the original exported/pasted chat logs (untouched)
        │   └── extraction.md     # how raw → manuscript was split; what was dropped as chatter
        ├── bible/
        │   ├── world.md          # places, factions, history
        │   ├── magic-system.md   # costs / limits / laws (if any)
        │   ├── timeline.md        # THE SPINE: E01… ordered events, each tagged [history] or [story]
        │   └── glossary.md        # invented names/terms/pronunciations
        ├── voice/
        │   ├── narrator.md        # FRESH target voice (NOT the owner's, NOT extracted from source)
        │   └── loved-lines.md     # bits the kids love, preserved verbatim where possible
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
Records title/author/dedication, genre/language, status, the narrator-voice reference, the
**list of active roles** drawn from `roles/`, and an **audience block**. The audience block names the *actual* readers so the
Beta Reader and Age-Appropriateness personas calibrate to *them*, not a generic "genre fan":

```yaml
title: Goblin Tales
author: <pen name or real name — fill in>   # printed on the title page (front matter)
dedication: >-                               # printed after the title page; optional
  For my boys.
genre: middle-grade fantasy
language: en
status: phase-1-review
narrator_voice: voice/narrator.md
audience:
  readers: the owner's two sons
  ages: [9, 11]                  # concrete, drives age-appropriateness + reading level
  already_love: >-
    the goblin pranks, Grix's terrible cooking, the fart-cave chapter — keep that energy
active_roles: [age-appropriateness, science-plausibility]
```

(`title`/`author`/`dedication`/`language` feed the export front matter, §9. Goblin book →
age-appropriateness on; soul-clone book → Science/Plausibility + Magic-System Logician on.)

### 5.2 Scene frontmatter
Every manuscript scene/chapter declares its place on the timeline, its POV, and whether it is
locked:

```yaml
---
story_time: after E12        # references bible/timeline.md event ids; may be "flashback before E04"
pov: Mara
locked: false                # true → critics may observe but never propose rewrites to this scene
---
```

`story_time` is set **explicitly, room-assisted**: when drafting (or ingesting), the room
proposes the tag; the owner confirms/edits. This is the only model of the three considered that
handles flashbacks and out-of-order reveals correctly. **Locking** can also be applied to a
*passage* inside an otherwise-editable scene with inline markers `<!-- lock -->…<!-- /lock -->`
(used to protect the kids' beloved lines from a zealous Line Editor; see also `voice/loved-lines.md`).

### 5.3 Reading order ≠ story-time
The book **exports in `manuscript/` file order** (the reading order the author intends).
`story_time` is used *only* to resolve character state (so flashbacks get the earlier self); it
never reorders the manuscript. A chapter that is a flashback still reads where it is placed.

### 5.4 The unified timeline spine (`bible/timeline.md`)
There is **one ordered spine** of canonical events, each with an id and a **type tag**:

```
E01 [history] The Sundering — 300 years before the story
E02 [history] Goblins exiled to the Underroot
…
E40 [story]   Grix finds the old map
E41 [story]   Mara's mother dies
```

- **`[history]`** events are backstory the book *weaves in* (some long predating any living
  character); **`[story]`** events happen within the narrative.
- Scene `story_time`, character **evolution beats**, **knowledge** acquisition (§6), and
  **flashbacks** all anchor to **any** event on this one spine. So a flashback to a `[history]`
  moment resolves character state correctly, and the Architect can point at unused `[history]`
  events as foreshadowing fuel (Phase 2).
- Ordering is by the spine, not by `E`-number arithmetic; ids are stable labels, and new events
  can be inserted between existing ones (e.g. `E40a`) without renumbering.

## 6. The character model (the spine)

A character is **not** a static sheet. It is a persona an agent can **embody and act out**, so
the room can drop the character into a situation, observe what they would actually do, and the
critics flag inconsistencies or ask for clarification.

- **`character.md`** — base/defining persona **as of first appearance** (not "story start" —
  characters introduced later begin from their first-appearance state). Includes a lightweight
  **relationships** note (allies/rivals/family/loyalties) so the Dialogue Director can judge
  whether an interaction is *real* rather than filler.
- **`voice.md`** — how they talk (voice-profile format).
- **`evolution.md`** — an **append-only** log of change beats, each **anchored to a timeline
  event** (§5.4). A beat may record a change in **personality**, **relationships**, *and*
  **knowledge** — knowledge is just another anchored state change. E.g.:

  ```
  ## at E41 — mother's death
  Grief, guardedness, flashes of anger at the world. Withdraws from the friend group.
  Why: she blames herself for being away when it happened.

  ## at E12 — learns the goblins are real
  Knowledge: now knows goblins exist and acts on it. Before E12 she'd have scoffed.
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

Because **knowledge** is resolved the same way, the critic also catches the classic
**knows-too-early** bug: if a scene `before E12` has Mara act on the goblins being real, the
resolution shows she does not yet hold that knowledge → flagged.

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
**Reader (👓) feedback enters the queue as *advisory observations*** ("this dragged for me, and
here's why"), not mandated changes; **Critic (🔍) findings carry actionable severity** (§8).

**Default personas**

| Persona | Type | Job | Pain solved |
|---|---|---|---|
| Narrator | ✍️ | Holds the book's authorial throughline + narrator voice; does the drafting (Phase 2). | — |
| Story Architect / dev editor | 🧭 | Outline, beats, arcs, stakes, pacing; proposes twists & tracks foreshadowing setup→payoff. | structure |
| Lorekeeper / Continuity | 🔍 | Owns the bible + timeline spine; flags contradictions in names/places/facts/magic rules **and in character state/knowledge resolved at each scene's story-time** (incl. knows-too-early). | self-inconsistency |
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

- **Margin-notes capture (`/note`):** the owner leaves notes against scenes while reading; they
  land in `notes/queue.md` without forcing any change.
- **Persona suggestions:** flow into the same queue, so notes and suggestions are adjudicated
  together.
- **Consolidation is a meta-editor.** `/review-and-update` runs a meta-editor (like
  `scientific-peer-review`'s) that **dedups** overlapping items and **reconciles conflicts** into
  *one coherent* item — e.g. the Line Editor wanting to cut a line the Beta Reader loved becomes
  a single decision for the owner, not two contradictory entries — then **ranks by
  fiction-severity**:
  - **blocker** — breaks the story or its consistency (continuity/knowledge contradiction, plot hole);
  - **major** — weakens it (flat dialogue, a sagging scene, an overused device);
  - **minor** — polish (word choice, a typo).
  Reader reactions ride along as *advisory* context, not severities.
- **Notes lifecycle.** When a cycle is adjudicated, consolidated items **move** from
  `notes/queue.md` into the saved `cycle-NN.md` plan and are **cleared** from the queue; the
  owner's dispositions (approved/edited/**rejected**) are recorded there, and **rejected items
  are not re-proposed** in later cycles (no nagging). `/review-and-update` mirrors
  `scientific-peer-review`'s output shape — the room proposes, the owner disposes, the studio
  applies.

## 9. Repo storage & export

- **Repo:** a dedicated writing repo, **target configurable per user** (e.g. `bub/writing`),
  not hardcoded — so anyone using `madskillz` sets their own. The target is **resolved on first
  run and remembered** in a local config (`~/.claude/writing/config`); first run **offers to
  init** the repo and lay down the folder format. Thereafter the studio commits **per draft and
  per revision cycle** and **pushes directly to `main`** — books in `books/<slug>/`, shared
  `roles/` and `ideas/` at the root. **No branches, no PR gate** — solo creative work where the
  owner is the approver, so per-book branches would only strand the shared `roles/`/`ideas/` and
  add switching friction. (A throwaway `experiment/<thing>` branch for a risky rewrite is always
  available ad hoc; the design does not require it.)
- **Ideas:** future-book seeds live in `ideas/` (the seer and soul-clone pitches seed the
  first two).
- **Export:** `/export` assembles **front matter** — a **title page** (`title`/`author` from
  `book.yaml`), an optional **dedication**, and a **table of contents** — ahead of the chapters
  in `manuscript/` file order, then `pandoc` produces **EPUB** (reflowable; e-reader default) and
  **PDF** (fixed layout; needs a LaTeX engine such as `tectonic`/`xelatex`). Document metadata
  (title/author/language) comes from `book.yaml`. Missing toolchain → report and fall back
  (e.g. EPUB-only if no LaTeX), never fake an export.

## 10. Build phasing (this spec covers all of it; the first plan targets Phase 1)

- **Phase 1 — The Reviewer.** Ingest the existing goblin stories (§10.1) → build
  bible/characters/timeline (room-assisted, owner-confirmed, contradiction-flagging) → tag
  scenes with `story_time` → set a fresh target narrator voice + capture loved-lines → run the
  room (Continuity, Line Editor, Tic Hunter, Dialogue Director, Beta Reader,
  Science/Plausibility, Copy Editor) including character-embodiment consistency checks →
  consolidate via `/review-and-update` → apply approved changes → export EPUB/PDF →
  repo init/commit/push. **Delivers a real, consistent, exportable book from work that already
  exists**, and de-risks the hard character/timeline/critic machinery. The folder format,
  character model, room engine, roles library, notes loop, repo + export all land here.
- **Phase 2 — The Writer (studio drafting).** Story Architect + autonomous chapter drafting to
  bible/characters/timeline + the draft→room→revise loop + suggestion-driven foreshadowing and
  twists. Writes the *new* books (seer, soul-clone).
- **Phase 3 — Depth.** More roles, richer character simulation, cross-book series continuity,
  nicer typesetting, an illustration pipeline, an idea→book promotion workflow.

### 10.1 Phase-1 ingestion & bootstrapping (the riskiest step)

The source is ChatGPT chat logs and is *known to be inconsistent* — so the prime directive is:
**never silently canonize the source's bugs.** Bootstrapping is a guided, owner-confirmed
pipeline, not an automatic extraction.

1. **Normalize the logs → manuscript.** Read the raw logs from `source/raw/` — accepting a
   ChatGPT **`conversations.json`** export and/or **pasted markdown**. When the stories span
   **multiple chat logs/sessions**, order them by the owner's instruction (or by export
   timestamps, confirmed). Separate actual story prose from prompts, model chatter, and meta.
   Where a scene was **regenerated/duplicated** in the logs (several versions of the same
   passage), surface the variants and let the owner pick the canonical one — never silently keep
   the last. Stitch the prose in narrative order, split into `manuscript/chNN.md` scenes (room
   proposes boundaries; owner confirms). Record exactly what was kept, dropped, and chosen-among
   in `source/extraction.md` (provenance — so nothing vanishes silently).
2. **Extract canon *with* the Continuity critic running.** As the Lorekeeper builds
   `bible/` (world, magic, glossary) and the `timeline.md` spine (E01…), every place the source
   **contradicts itself** becomes a **flagged decision in the queue**, not a guess —
   *"goblin named Grix in ch.2, Grax in ch.5 → which is canon?"* The owner picks; the choice is
   recorded in the bible. Canon is what the owner ratifies, never merely what the text last said.
3. **Infer character base-vs-evolution, conservatively.** The source only shows characters at
   *later* states. The room proposes, per character: a **base persona** (earliest-appearance
   self) + a small set of **evolution beats** anchored to timeline events — and **marks every
   inference as a proposal** for the owner to confirm, adjust, or reject. When the split is
   genuinely unclear, it asks rather than inventing a backstory.
4. **Set the target voice fresh; harvest loved-lines.** `voice/narrator.md` is authored as a
   *target* (audience age + Salvatore/Sanderson/Jordan flavor), **not** extracted from the
   weak source prose. Separately, the room proposes a `voice/loved-lines.md` list — specific
   lines/jokes worth preserving verbatim — for the owner to curate. Loved passages are
   protected via the `locked` mechanism (§5.2).
5. **Tag scenes** with `story_time` + `pov` (room-assisted; owner confirms), then the review
   loop proper begins.

Everything in steps 1–4 is **proposed and owner-ratified**; the system's job is to surface
structure and contradictions, not to declare canon.

### 10.2 Review unit & "done"

- **Review unit:** the room reviews **chapter-by-chapter**, and findings **roll up** into one
  book-level `/review-and-update` consolidation. This keeps each pass focused and the token cost
  bounded (vs. re-reading the whole book every cycle) while still letting whole-document critics
  (Tic & Repetition Hunter, Continuity) reason across chapters during the roll-up.
- **"Done" is the owner's call, not a gate.** Unlike the scientific loop, there is **no
  convergence/blocker gate** — this is creative work. The loop runs as many `/review-and-update`
  cycles as the owner wants and stops when the owner is happy. The system never loops on its own
  or blocks "completion"; it just keeps offering consolidated plans until told to stop.

## 11. Error handling & edge cases

- **No existing text and no brief** → ask what book to work on; never invent a premise.
- **ChatGPT logs are mostly prompts/chatter, or prose order is ambiguous** → the room proposes
  a split and records it in `source/extraction.md`; the owner confirms before it becomes the
  manuscript. Never discard source content silently.
- **Source contradicts itself during ingestion** (name/fact/timeline drift) → a flagged decision
  in the queue for the owner to ratify; never canonized by "whatever the text said last."
- **Multiple chat logs in unknown order / a scene regenerated several times** → order is
  owner-confirmed (timestamps as a hint); duplicate scene variants are surfaced for the owner to
  pick the canonical one; the choice is recorded in `source/extraction.md`.
- **Character base-vs-evolution split is unclear** → the room asks rather than inventing a
  backstory; inferences are proposals, not canon.
- **A character knows something too early** (knowledge resolved at the scene's story-time is not
  yet acquired) → Continuity flags it as a blocker; never silently "explained away."
- **Two personas suggest conflicting changes** → the consolidation meta-editor reconciles them
  into one decision for the owner (with the trade-off stated); the plan never contains two
  contradictory items for the same text.
- **Edit proposed against `locked` content** → refused at the source; critics may *comment* on
  locked scenes/passages but the plan cannot contain a rewrite of them.
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
  a scene `after E04` resolves with the E04 beat only. Include a `[history]`-anchored beat and a
  flashback to it (unified-spine resolution).
- **Knows-too-early detection** — a scene `before` a knowledge beat in which the character acts on
  that knowledge produces a blocker Continuity finding.
- **Conflicting-suggestion reconciliation** — two personas proposing opposite changes to the same
  line yield one reconciled decision in the plan, never two contradictory items.
- **Front-matter export** — the EPUB/PDF carries a title page (`title`/`author`), the dedication,
  and a TOC, with chapters in `manuscript/` file order.
- **Direct-to-main commits** — drafts and each cycle commit to `main`; `roles/` and `ideas/`
  remain at the repo root, not stranded on a branch.
- **`/note` capture** — `/note` appends an anchored note to `notes/queue.md` and triggers no
  change on its own.
- **ChatGPT-log ingestion** — a fixture log with interleaved prompts/chatter/prose splits into
  prose-only manuscript scenes, with `source/extraction.md` recording what was dropped; nothing
  is lost without a record.
- **Contradiction flagging on bootstrap** — a source that names a character two ways produces a
  flagged decision in the queue (not a silently-chosen canon).
- **Locked content is never rewritten** — a `locked: true` scene (and an inline
  `<!-- lock -->…<!-- /lock -->` passage) can receive comments but produces no rewrite items in
  the revision plan.
- **Fresh target voice** — `voice/narrator.md` is authored as a target, not copied from the
  source prose; loved-lines are preserved verbatim where marked.
- **Chapter-by-chapter roll-up** — per-chapter passes consolidate into one book-level
  `/review-and-update` plan; whole-document critics still reason across chapters at roll-up.
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
