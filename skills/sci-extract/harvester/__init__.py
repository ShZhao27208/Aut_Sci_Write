"""Paper harvesting subsystem for sci-extract.

Fetches complete metadata, native XML, full text, and figures for a paper
from every configured academic database, then renders two markdown files:
`raw.md` (verbatim English content) and an analysis prompt that the host
agent uses to write `analysis.md`.
"""

from __future__ import annotations

__all__ = [
    "env",
    "figures",
    "fulltext",
    "identify",
    "jats",
    "metadata",
    "oa_package",
    "render",
]
