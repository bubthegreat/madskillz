# Repo layout & file templates

One study occupies one folder in `jmresearch/research`, built up on a study branch
and opened as a PR (see `git-workflow.md`):

```
<topic>/<research-short-name>/
  paper.md            # manuscript in markdown — evolves across the review-cycle commits
  assets/             # figures, plots, diagrams referenced by the paper
  data/               # datasets / results tables — real data, *.reference.md stubs, or a mix
  scripts/            # analysis code / reproducibility scripts / notebooks
    LICENSE           # MIT — covers code (from licenses/MIT.txt)
  review/             # per cycle: the report (cycle-N.md) + the reviewed paper snapshot (cycle-N-paper.md)
  build/              # rendered manuscript: <slug>.pdf (Typst) + <slug>.epub — see references/render.md
  journey/            # human<->assistant dialogue transcript — provenance; NOT part of paper.md
  LICENSE             # CC BY 4.0 — covers paper, data, assets (from licenses/CC-BY-4.0.txt)
  ATTRIBUTIONS.md     # third-party sources, their licenses, what reproduction requires
  COMPLIANCE.md       # gate outcome: cleared / referenced-only / consent basis / overrides
  README.md           # title, type, date, topic + slug, license summary, reproduction notes
```

- `<topic>` and `<research-short-name>` are kebab-case slugs (lowercase, hyphens,
  no spaces or path characters). Validate before writing.
- `review/cycle-N.md` is the adjudicated plan from cycle N; keep every cycle so the PR
  shows what was raised and how the paper changed. Residual/unresolved findings also
  go in the **PR description** (see `git-workflow.md`).
- `review/cycle-N-paper.md` is the exact `paper.md` that cycle N reviewed, so a reader
  can diff the iterations — cycle to cycle, and against the final `paper.md` — without
  git. Keep every cycle's snapshot alongside its report.
- `journey/transcript.md` is the human<->assistant dialogue behind the study (the owner's questions,
  direction, and the substantive corrections) — committed as provenance so it is clear what was the
  owner's vs. the AI's heavy lifting. It is **not** part of `paper.md` and carries no privacy gate
  (it is the owner's own dialogue). Omit it when empty.
- Omit a subfolder that has no content. Never create an empty placeholder to imply
  coverage that does not exist.
- License files are copied verbatim from `references/licenses/`. For `MIT.txt`,
  fill `<YEAR>` and `<COPYRIGHT HOLDER>`. CC BY 4.0 legal code is used as-is; the
  attribution/copyright line lives in `README.md` and `ATTRIBUTIONS.md`.

## paper.md structure (required back-matter)

The manuscript is written for an **adjacent-field researcher** with an **educated-generalist
floor** (general scientific literacy, not a subfield specialist). The **abstract** doubles as the
plain-language summary — a reader at that level grasps what was done and found from it alone. There
is no separate lay-summary section.

End the manuscript with this back-matter, in this order:

```markdown
## Acronyms
| Acronym | Expansion |
|---|---|
| <ABC> | <full expansion> |

## Glossary
| Term | Plain-language definition |
|---|---|
| <term> | <definition the expected reader can follow> |

## Background / further reading   <!-- optional; omit if nothing needs it -->
- <concept> — <verified source: DOI / arXiv ID / ISBN / stable URL>, OR a clearly-marked
  topic/keyword suggestion when no source can be verified. Never present an unverified reading as a
  citation.
```

- Every acronym used in the body is expanded on first use AND listed in **Acronyms**; every
  specialized term used in the body is in the **Glossary**. Both directions — no orphan entries.
- Omit **Background / further reading** if nothing needs it; never pad it to imply coverage.

## Citation, cross-reference & provenance conventions

The manuscript grounds every claim using **standard scholarly conventions** — what any journal
article shows — not bespoke inline tags. Distinguish the kinds of grounding by *form*, not by a
`[C]/[D]/[A]`-style label:

- **Cited (external prior work)** → a **numbered citation `[N]`** keyed to a numbered reference
  list (`[12]`, `[3,5–7]`). This is the **default house style**. The citation-integrity reviewer
  (the citation specialist) may switch a paper to **author–date** `(Author, Year)` when its
  field/target journal expects that system — see
  `scientific-peer-review/references/reviewers/citation-integrity.md`. Use one system
  consistently; never mix systems and never leave a bespoke tag.
- **Data-derived (computed by this study)** → state the value and point to the **Figure or
  Table** that shows it: "modelled recurrence was 23.2% (Figure 3)" / "(Table 2)". Not `[D]`.
- **Assumption (a modelling/analysis choice)** → state it in **prose**, in Methods, and where
  possible test it with a sensitivity analysis: "We assume independent effects on the log
  scale." Not `[A]`.
- **Speculation / interpretation** → **hedged prose confined to the Discussion** ("may",
  "suggests", "we speculate that …"), never in Results. Each speculation still carries its
  reasoning — why it matters, why the data can't settle it, and what would settle it (feeds
  Future Work). The discipline is kept; only the inline tag is gone.

