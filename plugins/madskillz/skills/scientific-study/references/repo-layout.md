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
  journey/            # human<->assistant dialogue transcript — provenance; NOT part of paper.md
  blog/               # optional owner-voice write-up: blog-notes.md + post-<slug>.md; not the paper
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
  (it is the owner's own dialogue). `blog/` holds the optional owner-voice write-up produced by the
  `research-blog` skill. Omit either folder when empty.
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
