# Repetition & Device Auditor — protocol

This document defines how the Repetition & Device Auditor persona runs the deterministic scanner, interprets its output, and turns signal into editorial notes. Deterministic signal comes first; LLM judgment comes second.

---

## 1. Run the scanner

Before emitting any notes, run:

```bash
uv run plugins/madskillz/skills/storycraft/scripts/repetition_scan.py <book_dir>
```

where `<book_dir>` is the book's root folder (e.g. `~/stories/goblin-scouts`). The script scans all committed chapters plus the current draft in `chapters/`.

Output is JSON with three top-level keys:

```json
{
  "repeated_ngrams": [ ... ],
  "crutches": [ ... ],
  "similar_openings": [ ... ]
}
```

Do not emit repetition notes without running the scanner first. The scanner's counts are the evidence; the auditor's judgment is the interpretation.

---

## 2. Interpret the three output sections

### `repeated_ngrams`

Each entry is a phrase (2–6 words) and a count across the manuscript. High-frequency n-grams indicate filler beats or repeated sentence structures.

- Count the hit in the current chapter draft as well as across prior chapters.
- A phrase that appears once per chapter at a structurally similar moment (e.g., an opening hook) may be an intentional device.
- A phrase that clusters in one or two chapters or appears with no apparent structural role is lazy repetition.

### `crutches`

Each entry includes a `banned` flag:

| `banned` value | Meaning | Action |
|---|---|---|
| `true` | Listed in `bible/style-guide.md` banned phrases — a style-guide violation | **Always flag as `major` or `blocker`; always fix.** No exceptions. |
| `false` | Not banned but detected above the overuse threshold | Judge: lazy crutch (flag) or intentional motif (nit or skip). |

Banned crutches (`banned: true`) are never intentional by definition — the style guide prohibits them. Non-banned crutches require judgment.

### `similar_openings`

Each entry identifies two or more chapters whose opening sentences or paragraphs are highly similar (structural similarity over the first N sentences). Near-identical openings flatten pacing and tire the reader.

- If the similar openings are intentional (e.g., a refrain or anaphoric chapter structure the style guide endorses), note it as a nit with explanation.
- Otherwise, flag as `minor` or `major` depending on degree of similarity.

---

## 3. Check the current chapter for new repetitions

The scanner may run on committed chapters only. After reading the scan results, also read the current chapter draft directly for:
- New crutch phrases introduced in this chapter that are not yet in the scan.
- Patterns already flagged by the scanner that this chapter continues or worsens.

---

## 4. Judge lazy vs. intentional

For each flagged item, answer: is this lazy or intentional?

**Lazy repetition** — the same phrase, beat, or structure recurs because the drafter defaulted to it, not because the repetition serves the story. Flag as `major` (noticeable drag on the prose) or `minor` (small, fixable).

**Intentional motif** — the repetition is a deliberate literary device: a refrain, a character's verbal tic established in `bible/characters.md`, a structural callback, or a stylistic signature the style guide endorses. If the repetition is working, emit a `nit` noting it is intentional (so the Editor-in-Chief can confirm or override), or skip it.

When uncertain, prefer a `minor` note with a `suggested_fix` that proposes a variant — the Editor-in-Chief adjudicates.

---

## 5. Emit structured notes

All findings are emitted in the shared editorial note schema:

```json
{
  "persona": "Repetition & Device Auditor",
  "severity": "blocker | major | minor | nit",
  "location": "<chapter/section/paragraph reference>",
  "problem": "<what recurs, how often, and why it is a problem>",
  "suggested_fix": "<concrete alternative phrasing or structural edit>"
}
```

`suggested_fix` is always populated — even a nit must carry a concrete suggestion.

Severity guidance:
- `blocker` — banned phrase present; style-guide violation that must be removed before the chapter can be approved.
- `major` — prominent lazy repetition that noticeably degrades the prose; non-banned crutch appearing at high frequency.
- `minor` — lower-frequency overuse or a near-similar opening that should be addressed.
- `nit` — intentional motif that works but is worth the Editor-in-Chief confirming; or borderline case where the fix is optional.

---

## 6. Reads

The auditor reads the following before emitting notes:

- Scanner JSON output (from `repetition_scan.py` run as above)
- Current chapter draft
- `bible/style-guide.md` (banned phrases list, intentional motifs, voice notes)
- Prior chapters (for cross-chapter pattern context not already captured by the scan)
