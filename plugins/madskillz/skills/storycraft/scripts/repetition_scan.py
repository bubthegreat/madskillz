# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Deterministic repetition/device scanner for storycraft.

Flags repeated n-grams, crutch phrases, and near-identical chapter openings so the
Repetition & Device Auditor persona can judge lazy vs. intentional repetition.
Pure stdlib; run with `uv run repetition_scan.py <book_dir>`.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

_WORD = re.compile(r"[a-z0-9']+")

_STOPWORDS = frozenset("""
a an the this that these those some any each every all both no
i me my we us our you your he him his she her hers it its they them their
who whom which what
of to in on at by for with from into onto over under up down out off about as
through between behind before after
and or but nor so yet if because while than then
is am are was were be been being have has had do does did
will would can could should may might must
""".split())


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def find_repeated_ngrams(text: str, n_min: int = 2, n_max: int = 6, min_count: int = 3) -> list[dict]:
    toks = tokenize(text)
    out: list[dict] = []
    for n in range(n_min, n_max + 1):
        if len(toks) < n:
            break
        counts = Counter(tuple(toks[i:i + n]) for i in range(len(toks) - n + 1))
        for gram, c in counts.items():
            if c >= min_count:
                out.append({"ngram": " ".join(gram), "n": n, "count": c})
    out.sort(key=lambda g: (-g["count"], -g["n"]))
    return out


def find_crutches(text: str, banned: list[str] | None = None, min_count: int = 4) -> list[dict]:
    toks = tokenize(text)
    counts = Counter(toks)
    banned_set = {b.lower() for b in (banned or [])}
    out: list[dict] = []
    seen: set[str] = set()
    for phrase in banned_set:
        c = len(re.findall(r"\b" + re.escape(phrase) + r"\b", text.lower()))
        if c >= 1:
            out.append({"phrase": phrase, "count": c, "banned": True})
            seen.add(phrase)
    for word, c in counts.items():
        if c >= min_count and word not in seen and len(word) > 2 and word not in _STOPWORDS:
            out.append({"phrase": word, "count": c, "banned": False})
    out.sort(key=lambda x: (not x["banned"], -x["count"]))
    return out


def _opening(text: str, sentences: int) -> set[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return set(tokenize(" ".join(parts[:sentences])))


def chapter_opening_similarity(chapters: list[str], sentences: int = 2, threshold: float = 0.6) -> list[dict]:
    openings = [_opening(c, sentences) for c in chapters]
    out: list[dict] = []
    for i in range(len(openings)):
        for j in range(i + 1, len(openings)):
            a, b = openings[i], openings[j]
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac >= threshold:
                out.append({"a": i, "b": j, "similarity": round(jac, 3)})
    out.sort(key=lambda x: -x["similarity"])
    return out


def scan(chapters: list[str], banned: list[str] | None = None) -> dict:
    joined = "\n\n".join(chapters)
    return {
        "repeated_ngrams": find_repeated_ngrams(joined),
        "crutches": find_crutches(joined, banned=banned),
        "similar_openings": chapter_opening_similarity(chapters),
    }


def _read_banned(book_dir: Path) -> list[str]:
    """Best-effort parse of `banned_phrases:` from book.yaml without a yaml dep.

    Supports a flow list (banned_phrases: ["a", "b"]) or a block list of `- item` lines.
    """
    f = book_dir / "book.yaml"
    if not f.exists():
        return []
    banned: list[str] = []
    in_block = False
    for line in f.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("banned_phrases:"):
            rest = s.split(":", 1)[1].strip()
            if rest.startswith("[") and rest.endswith("]"):
                return [x.strip().strip("\"'") for x in rest[1:-1].split(",") if x.strip()]
            in_block = True
            continue
        if in_block:
            if s.startswith("- "):
                banned.append(s[2:].strip().strip("\"'"))
            elif s and not s.startswith("#"):
                break
    return banned


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: repetition_scan.py <book_dir>", file=sys.stderr)
        return 2
    book_dir = Path(argv[1])
    chapter_files = sorted((book_dir / "chapters").glob("*.md"))
    chapters = [p.read_text(encoding="utf-8") for p in chapter_files]
    print(json.dumps(scan(chapters, banned=_read_banned(book_dir)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
