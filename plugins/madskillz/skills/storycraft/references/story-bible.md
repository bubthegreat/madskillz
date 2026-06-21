# Story bible — file shapes and update rules

The `bible/` directory is the single source of truth for all canon. Every persona reads it before drafting or reviewing; only the Continuity Checker → Bible Keeper path writes it, and only with adjudicated, user-visible canon.

## File shapes

### `premise.md`

```markdown
# Premise

## Logline
<One- or two-sentence hook: protagonist, conflict, stakes.>

## Themes
- <theme>
- <theme>
```

### `characters.md`

One section per character:

```markdown
# Characters

## <Character name>

- **Role:** <protagonist | antagonist | supporting | …>
- **Voice:** <how they speak — cadence, vocabulary, verbal tics>
- **Traits:** <3–5 adjectives or short phrases>
- **Arc:** <where they start, what changes, where they end>
```

### `world.md`

```markdown
# World

## Setting
<Time, place, physical environment.>

## Rules
<Governing logic — magic system, technology limits, social norms, etc.>

## Factions
<Groups, institutions, or communities with stakes in the story.>
```

### `outline.md`

```markdown
# Outline

## Chapter 1 — <title>
<Beat: what happens, who moves, what changes.>

## Chapter 2 — <title>
<Beat.>
…
```

One section per planned chapter. The beat is a compact description (2–5 sentences) of the chapter's events and their narrative function.

### `timeline.md`

```markdown
# Timeline

| Event | When | Notes |
|---|---|---|
| <event> | <in-story date/time or relative marker> | <optional clarification> |
```

Ordered chronologically by in-story time. Add every event that future chapters could contradict.

### `style-guide.md`

```markdown
# Style guide

## Voice
<Defining qualities: register, pace, humor level, emotional temperature.>

## POV / tense
<Point of view and narrative tense. Note any permitted deviations.>

## Do
- <encouraged device or pattern>

## Don't
- <prohibited device or pattern>

## Banned phrases
<Mirror of `book.yaml: banned_phrases[]`. List each phrase explicitly — these are
enforced verbatim by the Repetition Auditor and Dialogue Doctor.>
- "<phrase>"
```

### `glossary.md`

```markdown
# Glossary

| Term | Canonical spelling | Definition / usage note |
|---|---|---|
| <term> | <exact form to use everywhere> | <what it means or how it is used> |
```

All proper nouns, invented words, place names, and faction names live here. The canonical spelling column is the ruling form; all other spellings are wrong.

## Read/write rule

- **All personas read** the full `bible/` before drafting, editing, or reviewing.
- **Only the Bible Keeper writes** `bible/*`:
  - **Phase 1 (co-design):** the Bible Keeper writes the initial `bible/*` from the Showrunner's co-design proposal once the user approves it at the co-design checkpoint (see `co-design.md`).
  - **Phase 2 (drafting):** subsequent canon changes are written only after the Continuity Checker proposes them, the Editor-in-Chief adjudicates, and the user has seen and approved them at a chapter checkpoint.
- No persona may invent or record new canon outside this path.
- Rejected or uncertain proposals are logged in `notes/checkpoints.md`, not written to the bible.
