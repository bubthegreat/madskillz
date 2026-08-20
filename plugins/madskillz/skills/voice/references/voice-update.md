# Voice updater - the trait-judgment pass

The only LLM step in the voice pipeline. Everything else (markers, corpus selection, file
writes, materiality, git) is `voicectl`; see SKILL.md for the four-step flow. This file defines
how to judge.

## Input

`voicectl update-prep` gives you the new corpus entries (owner messages since
`Processed through`) and the live core path (`~/.madskillz/voice/core.md`).

## Judgment rules

1. Read the new messages as writing samples and ask: is there anything **genuinely new** about
   how the owner writes that the core does not already capture? Recurring turns of phrase,
   sentence rhythm, humor moves, punctuation habits, hedges, favorite words, structure,
   reasoning patterns, decision patterns.
2. Only real, repeated signals count; one-off wording is not a trait.
3. **Observed, never invented.** Every trait traces to real messages, quoted in the entry.
4. **Exclude non-authored noise**: pasted task notifications, agent output dumps, compaction
   summaries, [Pasted text] stubs, error dumps, dictated setup scripts.
5. **Register-aware tagging.** Tag each trait **keep** (flavor worth preserving) or
   **tone-down** (a crutch; capture the tendency, don't license it in prose). A phrase the
   owner over-reaches for goes under **Flagged overuse**.
6. **Descriptive only.** The pass extends core's descriptive sections (Mechanics, Inquiry
   style, Phrasebook, Thought-process patterns, Document-craft instincts, Decision heuristics,
   Spoken register, Flagged overuse). A newly red-lined AI-tell goes to core's AI-tells
   section. Overlays (prescriptive) change only on explicit owner correction, never from
   corpus mining.
7. **Incremental, not a rewrite.** Tighten or extend existing entries; do not restart or bloat.
   Keep the profile a tight, voice-defining brief.
8. **Don't force findings.** Most passes add little or nothing; a no-change pass is valid and
   honest - then skip apply and go straight to `voicectl sync`.

## Output

Write the full revised core (frontmatter, all sections, one dated Changelog line describing
what the pass added) to a temp file and hand it to `voicectl update-apply <file>`; it validates
the structure, installs it atomically, and bumps `Processed through`. Never edit the live core
in place and never bump markers by hand.
