# Compliance & privacy gate

Run this **before publishing** (Step 4 of `scientific-study`, after the review
loop). Its job: never let a dataset or third-party artifact reach
`jmresearch/research` if we lack the right to redistribute it, or if it carries
privacy obligations. Output feeds `ATTRIBUTIONS.md` and `COMPLIANCE.md`.

**Posture is fail-closed.** Unknown or unverifiable status → not published, unless
the user records an explicit override (§4). Never fabricate a verdict: "unverified"
is reported as "unverified," never as "cleared."

## 1. Inventory

List every distinct input that would land in `data/`, `assets/`, or `scripts/`,
plus anything embedded in the paper (figures derived from third-party data,
copied tables, etc.). For each, capture: name, source/provenance, and the license
or terms it came under. An input with no identifiable source or license is, by
default, **unverified** → fail-closed.

## 2. Dataset & third-party license classification

For each dataset / asset / code dependency, classify the redistribution right:

| Class | Examples of terms | Action |
|---|---|---|
| **Redistributable** | CC0, CC BY, CC BY-SA, MIT/BSD/Apache, public-domain, explicit "may redistribute" | **include** the artifact; record license + source in `ATTRIBUTIONS.md` |
| **Not redistributable** | "no redistribution," ToS forbidding copying, all-rights-reserved | **reference-only** (§3) |
| **Conditional / restricted** | DUA, click-through/EULA, registration-gated, non-commercial (NC), no-derivatives (ND), share-alike conflicts | **reference-only** unless the user confirms the specific condition is met; record the condition |
| **Unknown / unverifiable** | no license found, ambiguous terms, can't confirm provenance | **fail-closed** → reference-only or block; never include on a guess |

Notes:
- **Private is still redistribution.** A dataset's terms are honored even though
  `jmresearch/research` is private. Do not relax the gate for "it's a private repo."
- **Share-alike (SA):** redistributing SA-licensed data may force the same license
  on derived files. Flag any conflict with the chosen CC BY 4.0 / MIT defaults.
- **Non-commercial / no-derivatives:** treat as reference-only by default — the
  published study's downstream use is not knowable here.

## 3. Reference-only stubs

When an artifact cannot be redistributed, record enough to reproduce **without**
copying it. In `data/<name>.reference.md` (or an `ATTRIBUTIONS.md` entry) record:

- canonical citation and/or source URL,
- dataset **version / release** and a **content hash** (e.g. SHA-256) of the file
  used, so a reproducer can confirm they obtained the same data,
- exact retrieval / access steps (including any required registration or DUA),
- the governing license/terms and why it is reference-only.

## 4. Privacy screening

Screen `data/` and `assets/` for personal data before anything is staged:

- **PII/PHI signals:** names, emails, phone numbers, government/individual IDs,
  dates of birth, precise geolocation, IP addresses, free-text fields that may
  carry identifiers, and identifiable faces or other biometrics in images/audio.
- **Human-subjects data:** require evidence of consent/approval (IRB/ethics
  approval, participant consent) that **covers archival and sharing** — not just
  the original study. Absent that basis → block.

If PII/PHI is detected or the consent basis is missing/unclear → **block**. The
user must then do one of:

1. **de-identify** the data and re-run the screen,
2. provide a **compliant reference** instead of the raw data (§3), or
3. record an **explicit attestation** that the data is cleared for archival
   (who attested, on what basis) — captured verbatim in `COMPLIANCE.md`.

Never de-identify or scrub data automatically — block and ask.

## 5. Recording the outcome

Every input ends as exactly one of: **include**, **reference-only**, or
**blocked → resolved by (de-identify | reference | attestation | override)**.
Write the full disposition to `COMPLIANCE.md` (see `repo-layout.md` template),
including any user override and its recorded rationale. The PR description repeats
these outcomes so nothing non-compliant lands silently.

## 6. Synergy with the review loop

The gate runs right after the agentic review loop, so ingest the `ethics-integrity`
reviewer's flags from the latest cycle (human subjects, consent, dual-use, data
provenance) as gate inputs rather than re-deriving them — but still apply §2–§4 to
anything the review did not cover.
