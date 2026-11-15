# Review report format

Every reviewer returns this exact shape. The meta-editor consumes them and emits its own
deliverable (see `reviewers/meta-editor.md`). Never invent a verdict for a check you could not
run — report it as skipped.

**Read `binding-findings.md` first.** It decides which of your findings the writer must act on. A
finding binds only when a reasonable reader would come away believing something the evidence
contradicts, in either direction (overstating or understating). Everything else is a **note**.

## Per-reviewer report

```
Reviewer: <role>
Inputs available: <list> | Checks skipped (missing input): <list or "none">
Recommendation: accept | minor | major | reject
Findings (binding only, severity-ranked):
  - [severity: blocker|major|minor] [location: §/line/table]
    Sentence: "<quoted verbatim>"
    Reader would believe: <the specific false belief>
    Evidence says: <what contradicts it: row id, source, figure or table>
    Fix: delete <…> | correct <fact> to <fact>
Notes (non-binding; the writer may ignore them):
  - [location] <one line each>
Questions for authors: …
Reviewer notes (optional): <reviewer-specific summary — e.g. Reproducibility's
  conceptual/runnable/bit-for-bit rating, or "no human-subjects/dual-use concern">
```

Findings that are not about a sentence (a missing analysis, a broken build, an unresolvable
citation, a data-rights breach) replace the `Sentence` and `Reader would believe` lines with
`Issue:` and `Why it matters:`, and keep `Evidence says` and `Fix`.

A check blocked by a missing input or an absent tool appears in up to three places: the
header's `Checks skipped`, a *finding* when it affects a verdict (e.g. an unresolvable
citation is a blocker), and the meta-editor Coverage section. Never report a blocked check as
passed.

Severity scale (shared across reviewers; binding findings only, per `binding-findings.md`):
- **blocker** — the false belief concerns a headline claim or a registered question's answer, or
  the finding is an integrity/citation failure (fabrication, a citation that does not support its
  sentence, a data-rights breach).
- **major** — the false belief concerns any other claim, or the fix needs new analysis or data.
- **minor** — a real but small false belief that a careful reader would likely catch.
- **note** — anything that fails the binding test: word choice, a missing qualifier, extra
  precision, style. Non-binding; never "fix before publication."

Never write a finding whose fix adds a qualifier, unless that qualifier is itself the correction
of the false belief. Never draft replacement prose; name the deletion or the corrected fact.

**Readability tier severity ceiling:** readability findings (plain-language, terminology &
acronym, accessibility / background) are normally `minor` or `note` and may rise to `major` only
for a completeness failure — a term/acronym used but never defined or missing from its index, a
missing required reader-facing section (Acronyms / Glossary), or a missing/badly-misleading
abstract. They are **never `blocker`**; the correctness tier owns blockers, and readability defers
to correctness in every conflict — except that a readability reviewer may always ask to **delete**
a qualifier that no binding finding requires.
