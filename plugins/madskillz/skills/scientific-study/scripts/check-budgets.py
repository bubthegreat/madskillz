#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Enforce the four-document manuscript contract as a build gate.

Reviewers should never spend attention on arithmetic a script does perfectly.
This checks every cap in ``references/manuscript-structure.md`` and every
structural requirement in ``references/question-register.md``.

    uv run scripts/check-budgets.py <study_dir>

Exits 0 if the manuscript is within contract, 1 otherwise. ``--warn-only``
reports without failing, for use mid-draft.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PAPER_WORDS = 4300
SUMMARY_WORDS = 200
PAPER_DISPLAY_ITEMS = 4
PAPER_REFS = 50
METHODS_WORDS = 3000
EXTENDED_DATA_ITEMS = 10
LEGEND_WORDS = 300
SUBHEADING_CHARS = 40

# Acronyms the summary paragraph may use without tripping the check.
SUMMARY_ACRONYM_ALLOW = {"AI", "DNA", "RNA", "US", "UK", "EU"}


def strip_noise(md: str) -> str:
    """Drop fenced code, tables, image refs and headings — count prose only."""
    md = re.sub(r"```.*?```", " ", md, flags=re.S)
    md = re.sub(r"^\s*\|.*$", " ", md, flags=re.M)      # table rows
    md = re.sub(r"^\s*!\[.*$", " ", md, flags=re.M)     # image refs
    md = re.sub(r"^\s*#{1,6} .*$", " ", md, flags=re.M)  # headings
    return md


def words(md: str) -> int:
    return len(strip_noise(md).split())


def section(md: str, name: str) -> str:
    """Body of a top-level '## <name>' section, up to the next '## '."""
    m = re.search(rf"^## +{re.escape(name)}\b.*?$", md, flags=re.M | re.I)
    if not m:
        return ""
    rest = md[m.end():]
    nxt = re.search(r"^## ", rest, flags=re.M)
    return rest[: nxt.start()] if nxt else rest


def body_before_backmatter(md: str) -> str:
    """Everything up to the availability statements / references."""
    for marker in (r"^## +Data availability", r"^## +References"):
        m = re.search(marker, md, flags=re.M | re.I)
        if m:
            return md[: m.start()]
    return md


class Report:
    def __init__(self) -> None:
        self.fail: list[str] = []
        self.warn: list[str] = []
        self.ok: list[str] = []

    def check(self, cond: bool, label: str, detail: str = "") -> None:
        (self.ok if cond else self.fail).append(f"{label}{detail and '  ' + detail}")


def check_paper(d: Path, r: Report) -> None:
    p = d / "paper.md"
    if not p.exists():
        r.fail.append("paper.md MISSING")
        return
    md = p.read_text(encoding="utf-8")
    body = body_before_backmatter(md)

    n = words(body)
    r.check(n <= PAPER_WORDS, f"paper.md body {n}/{PAPER_WORDS} words")

    summ = section(md, "Summary") or section(md, "Abstract")
    if not summ:
        r.fail.append("paper.md has no '## Summary' section")
    else:
        sw = words(summ)
        r.check(sw <= SUMMARY_WORDS, f"summary {sw}/{SUMMARY_WORDS} words")
        txt = re.sub(r"\[[\d,\s;-]+\]", " ", strip_noise(summ))
        acr = {t for t in re.findall(r"\b[A-Z]{2,}\b", txt)} - SUMMARY_ACRONYM_ALLOW
        if acr:
            r.warn.append(f"summary uses acronyms {sorted(acr)} — Nature bars these unless essential")
        if re.search(r"\d", txt):
            nums = sorted(set(re.findall(r"\d+(?:\.\d+)?%?", txt)))[:6]
            r.warn.append(f"summary contains measurements {nums} — bar these unless essential")

    figs = len(re.findall(r"^\s*!\[", body, flags=re.M))
    tables = len(re.findall(r"^\s*\|.*\|\s*$\n\s*\|[\s:|-]+\|\s*$", body, flags=re.M))
    r.check(figs + tables <= PAPER_DISPLAY_ITEMS,
            f"paper.md display items {figs + tables}/{PAPER_DISPLAY_ITEMS}",
            f"({figs} figures, {tables} tables)")

    cited = {int(x) for x in re.findall(r"\[(\d+)(?:[,;]|\])", body)}
    r.check(len(cited) <= PAPER_REFS, f"paper.md cites {len(cited)}/{PAPER_REFS} references")

    for m in re.finditer(r"^#{3,6} +(.+)$", body, flags=re.M):
        h = m.group(1).strip()
        if len(h) > SUBHEADING_CHARS:
            r.warn.append(f"subheading {len(h)} chars (max {SUBHEADING_CHARS}): {h[:60]!r}")

    for m in re.finditer(r"^\*\*(?:Figure|Fig\.?) *\d+.*$", body, flags=re.M):
        seg = body[m.start(): m.start() + 4000].split("\n\n")[0]
        if words(seg) > LEGEND_WORDS:
            r.warn.append(f"figure legend {words(seg)} words (max {LEGEND_WORDS})")

    di = md.lower().find("## data availability")
    ci = md.lower().find("## code availability")
    ri = md.lower().find("## references")
    r.check(di >= 0, "Data availability statement present")
    r.check(ci >= 0, "Code availability statement present")
    if di >= 0 and ci >= 0 and ri >= 0:
        r.check(di < ci < ri, "availability order: Data -> Code -> References")


