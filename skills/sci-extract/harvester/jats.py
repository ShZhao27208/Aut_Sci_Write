"""Parse JATS and Elsevier full-text XML into an ordered document model.

JATS is the NLM/NISO standard used by PMC, Europe PMC, BMC, and SpringerOpen.
Elsevier ships its own schema, so it gets a separate reader that produces the
same output shape. Downstream code never sees which schema it came from.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Elsevier XML mixes several namespaces; JATS is mostly namespace-free.
NS = {
    "ce": "http://www.elsevier.com/xml/common/dtd",
    "xocs": "http://www.elsevier.com/xml/xocs/dtd",
    "ja": "http://www.elsevier.com/xml/ja/dtd",
    "xlink": "http://www.w3.org/1999/xlink",
    "mml": "http://www.w3.org/1998/Math/MathML",
}


@dataclass
class Figure:
    """One figure or table with its caption and image reference."""

    label: str = ""
    caption: str = ""
    graphic_href: str = ""
    figure_id: str = ""
    kind: str = "figure"  # "figure" or "table"
    table_html: str = ""
    local_path: str = ""

    def display_label(self) -> str:
        return self.label or self.figure_id or "Unlabeled"


@dataclass
class Section:
    """A document section, nested arbitrarily deep."""

    title: str = ""
    level: int = 1
    paragraphs: List[str] = field(default_factory=list)
    subsections: List["Section"] = field(default_factory=list)
    section_type: str = ""

    def word_count(self) -> int:
        own = sum(len(p.split()) for p in self.paragraphs)
        return own + sum(s.word_count() for s in self.subsections)


@dataclass
class Document:
    """Schema-agnostic parsed full text."""

    title: str = ""
    abstract: str = ""
    structured_abstract: Dict[str, str] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    tables: List[Figure] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    acknowledgements: str = ""
    funding_statement: str = ""
    conflict_statement: str = ""
    data_availability: str = ""
    supplementary: List[str] = field(default_factory=list)
    schema: str = ""
    parse_errors: List[str] = field(default_factory=list)

    def body_word_count(self) -> int:
        return sum(s.word_count() for s in self.sections)

    def has_body(self) -> bool:
        return self.body_word_count() > 200


def parse(xml_text: str, schema: str) -> Document:
    """Parse full-text XML. `schema` is "jats" or "elsevier-xml"."""
    doc = Document(schema=schema)
    if not xml_text:
        return doc
    try:
        root = ET.fromstring(_strip_doctype(xml_text))
    except ET.ParseError as exc:
        doc.parse_errors.append(f"XML parse failed: {exc}")
        return doc

    if schema == "elsevier-xml":
        _parse_elsevier(root, doc)
    else:
        _parse_jats(root, doc)
    return doc


def _strip_doctype(xml_text: str) -> str:
    """External DTDs make ElementTree attempt network fetches; drop them."""
    cleaned = re.sub(r"<!DOCTYPE[^>[]*(\[[^\]]*\])?[^>]*>", "", xml_text, count=1, flags=re.S)
    return cleaned.lstrip("﻿ \n\r\t")


def _text_of(node: Optional[ET.Element], *, keep_math: bool = True) -> str:
    """Flatten an element's mixed content to plain text.

    Inline math is preserved as a LaTeX-ish placeholder because the analysis
    template asks for equations, and dropping them silently loses meaning.
    """
    if node is None:
        return ""
    parts: List[str] = []
    _collect_text(node, parts)
    text = "".join(parts)
    if keep_math:
        text = text.replace("−", "-")
    return re.sub(r"\s+", " ", text).strip()


# Elements that end a run of text; without a separator, `itertext()` would glue
# "Acknowledgements" to the paragraph that follows it.
_BLOCK_TAGS = frozenset(
    {
        "p",
        "title",
        "label",
        "caption",
        "sec",
        "list-item",
        "td",
        "th",
        "tr",
        "disp-formula",
        "disp-quote",
        "abstract",
        "ack",
        "para",
        "simple-para",
        "section",
        "section-title",
    }
)


def _collect_text(node: ET.Element, parts: List[str]) -> None:
    """Flatten mixed content, inserting spaces at block boundaries."""
    if node.text:
        parts.append(node.text)
    for child in node:
        # JATS allows <fig> and <table-wrap> inside <p>. Both are extracted into
        # their own objects, so descending into them here would duplicate every
        # caption in the middle of the body text that cites the figure.
        if _local(child.tag) in _FLOATING_TAGS:
            if child.tail:
                parts.append(child.tail)
            continue
        if _local(child.tag) in _BLOCK_TAGS:
            parts.append(" ")
        _collect_text(child, parts)
        if child.tail:
            parts.append(child.tail)


# Extracted separately into Document.figures / .tables / .supplementary.
_FLOATING_TAGS = frozenset(
    {"fig", "fig-group", "table-wrap", "table-wrap-group", "supplementary-material"}
)


def _local(tag: str) -> str:
    """Strip any namespace prefix from a tag name."""
    return tag.rsplit("}", 1)[-1]


def _href(node: ET.Element) -> str:
    """Read an xlink:href, tolerating documents that omit the namespace."""
    return node.get("{http://www.w3.org/1999/xlink}href") or node.get("href") or ""


# --------------------------------------------------------------------- JATS ---

# Back matter that must not be treated as a body section.
_JATS_BACKMATTER_TITLES = {
    "acknowledgements": "acknowledgements",
    "acknowledgments": "acknowledgements",
    "funding": "funding_statement",
    "funding information": "funding_statement",
    "competing interests": "conflict_statement",
    "conflict of interest": "conflict_statement",
    "conflicts of interest": "conflict_statement",
    "declaration of competing interest": "conflict_statement",
    "data availability": "data_availability",
    "data availability statement": "data_availability",
    "code availability": "data_availability",
    "supplementary information": "supplementary_marker",
    "supplementary material": "supplementary_marker",
}


def _parse_jats(root: ET.Element, doc: Document) -> None:
    """Read a JATS document. Root may be `<article>` or an articleset wrapper."""
    article = root if _local(root.tag) == "article" else root.find(".//article")
    if article is None:
        doc.parse_errors.append("no <article> element found")
        return

    _jats_front(article, doc)
    body = article.find("body")
    if body is not None:
        doc.sections = _jats_sections(body, level=1, doc=doc)
    _jats_figures(article, doc)
    _jats_back(article, doc)
    _jats_references(article, doc)


def _jats_front(article: ET.Element, doc: Document) -> None:
    """Title, abstract (flat or structured), and author keywords."""
    title_node = article.find(".//title-group/article-title")
    doc.title = _text_of(title_node)

    for abstract in article.findall(".//abstract"):
        # Skip graphical or one-line teaser abstracts.
        if (abstract.get("abstract-type") or "").lower() in ("graphical", "teaser", "précis"):
            continue
        subsections = abstract.findall("sec")
        if subsections:
            for section in subsections:
                heading = _text_of(section.find("title")) or "Abstract"
                body = " ".join(_text_of(p) for p in section.findall("p"))
                if body:
                    doc.structured_abstract[heading] = body
            doc.abstract = " ".join(
                f"{k}: {v}" for k, v in doc.structured_abstract.items()
            )
        else:
            doc.abstract = " ".join(_text_of(p) for p in abstract.findall("p"))
        if doc.abstract:
            break

    for group in article.findall(".//kwd-group"):
        for keyword in group.findall("kwd"):
            text = _text_of(keyword)
            if text and text not in doc.keywords:
                doc.keywords.append(text)


def _jats_sections(parent: ET.Element, level: int, doc: Document) -> List[Section]:
    """Recursively read `<sec>` trees, diverting back matter out of the body."""
    sections: List[Section] = []

    # Paragraphs sitting directly under <body> with no wrapping <sec>.
    loose = [_text_of(p) for p in parent.findall("p")]
    loose = [p for p in loose if p]
    if loose and level == 1:
        sections.append(Section(title="Introduction", level=1, paragraphs=loose))

    for node in parent.findall("sec"):
        title = _text_of(node.find("title"))
        key = title.lower().strip().rstrip(":")
        if key in _JATS_BACKMATTER_TITLES:
            _absorb_backmatter(node, _JATS_BACKMATTER_TITLES[key], doc)
            continue

        section = Section(
            title=title,
            level=level,
            section_type=node.get("sec-type") or "",
            paragraphs=_jats_paragraphs(node),
        )
        section.subsections = _jats_sections(node, level + 1, doc)
        if section.title or section.paragraphs or section.subsections:
            sections.append(section)
    return sections


def _jats_paragraphs(node: ET.Element) -> List[str]:
    """Direct paragraphs plus display equations, in document order."""
    out: List[str] = []
    for child in node:
        tag = _local(child.tag)
        if tag == "p":
            text = _text_of(child)
            if text:
                out.append(text)
        elif tag in ("disp-formula", "disp-formula-group"):
            # Equations carry meaning the analysis template explicitly asks for.
            formula = _text_of(child)
            if formula:
                out.append(f"[Equation] {formula}")
        elif tag == "list":
            for item in child.findall(".//list-item"):
                text = _text_of(item)
                if text:
                    out.append(f"- {text}")
    return out


def _absorb_backmatter(node: ET.Element, field_name: str, doc: Document) -> None:
    """Route a recognized back-matter section into its dedicated field."""
    text = " ".join(_jats_paragraphs(node))
    if field_name == "supplementary_marker":
        for media in node.findall(".//media") + node.findall(".//supplementary-material"):
            href = _href(media)
            if href:
                doc.supplementary.append(href)
        if text:
            doc.supplementary.append(text)
        return
    current = getattr(doc, field_name, "")
    if text and not current:
        setattr(doc, field_name, text)


def _jats_figures(article: ET.Element, doc: Document) -> None:
    """Figures and tables with labels, captions, and image filenames."""
    for node in article.findall(".//fig"):
        graphic = node.find(".//graphic")
        doc.figures.append(
            Figure(
                figure_id=node.get("id") or "",
                label=_text_of(node.find("label")),
                caption=_text_of(node.find("caption")),
                graphic_href=_href(graphic) if graphic is not None else "",
                kind="figure",
            )
        )

    for node in article.findall(".//table-wrap"):
        table_node = node.find(".//table")
        doc.tables.append(
            Figure(
                figure_id=node.get("id") or "",
                label=_text_of(node.find("label")),
                caption=_text_of(node.find("caption")),
                graphic_href=_href(node.find(".//graphic"))
                if node.find(".//graphic") is not None
                else "",
                kind="table",
                table_html=_table_to_markdown(table_node) if table_node is not None else "",
            )
        )


def _table_to_markdown(table: ET.Element) -> str:
    """Render a JATS/XHTML table as markdown so it survives into raw.md."""
    rows: List[List[str]] = []
    for row in table.findall(".//tr"):
        cells = [_text_of(c) for c in row if _local(c.tag) in ("td", "th")]
        if cells:
            rows.append(cells)
    if not rows:
        return ""

    width = max(len(r) for r in rows)
    padded = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(c.replace("|", "\\|") for c in padded[0]) + " |"]
    lines.append("|" + "---|" * width)
    for row in padded[1:]:
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in row) + " |")
    return "\n".join(lines)


def _jats_back(article: ET.Element, doc: Document) -> None:
    """Back-matter statements that live outside `<body>`."""
    back = article.find("back")
    if back is None:
        return

    if not doc.acknowledgements:
        doc.acknowledgements = _text_of(back.find(".//ack"))

    for group in back.findall(".//funding-statement") + back.findall(".//funding-source"):
        text = _text_of(group)
        if text and not doc.funding_statement:
            doc.funding_statement = text

    for notes in back.findall(".//notes"):
        note_type = (notes.get("notes-type") or "").lower()
        text = _text_of(notes)
        if not text:
            continue
        if "competing" in note_type or "conflict" in note_type:
            doc.conflict_statement = doc.conflict_statement or text
        elif "data" in note_type:
            doc.data_availability = doc.data_availability or text

    for section in back.findall(".//sec"):
        key = _text_of(section.find("title")).lower().strip().rstrip(":")
        target = _JATS_BACKMATTER_TITLES.get(key)
        if target:
            _absorb_backmatter(section, target, doc)


def _jats_references(article: ET.Element, doc: Document) -> None:
    """Flatten each reference to a citation string; structure varies too much."""
    for ref in article.findall(".//ref"):
        text = _text_of(ref)
        if text:
            doc.references.append(text)


# ----------------------------------------------------------------- Elsevier ---

def _parse_elsevier(root: ET.Element, doc: Document) -> None:
    """Read Elsevier's `full-text-retrieval-response`.

    Elsevier ships either a structured `<ja:article>` tree or, for older
    content, a single `<xocs:rawtext>` blob. Handle both.
    """
    doc.title = _text_of(_find_any(root, "title")) or _text_of(_find_any(root, "dc:title"))
    _elsevier_abstract(root, doc)
    _elsevier_keywords(root, doc)

    original = _find_any(root, "originalText")
    scope = original if original is not None else root

    sections = _elsevier_sections(scope, level=1)
    if sections:
        doc.sections = sections
    else:
        _elsevier_rawtext(root, doc)

    _elsevier_figures(scope, doc)
    _elsevier_back(scope, doc)

    for ref in _findall_any(scope, "bib-reference"):
        text = _text_of(ref)
        if text:
            doc.references.append(text)


def _find_any(node: ET.Element, local_name: str) -> Optional[ET.Element]:
    """Find the first descendant with this local tag name, any namespace."""
    target = local_name.rsplit(":", 1)[-1]
    for child in node.iter():
        if _local(child.tag) == target:
            return child
    return None


def _findall_any(node: ET.Element, local_name: str) -> List[ET.Element]:
    target = local_name.rsplit(":", 1)[-1]
    return [c for c in node.iter() if _local(c.tag) == target]


def _elsevier_abstract(root: ET.Element, doc: Document) -> None:
    for abstract in _findall_any(root, "abstract"):
        if (abstract.get("class") or "").lower() in ("graphical", "author-highlights"):
            continue
        text = " ".join(
            _text_of(p) for p in _findall_any(abstract, "simple-para") + _findall_any(abstract, "para")
        )
        if text:
            doc.abstract = text
            break
    if not doc.abstract:
        doc.abstract = _text_of(_find_any(root, "description"))


def _elsevier_keywords(root: ET.Element, doc: Document) -> None:
    for keyword in _findall_any(root, "keyword"):
        text = _text_of(keyword)
        if text and text not in doc.keywords:
            doc.keywords.append(text)


def _elsevier_sections(node: ET.Element, level: int) -> List[Section]:
    """Elsevier nests `<ce:section>` with `<ce:section-title>` and `<ce:para>`."""
    sections: List[Section] = []
    for child in node:
        if _local(child.tag) != "section":
            if level == 1:
                sections.extend(_elsevier_sections(child, level))
            continue
        title = _text_of(_direct_child(child, "section-title"))
        paragraphs = [
            _text_of(p) for p in child if _local(p.tag) in ("para", "simple-para")
        ]
        section = Section(
            title=title,
            level=level,
            paragraphs=[p for p in paragraphs if p],
            subsections=_elsevier_sections(child, level + 1),
        )
        if section.title or section.paragraphs or section.subsections:
            sections.append(section)
    return sections


def _direct_child(node: ET.Element, local_name: str) -> Optional[ET.Element]:
    for child in node:
        if _local(child.tag) == local_name:
            return child
    return None


def _elsevier_rawtext(root: ET.Element, doc: Document) -> None:
    """Fallback: one unstructured text blob, split on blank lines."""
    raw = _find_any(root, "rawtext")
    if raw is None or not (raw.text or "").strip():
        return
    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw.text) if b.strip()]
    if blocks:
        doc.sections = [
            Section(title="Full Text", level=1, paragraphs=blocks, section_type="rawtext")
        ]
        doc.parse_errors.append("Elsevier returned unstructured rawtext; sections not delimited")


def _elsevier_figures(node: ET.Element, doc: Document) -> None:
    for figure in _findall_any(node, "figure"):
        link = _find_any(figure, "link")
        doc.figures.append(
            Figure(
                figure_id=figure.get("id") or "",
                label=_text_of(_find_any(figure, "label")),
                caption=_text_of(_find_any(figure, "caption")),
                graphic_href=(link.get("{http://www.w3.org/1999/xlink}href") or link.get("locator") or "")
                if link is not None
                else "",
                kind="figure",
            )
        )

    for table in _findall_any(node, "table"):
        doc.tables.append(
            Figure(
                figure_id=table.get("id") or "",
                label=_text_of(_find_any(table, "label")),
                caption=_text_of(_find_any(table, "caption")),
                kind="table",
                table_html=_table_to_markdown(table),
            )
        )


def _elsevier_back(node: ET.Element, doc: Document) -> None:
    doc.acknowledgements = doc.acknowledgements or _text_of(_find_any(node, "acknowledgment"))
    for section in _findall_any(node, "section"):
        key = _text_of(_direct_child(section, "section-title")).lower().strip().rstrip(":")
        target = _JATS_BACKMATTER_TITLES.get(key)
        if not target or target == "supplementary_marker":
            continue
        text = " ".join(
            _text_of(p) for p in section if _local(p.tag) in ("para", "simple-para")
        )
        if text and not getattr(doc, target, ""):
            setattr(doc, target, text)
