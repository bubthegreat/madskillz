# scientific-podcast: turn a research discussion into a faithful podcast script

**Date:** 2026-06-20
**Status:** Design approved (brainstorming) — pending written-spec review
**Branch:** writing-skills

## 1. Context

While exploring ideas with the scientific skills (`scientific-peer-review`, `scientific-study`),
the owner has long, real discussions — but the medium is async and batched: he fires ~10
questions in a row for convenience, and the agent answers ~10 in a row. That transcript is a
faithful record of the *thinking*, but it does not read like a conversation.

The owner wants to turn such a discussion into a **podcast script** he can feed to AI/TTS to
produce an actual podcast. The script must **reframe** the raw async material into a coherent
two-person discussion: de-batch the Q-block/A-block into real back-and-forth, organize tangents
(weave them back, or label them and refocus), and order the material so it flows like a real
episode rather than a chronological dump.

This is a **standalone skill**, a *sibling to `blog`* — same fundamental shape (take a real
journey and re-narrate it faithfully in a chosen format, reading the same provenance source),
same hard non-fabrication stance — but the output is a two-speaker script instead of a prose
post. It is **not** part of `story-studio`, and it does **not** modify `blog`; it only **reads**
`blog`'s voice profile.

It is scoped to **research/scientific discussions** (per the `scientific-` name), but the
reframe core is built generically so a future general `podcast` skill could reuse it.

## 2. Goals and non-goals

**Goals**
- A standalone `scientific-podcast` skill that turns a real research discussion into a faithful,
  coherent **two-speaker podcast script** ready for AI/TTS.
- **Dual-source**, like `blog`: works on the **live session**, or a **pointed-at study folder**
  (`journey/transcript.md`, `review/cycle-*.md`, `paper.md`).
- The **reframe engine**: de-batch → thread → tangent-discipline → render.
- **Host = the owner's voice** (read-only reuse of `blog`'s voice profile); **guest = a neutral
  domain expert**.
- A **labeled script with light production cues** (segment headers, `HOST:`/`GUEST:` lines,
  `[tangent]…[back to main]` markers, optional intro/outro) — tool-agnostic.
- An **optional, pluggable audio render** step using a local, permissively-licensed TTS, with
  the script as the always-guaranteed output (§6).

**Non-goals**
- Inventing content. Reordering, condensing, and bridging transitions are allowed; fabricating
  questions, answers, or claims is not.
- Maintaining a voice profile (it reuses `blog`'s, read-only).
- Posting to any podcast platform.
- A hard dependency on any TTS model. Audio is optional and pluggable.

## 3. Integrity stance (non-negotiable, mirrors `blog`)

1. **Correct even when conversational.** No wrong explanation for the sake of flow.
2. **The discussion is real.** Never invent a question or an answer that was not actually
   asked/given. Smoothing, condensing, and bridging transitions are fine; fabricating content
   is not. A bridge line is clearly connective tissue, not a new claim.
3. **Faithful attribution.** Host lines are the owner's real questions, consolidated; guest
   lines are faithful to the agent's real answers. Anything inferred is flagged.
4. **No fabricated citations.** A real, resolvable source, or an honest "look that up."
5. **Honest about missing material.** If the source has no real discussion (e.g. only a paper),
   say so and offer a clearly-labeled *constructed* explainer — never pass a fabricated
   conversation off as real.

## 4. Shape and file layout

```
plugins/madskillz/skills/scientific-podcast/
  SKILL.md                       # gather source -> reframe -> render script -> (optional) audio
  references/
    reframe.md                   # de-batch / thread / tangent-discipline algorithm
    script-format.md             # speaker labels, segment headers, cue vocabulary, intro/outro
    audio-render.md              # optional, pluggable local-TTS rendering (Kokoro/Dia2/VibeVoice)
```

- Reads `blog`'s live voice profile read-only: `~/.claude/voice/voice.md` (fallback to `blog`'s
  seed `references/voice.md`). It does **not** write to it.
- Default output: `~/.claude/voice/podcasts/<slug>.md` (or a path the owner gives). Optional
  audio alongside it.

## 5. The reframe engine (the real work)

Detailed in `references/reframe.md`:

