# Phase 1 — Co-design protocol

Interactive. The Director leads; the user decides. Nothing is generated in this phase, so
it costs nothing to iterate — spend the time here rather than discovering the problem after
$50 of clips.

Work through the sequence below, one topic at a time. Do not dump all questions at once,
and do not proceed to Phase 2 without explicit approval of the look book, casting, and beat
sheet.

## 1. Logline and runtime

Get a one-sentence logline: who wants what, and what is in the way.

Then the runtime target, and be concrete about what it implies:

| Runtime | Shots | Generated seconds (3 takes) | Approx cost at 720p |
|---|---|---|---|
| 30s scene | ~10 | 240 | ~$17 |
| 2–5 min short | 25–50 | 600–1,200 | ~$40–85 |
| 10 min | ~100 | 2,400 | ~$170 |
| 90 min feature | 900+ | 21,600+ | ~$1,500+ |

State the number before the user commits to a runtime. If they want a feature, say plainly
what it costs and recommend proving a short first — but if they reaffirm, build what they
asked for and record the budget.

## 2. Genre, tone, references

Ask for two or three **existing films** as visual references. This is faster and more
precise than adjectives — "shot like *Children of Men*" carries lens, movement, and grade
in three words.

## 3. Look book → `bible/look.yaml`

The global visual contract, appended to every prompt. Fill each field:

```yaml
stock: shot on 35mm Kodak Vision3 500T
lens: 40mm spherical, shallow depth of field
lighting: single warm practical key, deep falloff, cool rain light from the window
palette: amber and slate blue, desaturated mid-tones
grade: gentle filmic contrast, lifted blacks
negative: text overlays, watermarks, extra fingers, modern logos, lens flares
```

- **`stock`** sets the overall texture. Naming a real stock is more reliable than "cinematic."
- **`lens`** — a focal length implies a whole grammar. 28mm is wide and unstable; 85mm is
  compressed and intimate. Pick one package and hold it.
- **`negative`** always includes text overlays and watermarks. Generative video adds them
  unprompted with surprising frequency.

Keep the look book **global**. Per-shot deviation belongs in `prompt_extra`, not here —
editing the look book mid-film changes every shot generated afterwards.

## 4. Characters and locations

Draft lockups with the user, then hand to Phase 2 for plates. See `casting.md` for what
belongs in a lockup. Resist the urge to cast a large ensemble: every character is a plate,
a continuity risk, and a line item.

## 5. Audio strategy → `film.yaml: audio_strategy`

Decide per film. Grok Imagine 1.5 generates synchronized native audio at no extra cost,
which makes this a real choice rather than a formality.

| Strategy | Choose when | Trade-off |
|---|---|---|
| `native` | Dialogue-light, ambience-driven, or you want speed | Sound differs shot to shot; no consistent score |
| `post` | Dialogue-heavy, or you have music/VO | Most control, most work; generate silent, mix at assembly |
| `hybrid` | You want the model's ambience but reliable dialogue | Keep native ambience as texture, lay dialogue over it |

Ask directly: *"Does anyone speak on camera?"* If yes and it matters, lean `post` or
`hybrid` — lip-sync on generated actors is the weakest link in the pipeline. If the film is
atmosphere over dialogue, `native` is genuinely good and much faster.

Under `native` or `hybrid`, capture voice references during casting.

## 6. Beat sheet → `bible/beats.md`

Scene-by-scene, one line each: what changes in this scene. Not shots yet — Phase 3 does
that decomposition.

Sanity-check the beat count against the runtime. A 3-minute short holds 4–8 beats. Twenty
beats in three minutes means nothing lands.

## 7. Write `film.yaml` and checkpoint

Write `film.yaml`, `bible/look.yaml`, draft `bible/casting.yaml`, `bible/beats.md`. Set
`status: co-design`. Run `estimate_cost.py` on the projected shot count so the user sees a
number now, not after the shot list exists.

**Checkpoint:** present the look book, the cast, the beat sheet, and the projected cost.
Get explicit approval. Commit `film: <slug> look book v1`. Then Phase 2.

## Adapting instead of originating

If the user is adapting a storycraft book, most of this is already written — see
`storycraft-handoff.md`. Do not re-run co-design from scratch; import the bible and confirm
the deltas.
