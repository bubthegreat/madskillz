# research-blog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a routed `research-blog` skill that turns a research journey into a first-person, funny-but-accurate blog post in the owner's voice, and saves the human↔assistant dialogue as study provenance.

**Architecture:** A new sibling skill under `plugins/madskillz/skills/research-blog/` (SKILL.md + two reference files + evals), routed from the `research` command, plus light edits to `scientific-study` (repo layout, optional handoff) — mirrors how the rest of the `scientific-*` family is built. No code; markdown skills validated via evals + writing-skills pressure scenarios.

**Tech Stack:** Markdown skill files; `evals/evals.json` triggering suites; Claude Code plugin (`madskillz` v0.7.0).

**Spec:** `docs/superpowers/specs/2026-06-20-research-blog-design.md`

## Global Constraints

Copied verbatim from the family conventions and the spec — every task implicitly includes these:

- **Descriptions are triggers-only** (no workflow summary), keep all trigger phrases — per `writing-skills` SDO and the Part 1 optimization.
- **Integrity stance is non-negotiable and explicit** in the SKILL: science correct even when funny; the journey is real (no fabricated question/aha); written *as* the owner without putting claims in their mouth; honest open threads stay; **no fabricated citations**.
- **Transcript = owner's own dialogue:** committed as study provenance, **NOT part of `paper.md`**, **no privacy gate** applied to it.
- **Backfill labels reconstruction:** reconstructed turns marked `(reconstructed from artifacts)`; unrecoverable gaps stated, never invented.
- **Persona files carry a Provenance note** (created/updated date + what changed), like `experts/`.
- **Reference cross-links by filename** (e.g. `references/blog-voice.md`), no `@`-links.
- **Slugs are kebab-case.** Standalone output goes under `./research-blog/<slug>/`; nothing is pushed to `jmresearch/research` unless it is a study.
- **Commit trailer:** end every commit message with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Voice persona — `blog-voice.md`

**Files:**
- Create: `plugins/madskillz/skills/research-blog/references/blog-voice.md`

**Interfaces:**
- Produces: the voice definition consumed by SKILL.md Step 3. No code signatures; the contract is the section set: `Who I am on the page`, `Comedic influences`, `The signature arc`, `Voice rules`, `Provenance`.

- [ ] **Step 1: Create the file with this exact content**

```markdown
# Blog voice — the owner's personal science-blog persona

You are writing a blog post **as the project owner** — first person, in their voice. The goal:
share the *learning journey* of a research idea so a curious general reader finds it neat, funny,
and genuinely illuminating, and comes away feeling that science / physics / learning is *cool*.

This is a **voice**, not a set of facts. Adopt the moves below; never let them bend the science
(the skill's integrity stance: correctness outranks comedy, always).

## Who I am on the page
- A smart, curious non-specialist who is delighted to be wrong and then un-wrong. I walk in with a
  confident mental model, get corrected, and the correction is the gift.
- I think science is freaking cool and I cannot shut up about it. Enthusiasm is the baseline.
- I am the reader's stand-in: if I was confused, they were too, and we figure it out together.

## Comedic influences (concrete moves, not just names)
- **Scott Adams / Dilbert** — deadpan understatement; say the obvious-but-unspoken thing flatly and
  let the absurdity sit without overselling it.
- **The Oatmeal (Matthew Inman)** — exuberant hyperbole and tangents; the occasional ALL-CAPS
  punchline for one genuinely deserving idea; "here is why this seemingly-boring thing is secretly
  the most amazing thing in the universe."
- **Allie Brosh / Hyperbole and a Half** — self-deprecating and emotionally honest; narrate the
  internal monologue of being wrong ("I was SO sure"); land the exact beat where it clicks.
- **Dave Chappelle** — conversational storytelling and timing; set up, hold, land; plant a callback
  early and pay it off at the end; willing to sit in the genuinely weird part.

## The signature arc
1. **I thought X.** State the confident, naive mental model — relatably.
2. **Record scratch.** The moment I find out it doesn't work that way.
3. **What's actually going on.** The real science, explained plainly and *correctly*, wonder intact.
4. **...and it's cooler than my wrong version.** Why reality beat my guess.
5. **How it rewired me.** What I now see differently — often ending on the next thing I'm confused about.

## Voice rules
- First person, contractions, short punchy sentences mixed with one long enthusiastic run-on when
  the excitement earns it.
- Plain language first; every necessary technical term gets a quick, friendly in-line gloss.
- Jokes serve the explanation. If a joke would make the science wrong or misleading, cut the joke.
- Honest about the edges: "I still don't fully get Y" stays in — it's true and it's relatable.
- No fake citations, ever. Name a real, resolvable source or say "go read up on X."

## Provenance
- Created/updated: <YYYY-MM-DD via the request that produced or extended this voice>. <What each
  update changed.> The owner tunes this file over time; treat it as the living definition of "how I
  sound."
```

