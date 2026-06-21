# Repo layout & config resolution

## Config resolution

Read `~/.claude/storycraft/config.yaml` for two keys:

```yaml
stories_repo: ~/stories   # path to the user's stories git repo
author: <name>
```

If the file is missing or `stories_repo` is unset, prompt the user for the path and offer to `git init` it. Record the chosen path back into the config file. Never hardcode a path or owner; this skill is usable by anyone.

## Per-book layout

Each book occupies one folder inside the stories repo. `<book-slug>` is kebab-case (lowercase, hyphens, no spaces).

```
<stories-repo>/
  <book-slug>/
    book.yaml              # metadata + generation parameters (see fields below)
    bible/
      premise.md           # logline + themes
      characters.md        # roster with per-character profile
      world.md             # setting, rules, factions
      outline.md           # chapter-by-chapter beats
      timeline.md          # ordered canonical events
      style-guide.md       # voice, POV/tense, do/don't, banned phrases
      glossary.md          # canonical names, terms, spellings
    chapters/
      01-<slug>.md         # zero-padded chapter files
      02-<slug>.md
      …
    notes/
      ideas.md             # this book's parking lot
      checkpoints.md       # log of per-chapter user approvals and redirects
    build/
      <book-slug>.epub     # committed — syncs to e-reader via repo
      <book-slug>.pdf
  ideas/                   # cross-book concept backlog so ideas are never lost
    <concept>.md
```

Omit any subfolder that has no content. Never create empty placeholders.

## `book.yaml` fields

All of the following keys are required when present; omit optional keys only if explicitly not applicable:

| Key | Description |
|---|---|
| `title` | Book title |
| `author` | Author name (from config unless overridden) |
| `audience` | Target audience (e.g. "children ages 6–9") |
| `reading_level` | Reading level (e.g. "early chapter book") |
| `genre` | Genre (e.g. "fantasy", "adventure") |
| `tone` | Tone descriptors (e.g. "funny, warm, slightly irreverent") |
| `pov` | Point of view (e.g. "third-person limited") |
| `tense` | Narrative tense (e.g. "past") |
| `target_chapters` | Planned chapter count |
| `target_words_per_chapter` | Target word count per chapter |
| `status` | Current state: `co-design` \| `drafting` \| `assembling` \| `done` |
| `banned_phrases` | List of crutch phrases to never use (e.g. `["And X nodded", "suddenly"]`) |
| `illustrate` | Whether illustration briefs are active: `true` \| `false` |

## Naming rules

- `<book-slug>`: kebab-case — lowercase letters, digits, and hyphens only. Validate before writing.
- Chapter files: zero-padded two-digit prefix, e.g. `01-opening.md`, `02-forest.md`.

## Commit/push rule

Commit at each checkpoint with messages of the form `book: <slug> <what>` — for example:

```
book: goblin-scouts bible v1
book: goblin-scouts ch.01
book: goblin-scouts build
```

Never push. The user pushes manually.
