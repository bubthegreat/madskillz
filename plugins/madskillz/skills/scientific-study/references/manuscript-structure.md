# Manuscript structure — the four-document contract

The manuscript is **four documents, not one**. This is modelled on Nature's article contract, whose
central idea is a **hard main-text budget with unlimited separate methods and supplementary
material**. Nothing is deleted by this structure; everything is *relocated* and still ships.

Why this exists: without a budget, an agentic study grows a new thematic section every time review
applies pressure, and pressure lands on whichever section is most quantitative. The result is a
40-page paper in which the questions the brief actually asked are the shortest sections. The budget
is the forcing function — when the main text is capped, the space has to be spent on the answer.

## The four documents

| File | Cap | Contains |
|---|---|---|
| `paper.md` | **4,300 words**, ≤4 display items, ≤50 references | The findings. Summary paragraph, Introduction, Results, Discussion, availability statements |
| `methods.md` | **3,000 words**, **no figures, no tables** | Everything needed to interpret and replicate |
| `extended-data.md` | **≤10 display items** | Figures and tables that support the paper but are not among its ≤4 |
| `supplementary.md` | uncapped prose and tables | Detail of interest to specialists only |

Word counts cover **body text only** — the title, author line, acknowledgements, availability
statements and references are excluded, matching Nature's convention.

`scripts/check-budgets.py` enforces every number above as a **build gate**. It is not a reviewer's
job to count words, references or figures; a script does that perfectly and reviewers should spend
their attention on whether the claims are true.

## `paper.md` — structure

```
# Title

## Summary
## 1. Introduction
## 2. Results               (subsections allowed; see naming rule below)
## 3. Discussion
## Data availability
## Code availability
## References
```

**`paper.md` ends at References.** Nothing follows the reference list. The reader-facing
back-matter — the **Acronyms** index, the **Glossary**, and any **Background / further reading** —
lives at the **end of `extended-data.md`** (see below). Keeping it out of `paper.md` is what makes
the paper short enough to read in one sitting, which is the whole point of the budget.

**Summary paragraph — ≤200 words.** Per Nature: *"a fully referenced summary paragraph, ideally of
no more than 200 words … aimed at readers outside the field"*, and it **avoids numbers,
abbreviations, acronyms and measurements unless essential**. That constraint is the point: a summary
that cannot lean on notation has to state what was found in words.

**Section naming — structural, never thematic.** `## 2. Results` with subheads like `### 2.1 What
the headline statistics count`. **Not** `## 3. The headline statistics are not measuring the same
object`. A section title that states a thesis is an argument wearing a heading, and it is how a
paper regrows: every finding gets promoted to a top-level section until there are seventeen of them.
Nature caps subheadings at 40 characters, which makes a thesis-as-heading impossible; adopt the same
cap.

**Display items — ≤4.** Tighter than Nature's 5–6, by house preference. Everything else goes to
Extended Data. A "display item" is a figure or a table. Figure legends are **<300 words** and, since
a Methods document exists, **carry no methods detail**.

**References — ≤50 in `paper.md`.** There is no cap on references appearing only in `methods.md`,
`extended-data.md` or `supplementary.md`. Numbering is **sequential across all four documents in
reading order**: main text → figure legends → Methods → Extended Data legends → Supplementary.
Maintain one master list at the end of `paper.md`.

> **Generate the numbering; never hand-maintain it.** A four-document manuscript with a shared
> sequential reference list is exactly the artifact where hand-maintained numbering drifts, and
> drift here is a citation-integrity defect, not a formatting nit.

**Minimal citations — the paper's list carries only what the paper cites.** Each point in the
paper cites the single best source that proves or disproves it. A point carries more than one
citation only when the text states the reason, in the sentence itself. So the reference list at
the end of `paper.md` holds **only sources actually cited in `paper.md`** — nothing is listed
there for completeness.

Every other source in the store is **displaced, not dropped**. Displaced sources get **numbered
continuations of the same sequence** in the supplementary documents, each with **a one-line reason
it carries no claim in the paper** — superseded by a better source, agrees with a source already
cited, background only, could not be verified, and so on. The numbering runs on from the paper's
last reference, so a reference number means one source across the whole manuscript. Close the
paper's list with one line pointing at the continuation, for example: *"Every other source in the
store is listed in Supplementary S1, with the reason it carries no claim in this paper."*

This is what keeps the ≤50 cap honest. A paper that stacks four agreeing citations on one sentence
is not better supported than one that cites the best of the four; it has only hidden which source
the claim rests on.

## `methods.md` — structure

```
## Source selection
## Extraction protocol
## Verification vocabulary
## Normalization and coding
## Analysis procedures
## Deviations from the analysis plan
```

Nature: *"written as concisely as possible but should contain all elements necessary to allow
interpretation and replication of the results,"* typically **≤3,000 words**.