1. **Extract** the real exchanges from the source — the owner's questions and the agent's
   answers — from the live session or the study artifacts. When the discussion spans **multiple
   sessions/logs**, merge them (order by the owner's instruction or by timestamps, confirmed)
   into one exchange set before reframing.
2. **De-batch** — pair each question with its answer and interleave into true
   Q → A → Q → A turns, dissolving the "10 questions then 10 answers" artifact.
3. **Thread** — group exchanges into coherent topic **segments** and order them for *narrative*
   flow (hook → build → payoff), not chronology. Related exchanges merge; redundant ones
   condense. **Episode shape is tunable** — the owner can set a target length / segment count,
   and the engine condenses or selects threads to fit while disclosing what was cut.
4. **Tangent discipline** — a side-thread is either **woven back** into its main thread, or
   **explicitly marked** `[tangent: …]` and then **refocused** `[back to main]`. Never left
   dangling.
5. **Render** — emit the script per `references/script-format.md`.

## 6. Speaker format, script format, and optional audio

### 6.1 Speakers
**Host = the owner**, voiced using `blog`'s voice profile (curious, deadpan-ironic), asking his
real questions. **Guest = a neutral domain expert**, giving the real answers. Two voices, an
interview. The host borrows the voice profile's *attitude*, rendered in **speakable cadence** —
spoken lines are shorter and more conversational than written blog prose, so the script reads
naturally aloud rather than as an essay with names attached.

### 6.2 Script format (`references/script-format.md`)
Labeled script with light production cues:

```
# <Episode title>
[intro]                              # optional

## Segment 2: Are the citations real?
HOST: So wait — how does the reviewer know a citation is real and not just plausible-sounding?
GUEST: Great question. It actually fetches the source and checks…
[tangent: what "hallucinated citation" means]
GUEST: …
[back to main]
HOST: …

[outro]                              # optional
```

The labels and cues are deliberately chosen to be **audio-ready**: `HOST:`/`GUEST:` map onto
two-speaker TTS speaker tags; nonverbal cues like `(laughs)` map onto dialogue-model markers.
So enabling audio requires **no change to the script**.

### 6.3 Optional audio render (`references/audio-render.md`)
The script is the always-guaranteed output. **If** a local, permissively-licensed TTS is
detected, an optional step renders multi-voice audio — mapping HOST and GUEST to distinct
voices. No third-party subscription anywhere in the path.

Recommended engines (all Apache-2.0 or MIT, fully local; verified 2026-06):

| Engine | License | Fit | Hardware |
|---|---|---|---|
| **Kokoro-82M** | Apache-2.0 | Several built-in distinct voices; assign one to HOST, one to GUEST, concatenate. **Default** — no GPU needed. | <2 GB / CPU-capable |
| **Dia2** (Nari Labs) | Apache-2.0 | Purpose-built two-speaker dialogue (`[S1]`/`[S2]` + nonverbal cues); most natural two-person feel. | ~10 GB VRAM (GPU) |
| **VibeVoice-1.5B** | Apache-2.0 | Up to 4 distinct speakers, ~90 min — long-form podcasts/audio dramas. | GPU |
| **Chatterbox-Turbo** | MIT | Voice cloning + emotion control; benchmarked vs ElevenLabs. | GPU, low-latency |

Selection: Kokoro when no GPU; Dia2/VibeVoice when a GPU is present. Missing TTS → produce the
script and report that audio was skipped; never fake audio.

## 7. Data flow

```
source (live session  OR  study folder: journey/transcript.md, review/cycle-*.md, paper.md)
        │
        ▼   extract real Q/A
   de-batch → thread → tangent-discipline        (references/reframe.md)
        │
        ▼   render with owner voice (host) + expert voice (guest)
   labeled script (segments, HOST/GUEST, [tangent]…[back to main], optional intro/outro)
        │
        ├─► save  ~/.claude/voice/podcasts/<slug>.md   (always)
        └─► OPTIONAL: local TTS → multi-voice audio     (if a model is installed)
```

## 8. Error handling & edge cases

- **No discussion available** (only a paper) → say so; offer a clearly-labeled *constructed*
  explainer, never a faked conversation.
- **No voice profile yet** → fall back to `blog`'s seed voice; note that the host voice is the
  seed, not the refined profile.
- **A tangent that cannot be tied back** → label it and refocus, or drop it with a noted reason;
  never leave it dangling.
- **Sprawling source** → thread and condense aggressively; the script is a curated discussion,
  not a full transcript. Note what was condensed.
- **Discussion spans multiple sessions/logs** → merge them in an owner-confirmed order
  (timestamps as a hint) before reframing; one episode out of many sessions.
- **Owner sets a target length/segment count** → fit by condensing or selecting threads, and
  disclose what was cut; never fabricate filler to pad to length.
- **TTS not installed / no GPU for the chosen model** → produce the script, fall back to
  Kokoro/CPU if possible, else skip audio and report; never fake audio.
- **Asked to auto-publish to a podcast platform** → out of scope; deliver the script (and
  optional audio file).

## 9. Testing

- **De-batch** — a fixture with a 5-question block then a 5-answer block reframes into 5
  interleaved Q→A turns with correct pairing.
- **Tangent discipline** — a fixture containing a side-thread is either woven back or emitted
  with `[tangent: …]` + `[back to main]`; never dangling.
- **No-fabrication** — given a source, every guest claim in the script traces to a real answer;
  inserted text is limited to connective transitions (checked against the source).
- **Voice reuse** — host lines render using `~/.claude/voice/voice.md` when present; clean
  fallback to the seed when absent (no new profile written).
- **Audio optionality** — with no TTS installed, the script is produced and audio is reported as
  skipped; with a stub TTS present, the render step is invoked and maps HOST/GUEST to distinct
  voices.
- **Skill triggering** — eval prompts (e.g. "make a podcast script from my peer-review
  discussion", "turn this study's journey into an interview") route here, not to `blog`.
