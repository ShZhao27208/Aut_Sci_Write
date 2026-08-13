"""Classify a user-supplied string into a paper identifier.

Supported inputs: DOI, arXiv ID, PMID, PMCID, paper title, free-text query.
The classifier is deliberately conservative: anything it cannot prove is an
identifier becomes a search query, which the caller resolves interactively.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

IdKind = Literal["doi", "arxiv", "pmid", "pmcid", "title", "query"]

_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:a-z0-9<>\[\]+]+)", re.IGNORECASE)
_ARXIV_NEW_RE = re.compile(r"\b(\d{4}\.\d{4,5})(v\d+)?\b")
_ARXIV_OLD_RE = re.compile(
    r"\b([a-z-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?\b", re.IGNORECASE
)
_PMCID_RE = re.compile(r"\bPMC(\d{6,9})\b", re.IGNORECASE)
_PMID_RE = re.compile(r"^\d{7,8}$")

_DOI_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
    "DOI:",
)

# Trailing punctuation that gets pasted along with a DOI but is never part of it.
_DOI_TRAILING = ".,;)]}>'\""


@dataclass
class PaperRef:
    """A resolved handle on one paper, progressively enriched as we fetch."""

    kind: IdKind
    value: str
    raw_input: str
    doi: str = ""
    arxiv_id: str = ""
    pmid: str = ""
    pmcid: str = ""
    title: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def is_searchable(self) -> bool:
        """True when the input needs a database search before we can fetch."""
        return self.kind in ("title", "query")

    def label(self) -> str:
        """Short human-readable handle for logs."""
        return self.doi or self.arxiv_id or self.pmcid or self.pmid or self.value


def normalize_doi(text: str) -> str:
    """Strip URL prefixes and trailing punctuation from a DOI-ish string."""
    candidate = text.strip()
    for prefix in _DOI_URL_PREFIXES:
        if candidate.lower().startswith(prefix.lower()):
            candidate = candidate[len(prefix) :]
            break
    candidate = candidate.strip().rstrip(_DOI_TRAILING)
    match = _DOI_RE.search(candidate)
    return match.group(1).rstrip(_DOI_TRAILING) if match else ""


def classify(text: str) -> PaperRef:
    """Turn an arbitrary user string into a PaperRef."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty identifier")

    doi = normalize_doi(raw)
    if doi:
        return PaperRef(kind="doi", value=doi, raw_input=raw, doi=doi)

    pmcid_match = _PMCID_RE.search(raw)
    if pmcid_match:
        pmcid = f"PMC{pmcid_match.group(1)}"
        return PaperRef(kind="pmcid", value=pmcid, raw_input=raw, pmcid=pmcid)

    arxiv_id = _extract_arxiv_id(raw)
    if arxiv_id:
        return PaperRef(kind="arxiv", value=arxiv_id, raw_input=raw, arxiv_id=arxiv_id)

    bare = raw.strip()
    if _PMID_RE.match(bare):
        return PaperRef(kind="pmid", value=bare, raw_input=raw, pmid=bare)

    # Distinguish "a title" from "a topic query" by length and shape. A title is
    # long and sentence-like; a query is short keywords. Both route to search,
    # but titles get exact-match scoring while queries get relevance ranking.
    kind: IdKind = "title" if _looks_like_title(bare) else "query"
    return PaperRef(kind=kind, value=bare, raw_input=raw, title=bare if kind == "title" else "")


def _extract_arxiv_id(text: str) -> str:
    """Pull an arXiv ID out of a URL, an `arXiv:` prefix, or a bare ID."""
    lowered = text.lower()
    if "arxiv.org" in lowered or lowered.startswith("arxiv:") or _is_bare_arxiv(text):
        cleaned = re.sub(r"^arxiv:", "", text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"https?://arxiv\.org/(abs|pdf)/", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\.pdf$", "", cleaned, flags=re.IGNORECASE)
        new_match = _ARXIV_NEW_RE.search(cleaned)
        if new_match:
            return new_match.group(1)
        old_match = _ARXIV_OLD_RE.search(cleaned)
        if old_match:
            return old_match.group(1)
    return ""


def _is_bare_arxiv(text: str) -> bool:
    """A standalone `2301.07041` with nothing else around it."""
    stripped = text.strip()
    match = _ARXIV_NEW_RE.fullmatch(stripped)
    return match is not None


def _looks_like_title(text: str) -> bool:
    """Heuristic: >=6 words or >=45 chars reads as a title, not a keyword query."""
    return len(text.split()) >= 6 or len(text) >= 45
