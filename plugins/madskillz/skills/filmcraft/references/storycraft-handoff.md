# Adapting a storycraft book into a film

`storycraft` produces a prose book with a story bible. filmcraft adapts one into a film.
The bibles line up closely enough that adaptation is mostly translation, not re-invention —
so **do not re-run co-design from scratch.** Import, then confirm the deltas.

## Locating the source

storycraft books live in the stories repo from `~/.claude/storycraft/config.yaml`
(`stories_repo`), one folder per book slug. Ask which book, and which chapters — adapting a
whole novel is a feature-length ask; see the cost table in `co-design.md` before agreeing
to it.

## Mapping the bibles

| storycraft | filmcraft | Translation work |
|---|---|---|
| `bible/premise.md` | `film.yaml: logline` | Compress to one sentence: who wants what, what is in the way |
| `bible/characters.md` | `bible/casting.yaml` | **The real work.** Prose profiles → 25–45 word lockups. See below |
| `bible/world.md` | `bible/casting.yaml` locations | Extract the two or three rooms that actually appear; name their light sources |
| `bible/style-guide.md` | `bible/look.yaml` | Prose voice does not translate. Ask for **film** references instead |
| `bible/outline.md` | `bible/beats.md` | Chapter beats → scene beats; most chapters are several scenes |
| `bible/timeline.md` | scene ordering + time-of-day continuity | Feeds the Script Supervisor |
| `chapters/NN-*.md` | `shots.yaml` | Phase 3 decomposition, scene by scene |

## Characters are the hard part

A storycraft character profile is written for a reader who imagines the face. A lockup is
written for a model that must draw the same face fifty times. Prose profiles are usually
too long, too interior, and not visually specific enough.

Extract only what a camera can see, then **add distinctiveness the prose did not need**.
A novel can say "an ordinary-looking man in his sixties" and the reader fills it in; a
generative model will produce a different ordinary man every call. Propose concrete
features — the wire-rim glasses, the elbow patches, the ink-stained fingers — and get the
user's approval, because you are adding canon the book did not have.

Flag this explicitly at the checkpoint: *"the book does not describe Marcus's face; I have
proposed these features so he stays the same person across shots."*

## What does not survive adaptation

Say so plainly rather than trying to shoot it:

- **Interiority.** Thoughts, memories, and narration have no camera equivalent. Either
  externalize them into action, give them to dialogue, or cut them.
- **Time compression.** "Three years passed" is a title card or a cut, not a shot.
- **Prose voice.** The thing storycraft works hardest to protect does not transfer. The
  look book is the film's voice, and it is a new decision.
- **Chapter structure.** Chapters are not scenes. Expect to re-break the story.

## Procedure

1. Confirm the book and the chapter range.
2. Copy the story bible into the film's `bible/` as a starting point — never edit the
   storycraft repo. The two repos stay separate; filmcraft only reads.
3. Translate each mapping above, surfacing every place you added visual canon.
4. Run the co-design checkpoint on the **deltas only**: the look book (genuinely new), the
   lockups (newly specific), and the scene breakdown.
5. Proceed to Phase 2 casting.

Record the provenance in `film.yaml`:

```yaml
adapted_from:
  repo: ~/stories
  book: the-sock-goblin
  chapters: [1, 2, 3]
```

so the film knows where it came from when someone picks it up months later.
