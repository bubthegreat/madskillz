"""Voice profile parsing: frontmatter, h2 sections, provenance markers."""

import re
from dataclasses import dataclass


@dataclass
class Profile:
    frontmatter: dict[str, str]
    preamble: str                      # body text before the first h2
    sections: list[tuple[str, str]]    # (heading line "## X", body text after it)

    def section(self, heading: str) -> str | None:
        for h, b in self.sections:
            if h == heading:
                return b
        return None

    def body(self) -> str:
        parts = [self.preamble.rstrip("\n")]
        for h, b in self.sections:
            parts.append(h + "\n" + b.rstrip("\n"))
        return "\n\n".join(p for p in parts if p.strip()) + "\n"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body). Tolerates a missing frontmatter block."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[end + 5 :]


def parse(text: str) -> Profile:
    fm, body = parse_frontmatter(text)
    lines = body.splitlines(keepends=True)
    preamble: list[str] = []
    sections: list[tuple[str, str]] = []
    current: list[str] | None = None
    heading = ""
    for line in lines:
        if line.startswith("## "):
            if current is not None:
                sections.append((heading, "".join(current)))
            heading = line.rstrip("\n")
            current = []
        elif current is None:
            preamble.append(line)
        else:
            current.append(line)
    if current is not None:
        sections.append((heading, "".join(current)))
    return Profile(fm, "".join(preamble), sections)


def render_frontmatter(fm: dict[str, str]) -> str:
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n"


_MARKER_RE = {
    "processed": re.compile(r"(Processed through:)\s*(\S+)"),
    "repo": re.compile(r"(Repo-synced through:)\s*(\S+)"),
}


def get_marker(text: str, which: str) -> str:
    """Marker ts, or '' when absent / 'none'."""
    m = _MARKER_RE[which].search(text)
    if m and m.group(2).lower() != "none":
        return m.group(2)
    return ""


def set_marker(text: str, which: str, ts: str) -> str:
    if not _MARKER_RE[which].search(text):
        raise ValueError(f"no '{which}' marker line found in profile")
    return _MARKER_RE[which].sub(lambda m: f"{m.group(1)} {ts}", text, count=1)


REQUIRED_CORE_SECTIONS = (
    "## Mechanics",
    "## Flagged overuse (tendencies to watch)",
    "## Provenance & sync",
)


def validate_core(text: str) -> list[str]:
    """Return a list of problems; empty means valid."""
    problems = []
    fm, _ = parse_frontmatter(text)
    if fm.get("voice") != "core":
        problems.append("frontmatter 'voice' must be 'core'")
    if fm.get("status") != "personal":
        problems.append("frontmatter 'status' must be 'personal'")
    for h in REQUIRED_CORE_SECTIONS:
        if f"\n{h}\n" not in text and not text.startswith(h + "\n"):
            problems.append(f"missing required section: {h}")
    for which in ("processed", "repo"):
        if not _MARKER_RE[which].search(text):
            problems.append(f"missing marker: {which}")
    return problems
