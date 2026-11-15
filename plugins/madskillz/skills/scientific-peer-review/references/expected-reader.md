# The expected reader (reading-level standard)

The single source of truth for **who the research family writes for** and **how plainly**. The
writer (`scientific-study`), the readability-tier reviewers, and `ask-an-expert`'s direct answers
all calibrate to this file, so the prose and the bar that judges it never drift apart.

## House default — a ~9th-grade general reader

Write so a motivated **general reader at about a 9th-grade reading level** (age ~14–15, no
specialist background) can follow **what was asked, what was done, what was found, and why it
matters** — from the paper alone. The 9th-grade bar covers word choice, grammar and concepts.

This **never trades correctness for plainness.** Where a plain word would lose real meaning, keep
the precise term and **define it on first use; never delete it.** Plainness is about *framing* a
hard idea so it lands, not about removing it.

## What this changes versus writing for a peer

Do **not** assume general scientific literacy. Concepts a working scientist knows cold —
**p-value, confidence interval, control group, statistical significance, regression, effect
size**, and the like — are themselves **defined in plain language on first use** and carried in the
**Glossary**. The 9th-grade reader has not met them; "standard scientific concepts" are not
exempt.

Craft rules:

- **Short sentences; one idea each.** Prefer common words over rare ones; active voice.
- **Define before you lean on it.** Every acronym is spelled out on first use; every symbol is
  named in words.
- **The abstract is the true plain-language summary.** A reader at this level gets the whole story
  from the abstract alone — there is no separate lay summary.
- **Ground abstractions in the concrete.** Use a short everyday example or analogy for each
  genuinely abstract idea, then connect it back to the precise term.

## Numbers in the text

A 9th-grade reader cannot read ".31 (−.07 to .69)" as "too few people to tell." So the prose says
what a result **means**, and the figures and tables carry the statistics.

- **In the text:** the finding in plain words ("a small lift," "about a third," "too few people to
  tell," "ruled out more than a small difference"), plus at most one plain number when that number
  is the point ("5.6% started on their own," "about a third").
- **In figures and tables:** confidence intervals, test statistics, β weights, p-values, exact
  effect sizes and sample counts. Each prose finding points at the figure or table that holds its
  numbers.
- **Let the number speak once.** When a figure shows that an interval crosses zero, the text says
  "too few people to tell" once; it does not also hedge the sentence around it.

## Hedging

Accuracy comes from the right claim at the right strength, not from qualifiers. The rules:

- **One qualifier per claim**, and only when the reader would otherwise believe something false.
- **Caveats live once**, in Methods or Limits, and are referenced, not repeated in every sentence.
- **Understating misleads as much as overstating.** A replicated link written as doubtful, or a
  small test's null written as "doesn't work," is an error, not caution.

Reviewers judge this with the binding test in `binding-findings.md`. The owner's AI-tells, phrases that read as machine-written whatever the register (announced honesty, unearned importance, catchy formulations, em-dashes), are in `plugins/madskillz/writing/anti-ai-tells.md`; the writer reads that file before drafting.

## Override — a deliberately specialist audience

A study written **on purpose** for a specialist audience may calibrate up — but only when it
**says so explicitly in its framing**, using the same honest-context discipline that marks a
replication/validation study. When the manuscript declares a specialist intended audience, the
writer **and** the reviewers calibrate to that declared audience instead of the default.

Absent an explicit declaration, **the 9th-grade default applies.** The override **raises the
assumed-knowledge bar only — it never lowers the correctness or integrity bar**, and the
Acronyms/Glossary machinery still applies in full.

## Defer to correctness (unchanged)

A readability suggestion must never reduce precision or override a correctness finding. When
plainness and precision conflict, reframe as "**define the term**," and surface the disagreement to
the meta-editor rather than overriding a correctness reviewer. Moving a statistic from the prose to
a figure or table does not reduce precision.

---

_Maintainer note: this file is the single source of truth, but the other surfaces (the
`scientific-study` writer, the readability rubrics, `ask-an-expert`, and the `research` command)
restate the "~9th-grade" band inline for locality. If the band is ever re-tuned, update them
together — `grep -rn "9th-grade" plugins/madskillz` finds them — so this file stays canonical._
