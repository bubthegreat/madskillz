"""Deterministic core + overlay render.

Output layout: synthesized frontmatter, overlay preamble + overlay sections (the
prescriptive layer for the medium), then the core body (identity, AI-tells,
descriptive layer, provenance). An overlay section whose first body line is
`<!-- override -->` and whose heading matches a core heading replaces that core
section in place instead of appearing in the overlay block.
"""

from . import profile as prof

OVERRIDE_MARK = "<!-- override -->"


class RenderError(Exception):
    pass


def render(core_text: str, overlay_text: str, context: str) -> str:
    core = prof.parse(core_text)
    overlay = prof.parse(overlay_text)

    overrides: dict[str, str] = {}
    additions: list[tuple[str, str]] = []
    for h, b in overlay.sections:
        if b.lstrip().startswith(OVERRIDE_MARK):
            if core.section(h) is None:
                raise RenderError(f"override for '{h}' has no matching core section")
            overrides[h] = b.lstrip()[len(OVERRIDE_MARK) :].lstrip("\n")
        else:
            additions.append((h, b))

    core_sections = [(h, overrides.get(h, b)) for h, b in core.sections]

    fm = {
        "voice": context,
        "owner": core.frontmatter.get("owner", overlay.frontmatter.get("owner", "")),
        "purpose": overlay.frontmatter.get("purpose", ""),
        "status": "rendered",
        "rendered-from": f"core + {context} overlay",
    }

    parts = [prof.render_frontmatter(fm)]
    if overlay.preamble.strip():
        parts.append(overlay.preamble.rstrip("\n") + "\n")
    for h, b in additions:
        parts.append(h + "\n" + b.rstrip("\n") + "\n")
    if core.preamble.strip():
        parts.append(core.preamble.rstrip("\n") + "\n")
    for h, b in core_sections:
        parts.append(h + "\n" + b.rstrip("\n") + "\n")
    return "\n".join(parts)
