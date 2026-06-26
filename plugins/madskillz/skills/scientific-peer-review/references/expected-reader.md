# The expected reader (reading-level standard)

The single source of truth for **who the research family writes for** and **how plainly**. The
writer (`scientific-study`), the readability-tier reviewers, and `ask-an-expert`'s direct answers
all calibrate to this file, so the prose and the bar that judges it never drift apart.

## House default — a ~10th-grade general reader

Write so a motivated **general reader at about a 10th-grade reading level** (age ~15–16, no
specialist background) can follow **what was asked, what was done, what was found, and why it
matters** — from the paper alone.

This **never trades correctness for plainness.** Where a plain word would lose real meaning, keep
the precise term and **define it on first use; never delete it.** Plainness is about *framing* a
hard idea so it lands, not about removing it.

## What this changes versus writing for a peer

Do **not** assume general scientific literacy. Concepts a working scientist knows cold —
**p-value, confidence interval, control group, statistical significance, regression, effect
size**, and the like — are themselves **defined in plain language on first use** and carried in the
**Glossary**. The 10th-grade reader has not met them; "standard scientific concepts" are not
exempt.

Craft rules:

- **Short sentences; one idea each.** Prefer common words over rare ones; active voice.
- **Define before you lean on it.** Every acronym is spelled out on first use; every symbol is
  named in words.
- **The abstract is the true plain-language summary.** A reader at this level gets the whole story
  from the abstract alone — there is no separate lay summary.
- **Ground abstractions in the concrete.** Use a short everyday example or analogy for each
  genuinely abstract idea, then connect it back to the precise term.

## Override — a deliberately specialist audience

A study written **on purpose** for a specialist audience may calibrate up — but only when it
**says so explicitly in its framing**, using the same honest-context discipline that marks a
replication/validation study. When the manuscript declares a specialist intended audience, the
writer **and** the reviewers calibrate to that declared audience instead of the default.

Absent an explicit declaration, **the 10th-grade default applies.** The override **raises the
assumed-knowledge bar only — it never lowers the correctness or integrity bar**, and the
Acronyms/Glossary machinery still applies in full.

## Defer to correctness (unchanged)

A readability suggestion must never reduce precision or override a correctness finding. When
plainness and precision conflict, reframe as "**define the term**," and surface the disagreement to
the meta-editor rather than overriding a correctness reviewer.

---

_Maintainer note: this file is the single source of truth, but the other surfaces (the
`scientific-study` writer, the readability rubrics, `ask-an-expert`, and the `research` command)
restate the "~10th-grade" band inline for locality. If the band is ever re-tuned, update them
together — `grep -rn "10th-grade" plugins/madskillz` finds them — so this file stays canonical._