- [ ] **Step 2: Structural check**

Run: `grep -c '^## ' plugins/madskillz/skills/research-blog/references/blog-voice.md`
Expected: `5` (Who I am / Comedic influences / The signature arc / Voice rules / Provenance)

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/research-blog/references/blog-voice.md
git commit -m "feat(research-blog): add the owner's blog-voice persona

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Output shapes — `blog-format.md`

**Files:**
- Create: `plugins/madskillz/skills/research-blog/references/blog-format.md`

**Interfaces:**
- Produces: three shapes consumed by SKILL.md — the post arc (Steps 3), the `blog-notes` entry (Step 2), the `transcript` log (Step 1). Filenames referenced by SKILL: `blog/post-<slug>.md`, `blog/blog-notes.md`, `journey/transcript.md`.

- [ ] **Step 1: Create the file with this exact content**

````markdown
# Blog format — post arc, blog-notes, transcript

Shapes the `research-blog` skill produces. The **voice** lives in `blog-voice.md`; this file is
**structure**.

## The post (`blog/post-<slug>.md`)

Follow this arc (the voice file's signature arc, as sections):

1. **Hook** — a vivid wrong intuition, a dumb-on-purpose question, or a "so I asked…" cold open.
2. **The mental model I walked in with** — what I assumed; relatable and usually wrong.
3. **The record scratch** — the moment it turns out that's not how it works. The correction.
4. **What's actually going on** — the real science, plain and *correct*, wonder intact. A gloss for
   every technical term; a real source or an honest "read up on X" where background is needed.
5. **Why it's cool / how it reframed me** — the payoff: reality beat my guess.
6. **Kicker** — a punchy close; often "…and now I'm confused about *this* next."

Length: whatever the journey earns — usually 500–1200 words. No padding.

## blog-notes (`blog/blog-notes.md`)

One entry per genuinely-interesting question/correction, ranked by merit (best first):

```
## <short title>
- Question I asked: <verbatim-ish>
- What I assumed: <prior mental model>
- The correction: <what's actually true>
- Why it's interesting (merit): <surprise / hook strength / how much it reframed things>
- Source: <session turn | study artifact | transcript line>
- Status: strong | maybe | thin
```

Rank by merit; `thin` notes are kept but not necessarily used. Never invent a note to fill space.

## transcript (`journey/transcript.md`)

An append-friendly, speaker-tagged dialogue log — **substance only**:

```
# Journey transcript — <topic>/<short-name>
<!-- Provenance: the human<->assistant dialogue behind this study. NOT part of paper.md. -->

## <YYYY-MM-DD> <short context>
**Me:** <the question / direction / pushback, substance preserved>
**Assistant:** <the substantive answer / correction — not tool calls, not bookkeeping>
```

- Include the owner's questions, direction, and pushback; the substantive replies and corrections.
- Exclude tool-call noise, file diffs, and mechanical chatter — a record of the *thinking*, not a
  system log.
- Append across runs; never rewrite history. In backfill mode, reconstructed turns are marked
  `(reconstructed from artifacts)` and unrecoverable gaps are stated, never invented.
````

- [ ] **Step 2: Structural check**

Run: `grep -E 'post-<slug>|blog-notes|transcript.md|Status: strong' plugins/madskillz/skills/research-blog/references/blog-format.md | wc -l`
Expected: `≥4` (all three shapes + the status line present)

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/skills/research-blog/references/blog-format.md
git commit -m "feat(research-blog): add post/blog-notes/transcript format shapes

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: The skill — `SKILL.md` + `evals/evals.json` (with RED baseline)

**Files:**
- Create: `plugins/madskillz/skills/research-blog/SKILL.md`
- Create: `plugins/madskillz/skills/research-blog/evals/evals.json`

**Interfaces:**
- Consumes: `references/blog-voice.md` (Task 1), `references/blog-format.md` (Task 2).
- Produces: the routable skill `research-blog` (name used by the `research` command in Task 4 and the `scientific-study` handoff in Task 6).

- [ ] **Step 1: RED baseline (writing-skills Iron Law) — observe failure without the skill**

Dispatch a fresh subagent with NO research-blog skill present, prompt:
> "We just finished researching rainbow shells around black holes. Write me a fun blog post about the journey that I can publish."

Record the baseline: does it (a) invent a learning journey / questions the user never asked, (b) write in a generic "science blog" voice rather than a specific owner voice, (c) skip saving any transcript/provenance, (d) risk a glib-but-wrong explanation for a joke? These are the failures the skill must fix. (Expected: at least (a)/(b)/(c) occur.)

- [ ] **Step 2: Create `SKILL.md` with this exact content**

```markdown
---
name: research-blog
description: >-
  Use when the user wants to turn a research idea or study into a personal blog post in their own
  voice — "blog the journey," "write up what I learned," "turn this into a blog post," "make this
  fun to read," or "blog this study." Also saves the human<->assistant dialogue as a study
  transcript. Trigger on phrases like "blog the journey," "write up what I learned," "turn this
  into a blog post," or "blog this study." Writes the post and saves it; the human publishes it.
---

# research-blog: the learning journey, in your voice

Turn a research journey into a neat, funny, genuinely-illuminating **blog post written as the
owner** — first person, their voice — so a curious general reader comes away feeling that science is
cool. The arc is the journey itself: *I thought X -> turns out no -> here's what's actually going on
-> and it's cooler than my wrong version -> here's how it rewired me.* Alongside the post, save the
human<->assistant **dialogue** as study provenance, so it is clear which thinking was the owner's and
where the AI did the heavy lifting.

The voice lives in `references/blog-voice.md`; the output shapes in `references/blog-format.md`.

## Integrity stance (non-negotiable)
1. **The science is correct even when it's funny.** Comedy never licenses a wrong explanation. If the
   corrected understanding is itself simplified or uncertain, say so *in voice*.
2. **The journey is real.** Blog-notes come from actual questions/corrections — never an invented
   misconception or a fabricated aha. Reconstructed pieces (backfill) are labeled; gaps are stated.
3. **Written as the owner, not putting claims in their mouth.** Consolidate their real
   questions/feedback; flag anything you infer rather than quote.
4. **Honest open threads stay in.** "I still don't fully get Y" is a feature and it's true.
5. **No fabricated citations.** A real, resolvable source, or an honest "read up on X."

## Step 1 - Gather the journey and save the transcript
Identify the source(s): the live session, a study folder's artifacts (`paper.md`, `review/cycle-*`),
and/or a previously saved transcript. Write or append `journey/transcript.md` per
`references/blog-format.md` - the human<->assistant dialogue (questions, direction, pushback;
substantive replies and corrections), excluding tool-call noise. This transcript is study
provenance: committed with the study, **not** part of `paper.md`, and **not** subject to a privacy
gate (it is the owner's own dialogue).

## Step 2 - Mine blog-notes
Extract the owner's real questions, the misconceptions that got corrected, and the aha moments.
Consolidate, dedupe, and rank by interesting merit. Write/append `blog/blog-notes.md` in the shape in
`references/blog-format.md`. In a live study this accrues as the journey unfolds; standalone or in
backfill it is extracted on demand.

## Step 3 - Draft the post in the owner's voice
Using `references/blog-voice.md` and the post arc in `references/blog-format.md`, write
`blog/post-<slug>.md` - funny, vivid, and scientifically accurate. Use the highest-merit
blog-note(s) as the spine. Gloss every technical term; keep the wonder.

## Step 4 - Deliver
Show the post and where it is saved. The human publishes it. Re-run to regenerate. This skill does
not post to any platform.

## Retroactive / backfill mode
Given an existing study that lacks `journey/`/`blog/` (e.g. one predating this skill): reconstruct
the journey from whatever exists (a saved transcript, else the live session and the study artifacts),
and backfill the structure - create `journey/transcript.md` and `blog/`. Mark reconstructed turns
`(reconstructed from artifacts)`; if no real dialogue is recoverable, say so rather than inventing
one. This is "the research team puts together the missing pieces" so any prior study can be blogged.

## Relationship to the family
- Routed from the `research` command ("blog the journey / write up what I learned").
- `scientific-study` may hand off here after the PR (optional blog write-up) and may read
  `journey/transcript.md` for refinement context.
- Standalone (no study folder): write `transcript.md`, `blog-notes.md`, and the post under a local
  working dir (e.g. `./research-blog/<slug>/`); nothing is pushed to `jmresearch/research`.

## Edge cases
- No journey to draw on -> ask for a source; never invent a learning journey.
- Blog an existing / other-session study -> backfill mode; note where verbatim Q&A is missing.
- Science left unresolved -> the post is honest about the open question; no tidy fake resolution.
- Asked to auto-post to a platform -> out of scope; deliver the markdown post.
- A funny framing would require a wrong explanation -> cut the joke, keep the correctness.
```

- [ ] **Step 3: Create `evals/evals.json` with this exact content**

```json
{
  "skill": "research-blog",
  "description": "Trigger and behavior evals for the personal science-blog persona.",
  "tests": [
    {
      "id": "trigger-blog-the-journey",
      "prompt": "We just finished researching rainbow shells around black holes - blog the journey for me.",
      "should_trigger": true,
      "grading_criteria": [
        "Skill triggers",
        "Saves the human<->assistant dialogue to journey/transcript.md (provenance, not part of paper.md)",
        "Mines the owner's real questions/corrections into ranked blog-notes",
        "Drafts a first-person post in the owner's voice that keeps the science correct",
        "Does not fabricate questions, aha moments, or citations"
      ]
    },
    {
      "id": "trigger-write-up-what-i-learned",
      "prompt": "Turn what I learned in this session into a fun blog post I can publish.",
      "should_trigger": true,
      "grading_criteria": [
        "Skill triggers",
        "Follows the post arc (wrong model -> correction -> what's actually going on -> why it's cool)",
        "Funny but scientifically accurate; technical terms glossed"
      ]
    },
    {
      "id": "backfill-existing-study",
      "prompt": "Blog the study in topic/old-study - it was done before we had the blog setup.",
      "should_trigger": true,
      "grading_criteria": [
        "Backfill mode: reconstructs the journey from paper.md + review/ artifacts",
        "Creates journey/ and blog/ structure",
        "Labels reconstructed pieces and states gaps honestly rather than inventing dialogue"
      ]
    },
    {
      "id": "no-trigger-produce-study",
      "prompt": "Do a research study on whether coffee improves memory and open a PR.",
      "should_trigger": false,
      "grading_criteria": ["Routes to scientific-study, not research-blog"]
    },
    {
      "id": "no-trigger-control",
      "prompt": "What's the capital of France?",
      "should_trigger": false,
      "grading_criteria": ["Skill does not trigger"]
    }
  ]
}
```

- [ ] **Step 4: GREEN — re-run the baseline scenario WITH the skill**

Dispatch a fresh subagent with the research-blog skill available, same prompt as Step 1. Verify it now: triggers the skill; saves `journey/transcript.md` (and does not fold it into a paper); mines real blog-notes without inventing them; writes in the owner's first-person voice; keeps the science correct (cuts any joke that would require a wrong explanation). Note any new rationalization and tighten the SKILL/integrity wording if found.

- [ ] **Step 5: Structural check**

Run: `python3 -c "import json;json.load(open('plugins/madskillz/skills/research-blog/evals/evals.json'))" && grep -c '^## Step' plugins/madskillz/skills/research-blog/SKILL.md`
Expected: valid JSON (no error) and `4` step headers.

- [ ] **Step 6: Commit**

```bash
git add plugins/madskillz/skills/research-blog/SKILL.md plugins/madskillz/skills/research-blog/evals/evals.json
git commit -m "feat(research-blog): add the skill orchestration + triggering evals

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Route from the `research` command

**Files:**
- Modify: `plugins/madskillz/commands/research.md`

**Interfaces:**
- Consumes: the `research-blog` skill name (Task 3).

- [ ] **Step 1: Add the blog route.** Replace this block:

```markdown
- **Ask a domain expert directly** (consult an existing subject-matter expert, or define a new
  reusable one — no study or review required) → invoke the **`ask-an-expert`** skill.

Study design, analysis, and reproducibility packaging will be routed from here as
they are added.
```

with:

```markdown
- **Ask a domain expert directly** (consult an existing subject-matter expert, or define a new
  reusable one — no study or review required) → invoke the **`ask-an-expert`** skill.
- **Blog the journey** (turn a research idea or study into a personal blog post in the owner's
  voice, and save the chat dialogue as study provenance — "blog the journey," "write up what I
  learned," "blog this study") → invoke the **`research-blog`** skill.

Study design, analysis, and reproducibility packaging will be routed from here as
they are added.
```

- [ ] **Step 2: Extend the command description.** Replace the frontmatter `description:` line:

```markdown
description: Entry point to the scientific research family — produce an agentic-peer-reviewed study (published as a PR), run the peer-review panel on a draft, or consult/define a reusable domain expert.
```

with:

```markdown
description: Entry point to the scientific research family — produce an agentic-peer-reviewed study (published as a PR), run the peer-review panel on a draft, consult/define a reusable domain expert, or blog the research journey in the owner's voice.
```

- [ ] **Step 3: Routing check**

Run: `grep -c 'research-blog' plugins/madskillz/commands/research.md`
Expected: `≥1`. (Behavioral: a "blog the journey" request routes here, not to `scientific-study`/`scientific-peer-review` — covered by the evals `no-trigger-produce-study` control in Task 3.)

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/commands/research.md
git commit -m "feat(research): route 'blog the journey' to research-blog

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Repo layout — `journey/` + `blog/`

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/references/repo-layout.md`

- [ ] **Step 1: Add the folders to the layout tree.** Replace:

```markdown
  review/             # per cycle: the report (cycle-N.md) + the reviewed paper snapshot (cycle-N-paper.md)
  LICENSE             # CC BY 4.0 — covers paper, data, assets (from licenses/CC-BY-4.0.txt)
```

with:

```markdown
  review/             # per cycle: the report (cycle-N.md) + the reviewed paper snapshot (cycle-N-paper.md)
  journey/            # human<->assistant dialogue transcript — provenance; NOT part of paper.md
  blog/               # optional owner-voice write-up: blog-notes.md + post-<slug>.md; not the paper
  LICENSE             # CC BY 4.0 — covers paper, data, assets (from licenses/CC-BY-4.0.txt)
```

- [ ] **Step 2: Add an explanatory bullet.** After the `review/cycle-N-paper.md` bullet (the one ending "Keep every cycle's snapshot alongside its report."), add:

```markdown
- `journey/transcript.md` is the human<->assistant dialogue behind the study (the owner's questions,
  direction, and the substantive corrections) — committed as provenance so it is clear what was the
  owner's vs. the AI's heavy lifting. It is **not** part of `paper.md` and carries no privacy gate
  (it is the owner's own dialogue). `blog/` holds the optional owner-voice write-up produced by the
  `research-blog` skill. Omit either folder when empty.
```

- [ ] **Step 3: Structural check**

Run: `grep -E 'journey/|blog/' plugins/madskillz/skills/scientific-study/references/repo-layout.md | wc -l`
Expected: `≥3`

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/references/repo-layout.md
git commit -m "feat(study): add journey/ transcript + blog/ to the repo layout

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `scientific-study` handoff + transcript refinement

**Files:**
- Modify: `plugins/madskillz/skills/scientific-study/SKILL.md`

**Interfaces:**
- Consumes: the `research-blog` skill name (Task 3); `journey/transcript.md` (Task 5 layout).

- [ ] **Step 1: Add an optional Step 7 (blog write-up).** After the Step 6 block (ends "Never merge — the human does.") and before `## Edge cases`, insert:

```markdown
## Step 7 — Optional: blog the journey

If the user wants a shareable write-up, hand off to the **`research-blog`** skill: it saves the
human<->assistant dialogue to `journey/transcript.md` (provenance, not part of the paper) and drafts
a first-person blog post in the owner's voice under `blog/`. This step is optional and never gates
publishing. The study may also **read** `journey/transcript.md` for refinement context — what the
human actually asked for — when revising. The transcript is the owner's own dialogue: committed as
provenance, never privacy-gated, never part of `paper.md`.
```

- [ ] **Step 2: Add the edge case.** In `## Edge cases`, after the "Asked to just review …" bullet, add:

```markdown
- Asked to blog the study / share the journey → hand off to `research-blog` (Step 7); it also saves
  the dialogue transcript as study provenance.
```

- [ ] **Step 3: Structural check**

Run: `grep -c 'research-blog' plugins/madskillz/skills/scientific-study/SKILL.md`
Expected: `≥2` (Step 7 + edge case)

- [ ] **Step 4: Commit**

```bash
git add plugins/madskillz/skills/scientific-study/SKILL.md
git commit -m "feat(study): optional Step 7 blog handoff + transcript refinement read

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Plugin version bump + family-wide validation

**Files:**
- Modify: `plugins/madskillz/.claude-plugin/plugin.json`

- [ ] **Step 1: Bump the version (new skill = minor).** Replace `"version": "0.7.0",` with `"version": "0.8.0",`.

- [ ] **Step 2: Validate the whole family resolves.** Run:

```bash
cd plugins/madskillz
# every referenced reference file exists
grep -rhoE 'references/[A-Za-z0-9/_-]+\.md' skills/research-blog | sort -u | while read r; do
  test -f "skills/research-blog/$r" && echo "ok  $r" || echo "MISSING $r"
done
# skill is discoverable + evals valid
test -f skills/research-blog/SKILL.md && echo "SKILL.md ok"
python3 -c "import json;json.load(open('skills/research-blog/evals/evals.json'))" && echo "evals ok"
python3 -c "import json;print('plugin', json.load(open('.claude-plugin/plugin.json'))['version'])"
```
Expected: all `ok`, no `MISSING`, `evals ok`, `plugin 0.8.0`.

- [ ] **Step 3: Commit**

```bash
git add plugins/madskillz/.claude-plugin/plugin.json
git commit -m "chore(madskillz): bump to 0.8.0 for research-blog skill

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (completed against the spec)

**Spec coverage:** §3 file layout → Tasks 1–3 (create) + Tasks 4–6 (modify) + Task 7 (register); §4 steps → SKILL.md Task 3; §4 backfill → SKILL.md "Retroactive / backfill mode" + eval `backfill-existing-study`; §5 voice → Task 1; §6 shapes → Task 2; §7 transcript storage (committed, not in paper, no gate) → SKILL Step 1 + Task 5 layout + Task 6 study note; §8 integration (route, handoff, refinement, layout) → Tasks 4/5/6; §9 integrity → SKILL integrity stance + RED/GREEN in Task 3; §11 testing → evals (Task 3) + RED/GREEN baseline. No gaps found.

**Placeholder scan:** the only `<...>` tokens are intentional template fields inside file *content* (e.g. `<slug>`, `<YYYY-MM-DD>`), not plan placeholders. No "TBD/TODO/handle edge cases".

**Type consistency:** filenames are consistent across tasks — `journey/transcript.md`, `blog/blog-notes.md`, `blog/post-<slug>.md`, skill name `research-blog`, references `blog-voice.md` / `blog-format.md`.

## Execution Handoff

(Filled at hand-off time — see the message accompanying this plan.)
