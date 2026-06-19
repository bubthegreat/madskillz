---
name: scientific-archive
description: >-
  Archive a completed or reviewed research item — the paper plus its pertinent
  data, scripts, and assets — to the private jmresearch/research repo under a
  stable <topic>/<research-short-name>/ layout, but only after a compliance gate
  clears dataset licensing and privacy. Use whenever the user wants to archive,
  publish, save, or push a study/paper/dataset to the research repo, preserve
  research for reproduction, or hand reviewed work off for safekeeping. Trigger
  on phrases like "archive this research," "push the paper to the research repo,"
  "save this study to jmresearch," "publish this to the research repo," or "store
  the data and scripts for this paper." The final step of the scientific-* family
  and the hand-off target of scientific-peer-review.
---

# scientific-archive: compliance-gated research archival

Push one research item — the paper plus its pertinent data, scripts, and assets —
to the private **`jmresearch/research`** repository under a stable
`<topic>/<research-short-name>/` layout, so it is durably preserved and
reproduction-ready for peer review. A pre-flight compliance gate runs first: data
we have no right to redistribute, or that carries privacy obligations, is never
silently pushed.

This is the archival/publishing step of the `scientific-*` family. It is distinct
from environment capture (`scientific-repro`, future). It never writes or revises
the paper, and never runs the review — it archives whatever artifacts exist plus,
when run after a review, the review report.

## Integrity stance (non-negotiable)

1. Archive only artifacts that actually exist. A missing category is reported,
   never faked.
2. Never fabricate a compliance verdict. "License unverified" / "privacy
   unverified" is reported as such — never asserted as "cleared."
3. Never claim a push that did not happen. Report the real result (commit SHA +
   pushed path) or the real failure.
4. The deliverable states its own coverage: what was pushed, what was referenced
   instead of redistributed (and why), what was omitted, and any overrides.
5. Compliance and privacy outrank convenience and completeness in every conflict.

## Step 0 — Compliance gate (runs first, can block)

Read `references/compliance-gate.md` and apply it to every dataset and third-party
asset/code in the item. Resolve each to one of:

- **include** — license/terms permit redistribution (even to a private repo);
- **reference-only** — not redistributable / unclear / DUA / click-through /
  non-commercial / no-derivatives → archive a data *reference* (citation, access
  URL, version, content hash, retrieval steps), not the raw data;
- **blocked** — PII/PHI present, or human-subjects consent/approval basis missing
  → the user must de-identify, supply a compliant reference, or record an explicit
  attestation.

**Fail-closed:** if licensing or privacy status is unknown or unverifiable, the
affected data is **not** pushed without an explicit, recorded user override.

When archiving right after a peer review, pull the `ethics-integrity` reviewer's
flags into this gate rather than re-deriving them.

## Step 1 — Collect artifacts

Gather what actually exists for this one item: the **paper** (markdown, required —
ask for it if absent), `assets/`, `data/`, `scripts/`, and — when run after a
review — the peer-review report(s). Note what is present and what is missing.

## Step 2 — Name the folder

Propose a `<topic>` and a slugified `<research-short-name>` derived from the
paper's title/subject, then **ask the user to confirm or override**. Both are
kebab-case slugs — validate (lowercase, hyphens, no spaces or path characters)
before any filesystem write.

## Step 3 — License & attributions

Default **CC BY 4.0** for paper/data/assets and **MIT** for code; confirm or let
the user override. Fold the Step 0 findings (sources, licenses, what reproduction
requires, reference-only datasets) into `ATTRIBUTIONS.md`.

## Step 4 — Resolve the repo

Read `references/git-workflow.md`. Verify `gh` is installed, authenticated, and
has push access to `jmresearch/research`. Clone it to the cache dir, or
`git pull --ff-only` an existing checkout. If `gh` is missing/unauthed, stop with
guidance (suggest running `gh auth login` via the `!` prefix) — do not fake a push.

## Step 5 — Lay out the folder

Build `<topic>/<research-short-name>/` per `references/repo-layout.md`: `paper.md`,
`assets/`, `data/` (real data, reference stubs, or a mix per Step 0), `scripts/`
(with its MIT `LICENSE`), `review/` (when post-review), top-level CC BY 4.0
`LICENSE`, `ATTRIBUTIONS.md`, `COMPLIANCE.md`, and `README.md`. If the folder
already exists, this is an **update** — list changed files and confirm overwrites.

## Step 6 — Pre-push summary & confirm

Show the file manifest, the target path, the compliance outcomes (cleared /
reference-only / overrides), and the commit message. **Get confirmation before
pushing** — pushing to a shared private repo's default branch is outward-facing,
and this is the user's last chance to catch anything sensitive.

## Step 7 — Commit & push, then report

Commit and push straight to the default branch (per `references/git-workflow.md`).
Report the commit SHA, the pushed path, and exactly what was **included** vs.
**referenced** vs. **omitted**, plus any recorded overrides. If the push fails
(no access, offline, rejected), report it honestly and offer to leave a local
commit for the user to push later.

## Edge cases

- No paper → ask for it; archive needs at least the manuscript.
- `gh` missing/unauthed → stop with `gh auth login` guidance; never fake a push.
- Push rejected / no access / offline → report honestly; offer a local commit.
- Folder already exists → update mode; list changes; confirm overwrites.
- Missing artifact categories → archive what exists; note gaps; never fabricate.
- Dataset license forbids redistribution → reference-only stub, not raw data.
- PII/PHI present or consent basis missing → block; de-identify / reference / attest.
- Licensing or privacy status unknown → fail-closed; not pushed without recorded override.
- Asked to also write/revise the paper or run the review → out of scope; point to
  the author / `scientific-writeup` / `scientific-peer-review`.
