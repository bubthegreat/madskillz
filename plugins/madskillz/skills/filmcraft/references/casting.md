# Casting & plates — the continuity mechanism

Phase 2. This is the highest-leverage step in the skill: generative video has no memory
between calls, so every clip re-invents anything you have not pinned down. Casting pins it
down twice — once in words (the **lockup**) and once in pixels (the **plate**).

Do this before the shot list depends on it. Re-casting after 40 shots are written means
regenerating all 40.

## The lockup

A frozen descriptor block, 25–45 words, pasted **verbatim** into every prompt featuring
that character. It is canon: paraphrasing it recasts the character, which is why the
integrity stance treats rewording as a canon change needing approval.

```yaml
characters:
  elena:
    lockup: >-
      ELENA, early thirties, sharp jaw, dark curls tied back, faint scar through the
      left eyebrow, olive canvas field jacket over a grey henley, brass pendant at the
      throat, no makeup
    plate: bible/plates/elena-03.png
```

**What belongs in a lockup:**

- Age bracket, build, face shape
- Hair — colour, length, how it is worn
- One or two **distinctive, unusual** features (the scar, the pendant, the crooked tooth).
  These are what the model latches onto; a face described only in generic terms will drift.
- Wardrobe, specifically. "Jacket" drifts; "olive canvas field jacket" holds.
- Anything that must never change

**What does not belong:**

- Emotion or expression — that is the shot's job, and baking it in fights every beat
- Action or pose — same reason
- Camera or lighting — that is the look book
- Backstory the camera cannot see

**Wardrobe changes** get their own lockup entry, not an edit to the existing one:
`elena` and `elena_rain` are two lockups. The shot picks the right one. Editing a lockup
mid-film silently changes every shot generated after it.

## The plate

The canonical reference still, passed as `reference_images` in `reference` mode. Words
constrain; pixels lock. Use both.

**Producing a plate:**

1. Generate 3–4 candidate stills from the lockup (`plate_variants` in `film.yaml`, costed
   by `estimate_cost.py`).
2. Show them to the user. **The user picks.** This is a checkpoint.
3. Save the pick to `bible/plates/<name>-NN.png` and record the path in `casting.yaml`.
4. Commit — plates are small and load-bearing, so they are versioned.

**What makes a good plate:** neutral expression, clear frontal or three-quarter face, even
lighting, full wardrobe visible, no strong pose. A plate shot in dramatic side-light bakes
that light into every downstream shot.

Keep a rejected plate in the folder if it might be wanted later; note in `checkpoints.md`
which was chosen and why.

## Locations

Same mechanism, less strict — rooms tolerate more variation than faces do.

```yaml
locations:
  study:
    lockup: >-
      A cramped book-lined study, rain-streaked sash window, one brass desk lamp, papers
      in drifts across an oak desk
```

Name the **light sources** explicitly. The lamp and the window in that lockup are what keep
the room's lighting consistent across shots that were generated hours apart.

## Voices

When `audio_strategy` is `native` or `hybrid`, a voice reference keeps a character sounding
like themselves:

```yaml
voices:
  elena_vo:
    ref: bible/voices/elena.wav
```

Referenced from a shot as `refs.voice: elena_vo`. `generate.py` resolves the id to the path.

Under `post`, skip voices entirely — dialogue is recorded or synthesized during assembly.

## Verification before the shot list

`shot_check.py` fails on any shot referencing a character or voice with no casting entry.
Run it after casting and before writing shots in bulk — it is cheaper to find a missing
plate at that point than after the shot list is built around it.

## When a character still drifts

In order of cost:

1. **Check the mode.** A drifting character shot is usually `text` mode. Switch to
   `reference`.
2. **Sharpen the lockup.** Add a distinctive feature. Generic descriptions drift.
3. **Re-plate.** A plate with an unusual pose or strong light generalizes badly.
4. **Shorten extension chains.** Drift compounds per hop; re-anchor with a fresh
   `reference` shot rather than a fourth `extend`.
5. **Accept and cut around it.** Sometimes the drifted take is only bad in the last second —
   pull `edit_out` in. This is what handles are for.
