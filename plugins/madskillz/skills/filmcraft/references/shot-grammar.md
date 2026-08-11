# Shot grammar — decomposing beats into generatable shots

The rules the Director and Editor apply in Phase 3, and the reasoning behind the checks in
`shot_check.py`. Deterministic checks catch the mechanical violations; this document covers
the judgment the checks cannot make.

## The clip budget

Grok Imagine 1.5 generates 1–15 seconds. That is a **generation** budget, not an edit
budget.

**Generate long, cut short.** Professional coverage gives the editor handles — extra frames
at the head and tail. Generate 8 seconds, cut to 3.5. The handles absorb the model's two
most common failures: a slow first beat while the subject settles, and a drift or morph in
the final second. `edit_in` / `edit_out` exist for exactly this.

A useful default: generate 8s, plan to use the middle 4–5s.

## What fits in one shot

One shot carries **one** of each:

| Element | Budget |
|---|---|
| Camera move | One. A push *or* a pan — not a push-then-pan |
| Subject action | One completed action, or one action beginning |
| Emotional turn | One |
| Location / time | Zero changes. A change of either is a cut, i.e. a new shot |
| Dialogue | ~2.5 words/sec, minus ~1.2s headroom |

Dialogue math, since it is the most common overrun: an 8-second clip has ~6.8 usable
seconds, which is **~17 words**. A 6-second clip is ~12 words. `shot_check.py` enforces
this and tells you the word count that fits.

If a line does not fit, the options are: cut the line, raise the duration, or split across
two shots — usually the last one, since a reaction cut mid-line is good filmmaking anyway.

## Shot sizes

Ordered wide → tight. The **distance** between adjacent shots is what makes a cut work.

| Code | Size | Typically used for |
|---|---|---|
| `EWS` | Extreme wide | Geography, scale, isolation |
| `WS` | Wide | Establishing; full figure in context |
| `MWS` | Medium wide | Knees up; blocking between characters |
| `MS` | Medium | Waist up; the workhorse |
| `MCU` | Medium close-up | Chest up; the dialogue default |
| `CU` | Close-up | Face; emotional beats |
| `ECU` | Extreme close-up | Detail — an eye, a hallmark, a trigger finger |

**The two-step rule.** Consecutive shots of the same subject should differ by at least two
steps on this ladder, or change angle. `MS → MCU` at the same angle reads as a glitch;
`MS → CU` reads as a cut. `shot_check.py` flags zero-step (major) and one-step (minor).

## The 180-degree rule

Draw a line through the two subjects of a scene. Keep the camera on one side of it. Cross
it and the audience sees the geography invert — characters suddenly face the wrong way and
the scene stops making spatial sense.

In `shots.yaml` this is the `screen_dir` field. Within a scene, consecutive shots should
not flip `L→R` ↔ `R→L`. The legitimate ways across:

- a **neutral** shot between them (`to-cam` / `from-cam`), which resets the audience
- a visible camera move that carries the audience across
- doing it deliberately for disorientation — set `axis_break: true` to record the intent

`shot_check.py` flags unmarked flips. It cannot tell an intentional axis break from a
mistake, which is why the field exists.

## Coverage

Every scene needs, at minimum:

1. **An establishing shot** — a wide that tells the audience where they are. `shot_check.py`
   fails a scene with no `EWS`/`WS`/`MWS`.
2. **Coverage of whoever is talking** — usually MCU or CU.
3. **A reaction** — the listener. This is the shot beginners omit, and it is the one that
   makes dialogue scenes cuttable.
4. **An out** — something to cut to when a take goes wrong. A detail ECU of a prop earns
   its cost many times over.

## Cutting rhythm

- Vary shot length. A run of identical 4-second cuts feels mechanical.
- Tension shortens cuts; reflection lengthens them.
- Do not cut on nothing. Cut on an action, a look, a line, or a sound.
- The wide at the head of a scene can run long; the beats inside it should not.

## Choosing a generation mode

From `grok-api.md`, restated as a decision:

- Shot contains a recurring character → **`reference`**, always. Pass the plate.
- Shot continues the previous shot with no cut (a held moment, a slow reveal) →
  **`extend`**. Watch the chain depth; drift compounds per hop.
- You have a specific still you want animated → **`image`**.
- Establishing shot, landscape, texture, no recurring subject → **`text`** is acceptable.

Using `text` for a character shot is the single most common cause of the face changing
between cuts.

## Prompt construction

`generate.py` compiles prompts deterministically in this order, and the order matters —
leading tokens dominate the frame:

1. **Camera** — size, angle, move
2. **Beat** — what happens
3. **Character lockups** — verbatim, never paraphrased
4. **Location plate** — verbatim
5. **`prompt_extra`** — shot-specific art direction
6. **Look book** — stock, lens, lighting, palette, grade
7. **Dialogue** — attributed to the speaker
8. **Negative terms** — last

Because compilation is deterministic, identical inputs give byte-identical prompts. If two
takes differ, the model varied — not the prompt. That property is what makes continuity
debugging tractable, so do not hand-edit compiled prompts; change the shot row or the bible
and recompile.