**⚠️ Methods cannot contain figures or tables.** This is a real Nature rule and it is the one most
studies violate, because method sections are naturally table-shaped — coding vocabularies, tier
definitions, inclusion rules. Those tables become **Extended Data items**, and Methods *references*
them (`Extended Data Table 1`). Plan for this: a table-heavy method is a rewrite, not a move.

**Deviations from the analysis plan** is mandatory and may not be omitted. If the analysis was
pre-specified and followed, the section says exactly that in one line. If a decision rule was chosen
*after* seeing a result — a different effect-size statistic, a different grouping, a changed
threshold — it is named here with the order of events. A study that cannot fill this section
honestly has an integrity problem, not a formatting problem.

## `extended-data.md` — structure

Up to **10 display items**, each formatted as it would be in print: a numbered title and a legend.

```
### Extended Data Fig. 1 | <title>
<legend>

### Extended Data Table 1 | <title>
<table>
```

Per Nature, Extended Data is for material that *"provides essential background … but is not included
in the printed version due to space constraints or being of interest only to a few specialists."*
Every item must be cited from `paper.md` or `methods.md`. An uncited Extended Data item is either
unnecessary or a symptom that the main text is missing something.

### Reader back-matter — at the end of `extended-data.md`

`extended-data.md` **ends** with the reader-facing back-matter, after the last display item:

```
## Acronyms                        (every acronym used in any document, expanded)
## Glossary                        (every specialized term, defined for the expected reader)
## Background / further reading    (optional; verified sources or clearly-marked suggestions)
```

**These do not count against the 10-display-item cap.** They are reference apparatus for the
reader, not evidence, even when the Acronyms index is shaped like a table. `check-budgets.py`
counts only headings of the form `Extended Data Fig. N` / `Extended Data Table N`, so back-matter
tables are already outside the count.

Why they sit here and not in `paper.md`: a reader looking up a term is no longer reading the
paper, and the paper is meant to be readable straight through. Everything the term-lookup reader
needs is in one place, next to the detail they will look up next. The in-line gloss at first use
(see `scientific-peer-review/references/expected-reader.md`) is what serves the straight-through
reader, so the Glossary is the second copy, not the first.

## `supplementary.md`

Uncapped. Long-form limitations, per-row provenance notes, full source inventories, sensitivity
tables that do not earn an Extended Data slot.

**Do not put datasets here.** Nature: *"providing large datasets in supplementary information is
strongly discouraged and the preferred approach is to make data available in repositories."* Data
lives in `data/`, and the Data availability statement points at it.

## Availability statements — both mandatory

They sit at the end of `paper.md`, **Data first, then Code, then References**.

**Data availability** must make the conditions of access to the *minimum dataset necessary to
interpret, verify and extend* the work transparent. For a study that redistributes nothing and cites
only published figures, that statement is short and unusually clean — say so plainly rather than
using boilerplate.

**Code availability** states whether and how the code can be accessed, and any restrictions.
Best practice is a **DOI-minting repository** (Zenodo, Code Ocean) plus a release tag, so a reader
can obtain the exact code that produced the results. Shipping `scripts/` in the repo with no tag is
weaker; if that is what was done, say so rather than implying more.

## What this replaces

This structure **retires the condensed short form** (`paper-short.md`). It existed because papers
were 30–40 pages and needed a reader-facing digest. A 4,300-word paper with a 200-word summary
paragraph *is* the digest. Producing a short form of an already-short paper adds a second document
to keep in sync and, in practice, a fresh compression pass reacquires overclaims the full paper had
been forced to drop.

## Checklist before the review loop

- [ ] `paper.md` body ≤4,300 words
- [ ] Summary ≤200 words, no acronyms or measurements unless essential
- [ ] ≤4 display items in `paper.md`; every figure legend <300 words and free of methods detail
- [ ] ≤50 references cited in `paper.md`, and the list holds **only** sources cited in `paper.md`
- [ ] Every point cites one source, or states in the text why it cites more than one
- [ ] Displaced sources are numbered on from the paper's list in the supplementary documents, each
      with a one-line reason
- [ ] `paper.md` ends at References — no Acronyms, Glossary or Background section after it
- [ ] `extended-data.md` ends with Acronyms, Glossary, and optional Background / further reading
- [ ] No section heading states a thesis; no subheading over 40 characters
- [ ] `methods.md` ≤3,000 words and contains **no** figures or tables
- [ ] `methods.md` has a *Deviations from the analysis plan* section, filled honestly
- [ ] ≤10 Extended Data items, each cited from `paper.md` or `methods.md`
- [ ] No dataset pasted into `supplementary.md`
- [ ] Data availability and Code availability statements present, in that order, before References
- [ ] `uv run <skill>/scripts/check-budgets.py <study_dir>` exits 0
