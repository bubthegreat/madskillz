# Scientific-study: always-on condensed short-form summary — design

**Date:** 2026-07-12 · **Skill:** `scientific-study` (madskillz) · **Status:** approved, pre-plan

## Context

Every `scientific-study` run publishes a full paper written for a ~10th-grade general reader,
which runs long (the reference study reached 17 rendered pages). The owner wants, *in addition to*
the full paper, a short condensed version for fast reading and on-device (reMarkable) QA — proven
out by hand this session for the `stacked-fanin-pipeline-diversity` radiology study: a two-column,
~2–3-page specialist condensation (`paper-short.md` → `build/<slug>-short.pdf`).

The load-bearing lesson from building that exemplar: **compression is where caveats get dropped and
overclaims sneak back in.** The hand-built short form passed only after a re-gate caught a
compression-introduced error (a plain-accuracy figure mislabeled "balanced accuracy"). So the
short form is not a formatting pass — it is an editorial compression that must be re-gated for
honesty every time.

## Goal

Add an **always-on** step to `scientific-study` that, after the full paper clears the peer-review
quality gate and renders, produces a re-gated specialist short-form PDF **alongside** (never
replacing) the full paper, and ships it in the PR.

## Decisions (locked)

- **Always-on, additive.** Runs every study; the full paper is untouched.
- **Audience: specialist.** Drops the general-reader scaffolding; assumes the field's terms.
- **Re-gate: claims-ledger + adversarial** (both), plus an automatic numbers-trace check.
- **Best-effort render, fail-closed honesty:** never fake a build; if it cannot render, publish
  without it and say so — same discipline as the existing render step.

## Design

### New Step 5b — "Condensed short form" (after Step 5 render, before Step 6 PR)

Operates on the **already-gated** `paper.md` (post-Step-3 loop, post-Step-5 render). Sequence:

1. **Author `paper-short.md`** — a specialist condensation of `paper.md`:
   - **Keep:** title (suffixed "(short form)") + one-line byline; a 1-paragraph abstract; a
     compressed Introduction (question + the paper's arc/structure in 2–4 sentences); a compressed
     Methods (strip inline plain-language asides — "*stratified* means…"); Results that **lean on
     the existing figures** and the 1–2 most load-bearing tables rather than restating every
     number in prose; a tightened Discussion; Limitations compressed to one dense paragraph; the
     References list.
   - **Drop:** Glossary, Acronyms index, Background / further reading, and inline term definitions
     (specialist reader).
   - **Reuse, don't regenerate, figures.** Reference the same `assets/*.png` the full paper built.
   - **Hard constraint:** every number must already appear in `paper.md` / the study's `data/`
     files. The short form performs **no new analysis** and introduces **no number** not in the
     full paper. Leave `[[NEEDS-DATA]]` rather than invent — same rule as the drafting step.
   - Preserve **every** caveat in compressed form: the hedges the full paper earned (within-noise,
     confounds, single-source, disclosed residuals) must survive compression.

2. **Re-gate the short form for compression drift.** Invoke `scientific-peer-review`'s
   **claims-ledger** and **adversarial** reviewers on `paper-short.md` (with the `data/` files),
   framed explicitly as a *compression check against the full paper*: did shortening drop a caveat,
   reintroduce an overclaim, or mislabel a metric? Also run the automatic numbers-trace check
   (every figure in the short form appears in `paper.md`/`data/`). Apply blocker/major fixes;
   disclose any residual in the PR. (Only 2 reviewers — deliberately cheap.)

3. **Render two-column.** Produce `build/<slug>-short.pdf` via the short-form renderer
   (`references/render.md` / `scripts/render-paper.py`): pandoc → Typst with `columns=2`,
   `fontsize=10pt`, ~`1.6cm`/`1.7cm` margins, **no** table of contents. Target **≤5 pages
   excluding references** (typically ~2–3). No EPUB for the short form (the full paper carries the
   reflowable copy). Best-effort: if `pandoc`/`typst` are unavailable, skip with a recorded note —
   never fake.

4. **Commit** `paper-short.md` + `build/<slug>-short.pdf` and note the short form in the PR
   description and README. It ships **in addition to** the full paper and its PDF/EPUB.

### Renderer change (`scripts/render-paper.py`)

Add a short-form render path that takes `paper-short.md` and emits a two-column PDF with the params
above. Capture the layout config in code (`margin{x,y}`, `fontsize`, `columns`) so it is
reproducible, not an ad-hoc CLI invocation. The existing full-paper render (single-column PDF +
EPUB, with TOC) is unchanged. Both are driven from the same script.

**Render gotcha (verified this session):** pandoc's Typst template rejects an inline
`-V margin='{"x":…,"y":…}'` map (fails with `margin: (: ,)`). Pass the nested `margin` map — and
`fontsize`/`columns` — via a written **metadata file** (`--metadata-file`), not inline `-V`. The
short render also omits `--toc` and `--number-sections` is optional. Working invocation from the
exemplar: `pandoc paper-short.md --from gfm --pdf-engine=typst --metadata-file=<meta.yaml> -o
build/<slug>-short.pdf`, with `meta.yaml` = `{margin:{x:1.6cm,y:1.7cm}, fontsize:10pt, columns:2}`.

### `references/short-form.md` (new)

The condensation contract the drafting step follows: audience (specialist), the keep/drop list
above, the "no new number" rule, the "preserve every caveat" rule, the re-gate (claims-ledger +
adversarial as a compression check), the render params, and the ≤5-page target. Kept as a
reference file (loaded only at Step 5b) so it does not bloat always-on context.

## Edge cases

- **Full paper failed to clear the gate (published with residual blockers).** Still produce the
  short form; it inherits and discloses the same residuals — it must not present a cleaner story
  than the full paper.
- **`pandoc`/`typst` missing.** Skip the short PDF with a recorded note; keep `paper-short.md`
  (renderable later). Never fake.
- **Short form re-gate finds a blocker/major that traces to the full paper too** (not a
  compression artifact). Fix it in **both** and note it — the short form must not be more honest
  than the paper it summarizes, nor less.
- **Human-review follow-ups (Step 7).** When a follow-up materially changes the paper's claims or
  numbers, regenerate the short form (re-gate + re-render) so the two do not drift.
- **Study deliberately specialist-audience (Step 1 override).** Short form still drops the
  back-matter scaffolding; the prose is already specialist, so condensation is lighter.

## Verification

- Run `scientific-study` (or the Step 5b path) on the existing `stacked-fanin-pipeline-diversity`
  study: confirm it produces `paper-short.md` + `build/<slug>-short.pdf`, ≤5 pages excl.
  references, with the claims-ledger + adversarial re-gate reports saved and every number tracing
  to the data files. (The hand-built exemplar is the expected-output oracle.)
- Eval in `evals/evals.json` locks: a study run produces a **re-gated specialist short-form PDF
  alongside** the full paper (not replacing it), with no number absent from the full paper/data.

## Files

- `plugins/madskillz/skills/scientific-study/SKILL.md` — new Step 5b + edge cases
- `plugins/madskillz/skills/scientific-study/references/short-form.md` — **new**, condensation contract
- `plugins/madskillz/skills/scientific-study/references/render.md` — two-column short-render params
- `plugins/madskillz/skills/scientific-study/scripts/render-paper.py` — short-form render path
- `plugins/madskillz/skills/scientific-study/evals/evals.json` — short-form eval
- `plugins/madskillz/.claude-plugin/plugin.json` — version bump
