# Phase 6 — Continuity QA

Generated takes are not deliverables until someone has looked at them. This phase catches
drift **before** it propagates into a scene's worth of downstream shots.

Run QA per scene, not once at the end. Finding that Elena's jacket changed colour in shot 4
is cheap; finding it after shots 5–20 were extended from shot 4 is not.

## Extracting frames

`assemble.py --dry-run` shows the conform commands; for QA you want stills. Three frames
per take — head, middle, tail — because drift usually appears at the tail:

```
ffmpeg -y -i generated/s01-002_t01.mp4 -vf "select='eq(n\,0)'" -frames:v 1 qa/s01-002_t01_head.png
ffmpeg -y -i generated/s01-002_t01.mp4 -vf "thumbnail" -frames:v 1 qa/s01-002_t01_mid.png
ffmpeg -y -sseof -0.2 -i generated/s01-002_t01.mp4 -frames:v 1 qa/s01-002_t01_tail.png
```

Read the extracted frames with the Read tool — they render visually, which is what makes
this a real check rather than a metadata comparison.

## The comparison set

For each take, compare against three things:

1. **The plate** — is this still the same character? Face, hair, wardrobe, distinguishing
   features from the lockup.
2. **The previous shot in the scene** — same lighting state, same props, same time of day,
   same wardrobe.
3. **The shot row's intent** — is this the size, angle, and action that was asked for? The
   model frequently ignores camera direction.

## What to flag

The Script Supervisor leads. Flag by name, with severity:

| Finding | Severity | Typical fix |
|---|---|---|
| Different face from the plate | blocker | Re-take in `reference` mode; sharpen the lockup |
| Wardrobe changed mid-scene | blocker | Re-take; check the shot names the right lockup |
| Lighting state flipped (day↔night, key side moved) | blocker | Re-take; name the practical sources in the lockup |
| Story-critical prop missing or wrong | blocker | Re-take with the prop in `prompt_extra` |
| Wrong shot size or angle delivered | major | Re-take; simplify the camera instruction |
| Warping, extra limbs, morphing hands | major | Re-take; if only in the tail, pull `edit_out` in |
| On-screen text or watermark | major | Add to `negative`; re-take |
| Minor texture or background variation | minor | Usually accept — audiences do not track this |
| Drift in the final second only | minor | Trim it. This is what handles are for |

**The trim-first principle:** before spending on a re-take, check whether the problem is
inside your handles. A shot generated at 8s and cut to 4s has four seconds of slack — a
tail that morphs at 7s never reaches the screen. Pull `edit_out` in and move on.

## Selecting takes

Once a shot passes, the user picks the take. Record it:

```yaml
select: s01-002_t02.mp4
```

Without `select`, `assemble.py` falls back to the first take on disk — which is a
reasonable default but is not a decision. Record the choice explicitly for anything the
user actually looked at, and note why in `notes/checkpoints.md` when the reason is
interesting.

**Checkpoint:** present the takes, the QA findings, and the recommended selects. The user
approves. Commit `film: <slug> qa s01`.

## When drift will not resolve

If a shot drifts across three takes, stop re-rolling — you are paying for the same failure
repeatedly. Escalate in this order:

1. Switch `text` → `reference`, or `extend` → `reference`. Mode is the usual culprit.
2. Re-anchor: replace a deep `extend` chain with a fresh `reference` shot.
3. Sharpen the lockup with a more distinctive feature.
4. Re-plate the character, then re-take.
5. Change the shot. A framing the model cannot hold is a framing to design around — split
   it, widen it, or cut to a reaction instead.

Report the real state at every step. A shot that never resolved is reported as unresolved,
not quietly dropped from the cut.