def check_methods(d: Path, r: Report) -> None:
    p = d / "methods.md"
    if not p.exists():
        r.fail.append("methods.md MISSING")
        return
    md = p.read_text(encoding="utf-8")
    n = words(md)
    r.check(n <= METHODS_WORDS, f"methods.md {n}/{METHODS_WORDS} words")

    figs = re.findall(r"^\s*!\[", md, flags=re.M)
    tabs = re.findall(r"^\s*\|.*\|\s*$\n\s*\|[\s:|-]+\|\s*$", md, flags=re.M)
    r.check(not figs, "methods.md contains no figures",
            f"(found {len(figs)} — move to extended-data.md)" if figs else "")
    r.check(not tabs, "methods.md contains no tables",
            f"(found {len(tabs)} — move to extended-data.md)" if tabs else "")

    r.check(bool(re.search(r"^## +Deviations from the analysis plan", md, flags=re.M | re.I)),
            "methods.md has 'Deviations from the analysis plan'")


def check_extended_data(d: Path, r: Report) -> None:
    p = d / "extended-data.md"
    if not p.exists():
        r.warn.append("extended-data.md absent (fine if the study needs none)")
        return
    md = p.read_text(encoding="utf-8")
    items = re.findall(r"^#{2,4} +Extended Data (?:Fig\.?|Figure|Table)", md, flags=re.M | re.I)
    r.check(len(items) <= EXTENDED_DATA_ITEMS,
            f"extended-data.md {len(items)}/{EXTENDED_DATA_ITEMS} items")

    paper = (d / "paper.md").read_text(encoding="utf-8") if (d / "paper.md").exists() else ""
    methods = (d / "methods.md").read_text(encoding="utf-8") if (d / "methods.md").exists() else ""
    both = paper + methods
    for m in re.finditer(r"^#{2,4} +(Extended Data (?:Fig\.?|Figure|Table) *\d+)", md, flags=re.M | re.I):
        label = m.group(1)
        key = re.sub(r"\s+", r"\\s*", re.sub(r"Fig\.?", r"Fig\\.?", label, flags=re.I))
        if not re.search(key, both, flags=re.I):
            r.warn.append(f"{label} is never cited from paper.md or methods.md")


def check_register(d: Path, r: Report) -> None:
    p = d / "question-register.md"
    if not p.exists():
        r.fail.append("question-register.md MISSING")
        return
    md = p.read_text(encoding="utf-8")
    rows = [ln for ln in md.splitlines()
            if re.match(r"^\s*\|\s*(Q\d+|E\d+)\s*\|", ln, flags=re.I)]
    r.check(bool(rows), "question-register.md lists at least one question")
    verdicts = {"answered", "answered-with-caveat", "premise-rejected", "evidence-insufficient"}
    for ln in rows:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        qid = cells[0] if cells else "?"
        verdict = cells[2].lower().strip("*` ") if len(cells) > 2 else ""
        if not verdict:
            r.fail.append(f"{qid}: no verdict recorded")
        elif verdict == "declined":
            r.fail.append(f"{qid}: 'declined' is not a verdict — see question-register.md")
        elif verdict not in verdicts:
            r.fail.append(f"{qid}: unknown verdict {verdict!r}; expected one of {sorted(verdicts)}")


def check_retired(d: Path, r: Report) -> None:
    if (d / "paper-short.md").exists():
        r.warn.append("paper-short.md present but the short form is retired in v0.22.0 "
                      "— a 4,300-word paper is its own digest")


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    warn_only = "--warn-only" in argv
    if len(args) != 1:
        print("usage: check-budgets.py <study_dir> [--warn-only]", file=sys.stderr)
        return 2
    d = Path(args[0]).resolve()
    if not d.is_dir():
        print(f"not a directory: {d}", file=sys.stderr)
        return 2

    r = Report()
    check_register(d, r)
    check_paper(d, r)
    check_methods(d, r)
    check_extended_data(d, r)
    check_retired(d, r)

    for line in r.ok:
        print(f"  ok    {line}")
    for line in r.warn:
        print(f"  WARN  {line}")
    for line in r.fail:
        print(f"  FAIL  {line}")

    print(f"\n{len(r.ok)} ok, {len(r.warn)} warnings, {len(r.fail)} failures")
    if r.fail and not warn_only:
        print("manuscript is outside the contract — see references/manuscript-structure.md")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