In-text **cross-references** to the paper's own parts spell out and capitalize the element —
**"Section 4", "Section 2.3", "Figure 1", "Table 2", "Appendix A"** — not `§4` (the section
sign is venue-specific; use it only where the target venue does) and not a bare number. Do not
carry a `[C]/[D]/[A]` provenance legend in the published paper.

## README.md template

```markdown
# <Paper title>

- **Topic:** <topic>
- **Short name:** <research-short-name>
- **Type:** <novel research | replication/validation of established work>
- **Created:** <YYYY-MM-DD>
- **Status:** <in-review (PR open) | merged>

## Contents
- `paper.md` — manuscript (ends with Acronyms, Glossary, and optional Background / further reading)
- `assets/` — <one line>
- `data/` — <one line; note any reference-only datasets>
- `scripts/` — <one line>
- `review/` — per review cycle: the report (`cycle-N.md`) and the reviewed paper snapshot (`cycle-N-paper.md`)
- `build/` — rendered `<slug>.pdf` (Typst) and `<slug>.epub` of the manuscript

## Licensing
- Paper, data, and assets: **CC BY 4.0** (`LICENSE`).
- Code in `scripts/`: **MIT** (`scripts/LICENSE`).
- Third-party material and its terms: see `ATTRIBUTIONS.md`.
- © <YEAR> <author(s)>. Attribute as: <citation>.

## Reproduction
<How to reproduce: data access steps, how to run scripts, dependencies. Note any
reference-only datasets and how to obtain them. See COMPLIANCE.md for terms.>
```

## ATTRIBUTIONS.md template

```markdown
# Attributions

Third-party material used in this research and the terms under which it is
included or referenced. Required for lawful reproduction.

## Datasets
| Dataset | Source / URL | Version | License / terms | Disposition |
|---|---|---|---|---|
| <name> | <url> | <ver / hash> | <license> | included / reference-only |

## Code & libraries
| Component | Source | License | Disposition |
|---|---|---|---|
| <name> | <url> | <license> | included / reference-only |

## Assets (figures, images)
| Asset | Source | License | Disposition |
|---|---|---|---|
| <name> | <url / "original"> | <license> | included / reference-only |
```

## COMPLIANCE.md template

```markdown
# Compliance record

Generated by scientific-study's compliance gate. Documents why each input was
included, referenced, or blocked-and-resolved.

- **Gate run:** <YYYY-MM-DD>
- **Posture:** fail-closed (unknown status not published without recorded override)
- **Privacy screen:** <no PII/PHI detected | PII/PHI handled — see below>
- **Human-subjects basis:** <n/a | consent/approval ref covering archival/sharing>

## Dispositions
| Input | Class | Disposition | Basis / rationale |
|---|---|---|---|
| <name> | redistributable / restricted / unknown | include / reference-only / blocked→resolved | <terms; override author + reason if any> |

## Overrides
<None | who authorized, on what date, what was overridden, and the recorded rationale.>
```

## Reference-only data stub template (`data/<name>.reference.md`)

```markdown
# <Dataset name> — reference only

Not redistributed here due to: <license / DUA / privacy>. Obtain it as follows.

- **Source:** <url>
- **Version / release:** <ver>
- **Content hash (file used):** <sha256>
- **Retrieval steps:** <how to access, including registration/DUA if any>
- **License / terms:** <terms>
```
