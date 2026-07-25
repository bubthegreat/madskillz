# Short-form condensation contract

After the full paper clears the quality gate (Step 3) and renders (Step 5), produce a condensed
`paper-short.md` **in addition to** the full paper — never replacing it. Audience: **specialist**
(a domain reader who knows the field's terms).

## What the short form is

A compression of the gated `paper.md`, not new work. It performs **no new analysis** and uses
**no number** that is not already in `paper.md` / the study's `data/` files. If a needed number is
not there, leave `[[NEEDS-DATA: …]]` rather than invent it.

## Keep / drop

**Keep:** the title (suffix "(short form)") + a one-line byline; a **1-paragraph abstract**; a
compressed Introduction (the question + the paper's arc in 2–4 sentences); a compressed Methods
(strip inline plain-language asides such as "*stratified* means…"); Results that **lean on the
existing figures** and the 1–2 most load-bearing tables instead of restating every number in prose;
a tightened Discussion; **Limitations compressed to one dense paragraph**; the References list.

**Drop:** the Glossary, the Acronyms index, Background / further reading, and inline term
definitions (the specialist reader does not need them).

**Reuse figures.** Reference the same `assets/*.png` the full paper already built — do not
regenerate them.

## Preserve every caveat

Compression is where caveats get dropped and overclaims sneak back. Every hedge the full paper
earned — within-noise / directional-only results, confounds, single-source limits, disclosed
residuals — MUST survive in compressed form. The short form must be **neither more nor less honest**
than the paper it summarizes.

It also must not acquire revision history the full paper does not carry. A short form is authored
*after* the gate closes, from an already-revised paper, so the drafting sequence is freshest exactly
when it is written — and "an earlier draft asserted…" is the phrase that shows up. A draft is not a
publication; see the claim-discipline rule in `SKILL.md`. Compress what the paper now claims, not how
it got there.

## Re-gate (required)

Invoke `scientific-peer-review`'s **claims-ledger** and **adversarial** reviewers on
`paper-short.md` (with the `data/` files), framed as a **compression check against the full paper**:
did shortening drop a caveat, reintroduce an overclaim, or mislabel a metric? Also confirm every
number in the short form appears in `paper.md`/`data/` (numbers-trace check). Apply blocker/major
fixes; disclose any residual in the PR. If a finding traces to the full paper too, fix it in **both**.

## Render

Render two-column per `references/render.md`:

    uv run <skill>/scripts/render-paper.py <topic>/<research-short-name> --short

Target **≤5 pages excluding references** (typically ~2–3). Commit `paper-short.md` and
`build/<slug>-short.pdf`; note the short form in the PR description and README. Best-effort: if
`pandoc`/`typst` are unavailable, keep `paper-short.md` and skip the PDF with a recorded note —
never fake a build.
