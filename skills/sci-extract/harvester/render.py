"""Output writers: raw.md, metadata.json, native XML, and the analysis prompt.

`raw.md` is the AI-readable substitute for the PDF: every field the databases
returned plus the complete body text, with figures embedded as relative links so
an agent reading the markdown sees the images in place. It is written in English
because that is the language of the source material and paraphrasing it here
would defeat the purpose of a verbatim capture.

`_analysis_prompt.md` is the handoff to whatever agent is running this skill. The
prompt carries the extraction template and asks for Chinese output; no LLM
credentials are used or needed, since the host agent does the writing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .figures import FigureReport
from .fulltext import FullText
from .jats import Document, Figure, Section
from .metadata import PaperMetadata

RAW_NAME = "raw.md"
ANALYSIS_NAME = "analysis.md"
PROMPT_NAME = "_analysis_prompt.md"
METADATA_NAME = "metadata.json"
XML_NAME = "fulltext.xml"
PDF_NAME = "paper.pdf"

_SLUG_STOPWORDS = frozenset(
    {"a", "an", "the", "of", "for", "and", "or", "in", "on", "with", "to", "from", "by"}
)


@dataclass
class RenderResult:
    """Paths written for one paper."""

    directory: Path
    raw: Path | None = None
    metadata: Path | None = None
    xml: Path | None = None
    prompt: Path | None = None
    pdf: Path | None = None
    # True when analysis.md predates this run and now describes an older capture.
    stale_analysis: bool = False

    def written(self) -> list[Path]:
        return [
            p
            for p in (self.raw, self.metadata, self.xml, self.prompt, self.pdf)
            if p is not None
        ]


def paper_dirname(meta: PaperMetadata) -> str:
    """Stable, filesystem-safe directory name: `{year}_{author}_{short-title}`."""
    year = meta.year or "n.d."
    author = _slug(meta.first_author_family()) or "unknown"
    words: list[str] = []
    for word in re.findall(r"[A-Za-z0-9]+", meta.title or "untitled"):
        if word.lower() in _SLUG_STOPWORDS and words:
            continue
        words.append(word.lower())
        if len(words) == 6:
            break
    title = "-".join(words) or "untitled"
    return f"{year}_{author}_{title}"[:120]


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()


def write_raw(
    path: Path,
    meta: PaperMetadata,
    doc: Document | None,
    fulltext: FullText,
    figure_report: FigureReport | None,
) -> Path:
    """Write the complete human and AI readable capture of the paper."""
    lines: list[str] = []
    out = lines.append

    title = meta.title or (doc.title if doc else "") or "Untitled"
    out(f"# {title}")
    if meta.subtitle:
        out(f"\n*{meta.subtitle}*")
    out("")
    _raw_status_badge(out, doc, figure_report, fulltext)
    _raw_citation_block(out, meta)
    _raw_identifiers(out, meta)
    _raw_authors(out, meta)
    _raw_abstract(out, meta, doc)
    _raw_keywords(out, meta, doc)

    # Figures are emitted inline at their first citation; this tracks which ones
    # have already been placed so the trailing gallery only holds the rest.
    emitted: set[int] = set()

    if doc is not None and doc.has_body():
        out("## Full Text")
        out("")
        for section in doc.sections:
            _raw_section(out, section, doc, emitted)
    else:
        out("## Full Text")
        out("")
        out(_no_fulltext_note(meta, fulltext))
        out("")

    _raw_orphan_figures(out, doc, figure_report, emitted)
    _raw_tables(out, doc)
    _raw_backmatter(out, doc)
    _raw_references(out, meta, doc)
    _raw_provenance(out, meta, fulltext, figure_report)

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


FULLTEXT_WITH_FIGURES = "论文全文已提取（包括图片）"
FULLTEXT_PDF_FIGURES = "论文全文已提取（图片从 PDF 截出）"
FULLTEXT_NO_FIGURES = "论文全文已提取（无图片）"
FULLTEXT_FIGURES_SKIPPED = "论文全文已提取（图片按要求跳过）"
NO_FULLTEXT = "论文全文未提取"


def extraction_status(
    doc: Document | None, figure_report: FigureReport | None
) -> str:
    """The badge that goes under the title, naming exactly what was captured.

    A reader deciding whether this file is usable needs the answer before the
    metadata table, and the three states are not interchangeable: figures cropped
    from a PDF carry order-matched captions that may be misaligned, and full text
    with no figures at all is a different kind of gap from no full text.
    """
    if doc is None or not doc.has_body():
        return NO_FULLTEXT
    method = figure_report.method if figure_report else "none"
    saved = figure_report.count if figure_report else 0
    if method == "skipped":
        return FULLTEXT_FIGURES_SKIPPED
    if saved and method == "publisher":
        return FULLTEXT_WITH_FIGURES
    if saved and method == "pdf-embedded":
        return FULLTEXT_PDF_FIGURES
    return FULLTEXT_NO_FIGURES


def _raw_status_badge(
    out,
    doc: Document | None,
    figure_report: FigureReport | None,
    fulltext: FullText,
) -> None:
    """Print the badge plus, when something is missing, why it is missing."""
    status = extraction_status(doc, figure_report)
    out(f"> **{status}**")
    detail = _status_detail(status, doc, figure_report, fulltext)
    if detail:
        out(">")
        out(f"> {detail}")
    out("")


def _status_detail(
    status: str,
    doc: Document | None,
    figure_report: FigureReport | None,
    fulltext: FullText,
) -> str:
    if status == FULLTEXT_FIGURES_SKIPPED:
        return "本次运行指定了 --skip-figures，未尝试抓图；正文与图注不受影响。"
    if status == FULLTEXT_WITH_FIGURES:
        return f"{figure_report.count} 张图片来自出版社原图，分辨率与原文一致。"
    if status == FULLTEXT_PDF_FIGURES:
        return (
            f"{figure_report.count} 张图片由 PDF 页面裁切得到，图注按出现顺序匹配，"
            "可能与图片不完全对应，引用前请核对。"
        )
    if status == FULLTEXT_NO_FIGURES:
        expected = len(doc.figures) if doc else 0
        if not expected:
            return "原文未包含图片。"
        reason = _figure_failure_reason(figure_report)
        return f"正文含 {expected} 处图片，均未取到{reason}；图注已保留在正文中。"
    return _no_fulltext_reason(fulltext)


def _figure_failure_reason(figure_report: FigureReport | None) -> str:
    if figure_report and figure_report.notes:
        return f"（{figure_report.notes[0]}）"
    if figure_report and figure_report.failed:
        return f"（{figure_report.failed[0]}）"
    return ""


def _no_fulltext_reason(fulltext: FullText) -> str:
    """Name the concrete obstacle, not just the fact of failure."""
    if fulltext.attempts:
        return (
            "本文仅含元数据与摘要，未取到正文。"
            f"已尝试：{'；'.join(fulltext.attempts)}。"
        )
    return "本文仅含元数据与摘要，未取到正文：没有可用的开放获取全文源。"


def _raw_citation_block(out, meta: PaperMetadata) -> None:
    bits: list[str] = []
    if meta.journal:
        bits.append(meta.journal)
    if meta.year:
        bits.append(meta.year)
    if meta.volume:
        bits.append(f"vol. {meta.volume}" + (f"({meta.issue})" if meta.issue else ""))
    if meta.pages:
        bits.append(f"pp. {meta.pages}")
    elif meta.article_number:
        bits.append(f"art. {meta.article_number}")
    if bits:
        out(f"**{' | '.join(bits)}**")
        out("")

    rows: list[tuple[str, str]] = []
    if meta.publisher:
        rows.append(("Publisher", meta.publisher))
    if meta.paper_type:
        rows.append(("Type", meta.paper_type))
    for label, value in (
        ("Published", meta.published_date),
        ("Online", meta.online_date),
        ("Accepted", meta.accepted_date),
        ("Received", meta.received_date),
    ):
        if value:
            rows.append((label, value))
    if meta.license:
        rows.append(("License", meta.license))
    if meta.oa_status:
        access = meta.oa_status + (" (open access)" if meta.is_open_access else "")
        rows.append(("Access", access))
    counts = ", ".join(f"{src}: {n}" for src, n in sorted(meta.citation_counts.items()))
    if counts:
        rows.append(("Citations", counts))
    if rows:
        out("| Field | Value |")
        out("| --- | --- |")
        for label, value in rows:
            out(f"| {label} | {_cell(value)} |")
        out("")


def _raw_identifiers(out, meta: PaperMetadata) -> None:
    ids = [
        ("DOI", meta.doi, f"https://doi.org/{meta.doi}" if meta.doi else ""),
        ("PMID", meta.pmid, f"https://pubmed.ncbi.nlm.nih.gov/{meta.pmid}/" if meta.pmid else ""),
        (
            "PMCID",
            meta.pmcid,
            f"https://pmc.ncbi.nlm.nih.gov/articles/{meta.pmcid}/" if meta.pmcid else "",
        ),
        ("arXiv", meta.arxiv_id, f"https://arxiv.org/abs/{meta.arxiv_id}" if meta.arxiv_id else ""),
        ("Scopus", meta.scopus_id, ""),
        ("WoS", meta.wos_uid, ""),
    ]
    present = [(label, value, url) for label, value, url in ids if value]
    if not present:
        return
    out("## Identifiers")
    out("")
    for label, value, url in present:
        out(f"- **{label}:** {f'[{value}]({url})' if url else value}")
    out("")


def _raw_authors(out, meta: PaperMetadata) -> None:
    if not meta.authors:
        return
    out(f"## Authors ({len(meta.authors)})")
    out("")
    for author in meta.authors:
        parts = [f"**{author.display()}**"]
        if author.orcid:
            parts.append(f"ORCID {author.orcid}")
        if author.is_corresponding:
            parts.append("corresponding")
        out(f"- {', '.join(parts)}")
        for affiliation in author.affiliations:
            out(f"  - {affiliation}")
    out("")

    if meta.funders:
        out("## Funding")
        out("")
        for funder in meta.funders:
            name = funder.get("name") or funder.get("funder") or "Unnamed funder"
            awards = funder.get("awards") or funder.get("award") or []
            if isinstance(awards, str):
                awards = [awards]
            suffix = f" ({', '.join(str(a) for a in awards)})" if awards else ""
            out(f"- {name}{suffix}")
        out("")


def _raw_abstract(out, meta: PaperMetadata, doc: Document | None) -> None:
    structured = doc.structured_abstract if doc else {}
    if structured:
        out("## Abstract")
        out("")
        for heading, body in structured.items():
            out(f"**{heading}.** {body}")
            out("")
        return
    abstract = (doc.abstract if doc and doc.abstract else "") or meta.abstract
    if abstract:
        out("## Abstract")
        out("")
        out(abstract)
        out("")
    if meta.tldr:
        out(f"> **TL;DR (Semantic Scholar):** {meta.tldr}")
        out("")


def _raw_keywords(out, meta: PaperMetadata, doc: Document | None) -> None:
    groups = [
        ("Keywords", (doc.keywords if doc else []) or meta.keywords),
        ("MeSH Terms", meta.mesh_terms),
        ("Topics", meta.topics),
        ("Subjects", meta.subjects),
    ]
    rendered = [(label, values) for label, values in groups if values]
    if not rendered:
        return
    for label, values in rendered:
        out(f"**{label}:** {', '.join(str(v) for v in values)}")
        out("")


def _cell(value: str) -> str:
    """Escape a value for a markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _raw_section(
    out,
    section: Section,
    doc: Document,
    emitted: set[int],
    level: int = 3,
) -> None:
    """Render one section and everything nested under it."""
    if section.title:
        out(f"{'#' * min(level, 6)} {section.title}")
        out("")
    for paragraph in section.paragraphs:
        out(paragraph)
        out("")
        # Place each figure right after the paragraph that first cites it, so the
        # image lands in the reading order an agent will follow.
        for figure in _figures_cited_in(paragraph, doc, emitted):
            _emit_figure(out, figure)
    for subsection in section.subsections:
        _raw_section(out, subsection, doc, emitted, level + 1)


def _figures_cited_in(
    paragraph: str, doc: Document, emitted: set[int]
) -> list[Figure]:
    """Figures whose label appears in this paragraph and are not yet emitted."""
    found: list[Figure] = []
    for position, figure in enumerate(doc.figures):
        if position in emitted or not figure.local_path:
            continue
        if _mentions(paragraph, figure):
            emitted.add(position)
            found.append(figure)
    return found


def _mentions(paragraph: str, figure: Figure) -> bool:
    """Whether a paragraph cites this figure, tolerating label spelling variants."""
    number = re.search(r"(\d+)", figure.label or figure.figure_id or "")
    if not number:
        return False
    n = number.group(1)
    # Papers cite panels ("Fig. 1a", "Fig. 1c-e") and ranges ("Figures 1 and 2"),
    # so the number may be followed by a panel letter and may sit anywhere in a
    # list. A trailing \b would reject every one of those and push the figure into
    # the orphan gallery. (?!\d) keeps Fig. 1 from matching Fig. 10.
    pattern = rf"\b(?:fig(?:ure)?s?\.?)\s*(?:\d+\s*(?:,|and|to|-|–)\s*)*{n}(?!\d)"
    return re.search(pattern, paragraph, re.IGNORECASE) is not None


def _emit_figure(out, figure: Figure) -> None:
    label = figure.display_label()
    out(f"![{label}]({figure.local_path})")
    out("")
    caption = figure.caption.strip()
    out(f"**{label}.** {caption}" if caption else f"**{label}.**")
    out("")


def _raw_orphan_figures(
    out,
    doc: Document | None,
    figure_report: FigureReport | None,
    emitted: set[int],
) -> None:
    """Figures never cited by name in the body, plus any that failed to download."""
    if doc is None:
        return
    orphans = [
        f
        for position, f in enumerate(doc.figures)
        if f.local_path and position not in emitted
    ]
    missing = [f for f in doc.figures if not f.local_path]
    if not orphans and not missing:
        return

    out("## Figures")
    out("")
    for figure in orphans:
        _emit_figure(out, figure)
    for figure in missing:
        label = figure.display_label()
        caption = figure.caption.strip()
        out(f"**{label}.** {caption}" if caption else f"**{label}.**")
        out("")
        out(f"*Image not retrieved. Source filename: `{figure.graphic_href}`*")
        out("")
    if figure_report and figure_report.method == "pdf":
        out(
            "*Figures above were cropped from the PDF, so caption pairing follows "
            "document order and may be approximate.*"
        )
        out("")


def _raw_tables(out, doc: Document | None) -> None:
    if doc is None or not doc.tables:
        return
    out("## Tables")
    out("")
    for table in doc.tables:
        label = table.display_label()
        caption = table.caption.strip()
        out(f"**{label}.** {caption}" if caption else f"**{label}.**")
        out("")
        if table.table_html:
            out(table.table_html)
            out("")
        elif table.local_path:
            out(f"![{label}]({table.local_path})")
            out("")
        else:
            out(f"*Table body not retrieved. Source filename: `{table.graphic_href}`*")
            out("")


def _raw_backmatter(out, doc: Document | None) -> None:
    if doc is None:
        return
    blocks = [
        ("Data Availability", doc.data_availability),
        ("Funding Statement", doc.funding_statement),
        ("Acknowledgements", doc.acknowledgements),
        ("Competing Interests", doc.conflict_statement),
    ]
    for heading, body in blocks:
        if body and body.strip():
            out(f"## {heading}")
            out("")
            out(body.strip())
            out("")
    if doc.supplementary:
        out("## Supplementary Material")
        out("")
        for item in doc.supplementary:
            out(f"- {item}")
        out("")


def _raw_references(out, meta: PaperMetadata, doc: Document | None) -> None:
    entries: list[str] = list(doc.references) if doc and doc.references else []
    if not entries and meta.references:
        for ref in meta.references:
            text = ref.get("citation") or ref.get("unstructured") or ""
            if not text:
                bits = [ref.get(k, "") for k in ("author", "year", "title", "journal")]
                text = ", ".join(b for b in bits if b)
            doi = ref.get("doi")
            if doi and doi not in text:
                text = f"{text} https://doi.org/{doi}".strip()
            if text:
                entries.append(text)
    if not entries:
        return
    out(f"## References ({len(entries)})")
    out("")
    for index, entry in enumerate(entries, start=1):
        out(f"{index}. {entry}")
    out("")


def _raw_provenance(
    out,
    meta: PaperMetadata,
    fulltext: FullText,
    figure_report: FigureReport | None,
) -> None:
    """Record where every part came from, so gaps are legible rather than silent."""
    out("---")
    out("")
    out("## Provenance")
    out("")
    if meta.sources_consulted:
        out(f"- **Metadata sources:** {', '.join(sorted(meta.sources_consulted))}")
    if fulltext.found:
        native = "native" if fulltext.is_native_xml else "converted"
        out(f"- **Full text:** {fulltext.source} ({fulltext.format}, {native} XML)")
    else:
        out("- **Full text:** not retrieved")
    if figure_report:
        out(
            f"- **Figures:** {figure_report.count} saved"
            + (f" via {figure_report.method}" if figure_report.method != "none" else "")
        )
        for note in figure_report.notes:
            out(f"  - {note}")
        for failure in figure_report.failed:
            out(f"  - {failure}")
    if meta.source_errors:
        out("- **Source errors:**")
        for source, error in sorted(meta.source_errors.items()):
            out(f"  - {source}: {error}")
    if fulltext.errors:
        out("- **Full text attempts:**")
        for error in fulltext.errors:
            out(f"  - {error}")
    out("")


def _no_fulltext_note(meta: PaperMetadata, fulltext: FullText) -> str:
    """State what survived the degrade, what blocked the rest, and what to do next.

    A downstream reader must not mistake this file for a full capture, so the gap
    is spelled out with the concrete obstacle per source and the remaining routes
    to the text, rather than a bare "not available".
    """
    lines = [
        "**Full text was not retrieved. This capture is degraded to the metadata "
        "layer.**",
        "**Captured:** " + _degraded_inventory(meta),
        "**Missing:** " + _degraded_gaps(meta),
    ]
    if fulltext.attempts:
        attempted = "\n".join(f"- {attempt}" for attempt in fulltext.attempts)
        lines.append(f"**Sources attempted:**\n{attempted}")
    lines.append("**How to obtain the text:**\n" + _degraded_routes(meta))
    return "\n\n".join(lines)


def _degraded_gaps(meta: PaperMetadata) -> str:
    """List only what is genuinely absent, so the note cannot contradict the file."""
    gaps = ["body sections", "figures", "tables"]
    if not meta.references:
        gaps.append("the reference list")
    if not meta.abstract:
        gaps.append("the abstract, which no source carried either")
    text = ", ".join(gaps[:-1]) + f" and {gaps[-1]}" if len(gaps) > 1 else gaps[0]
    if meta.references:
        text += (
            f". The {len(meta.references)} references below come from metadata "
            "sources, so they may be ordered or formatted differently from the "
            "published list"
        )
    return text + "."


def _degraded_inventory(meta: PaperMetadata) -> str:
    """Name the fields that did land, so the file's value is legible."""
    present = ["bibliographic metadata"]
    if meta.abstract:
        present.append("abstract")
    if meta.tldr:
        present.append("TL;DR")
    if meta.keywords or meta.mesh_terms or meta.topics or meta.subjects:
        present.append("keywords/subject terms")
    if meta.references:
        present.append(f"{len(meta.references)} references from metadata sources")
    if meta.funders:
        present.append("funding")
    return ", ".join(present) + "."


def _degraded_routes(meta: PaperMetadata) -> str:
    """Concrete next steps, ordered by how likely they are to work."""
    routes: list[str] = []
    landing = meta.urls.get("doi") or (
        f"https://doi.org/{meta.doi}" if meta.doi else ""
    )
    if landing:
        routes.append(f"- Publisher page (may allow institutional access): {landing}")
    if meta.pmid:
        routes.append(
            f"- PubMed record: https://pubmed.ncbi.nlm.nih.gov/{meta.pmid}/"
        )
    if meta.oa_pdf_url:
        routes.append(
            f"- An open PDF was reported but could not be fetched from here: "
            f"{meta.oa_pdf_url}"
        )
    if not meta.is_open_access:
        routes.append(
            "- This article is not open access. If your institution is entitled, "
            "add the publisher API key to the .env file and re-run; the Elsevier "
            "and Springer full-text APIs honour subscriber entitlement."
        )
    routes.append(
        "- Re-running later can help when a source failed on a transient error "
        "or an exhausted daily quota rather than on entitlement."
    )
    return "\n".join(routes)


def write_metadata(
    path: Path,
    meta: PaperMetadata,
    doc: Document | None,
    fulltext: FullText,
    figure_report: FigureReport | None,
    *,
    include_raw: bool = False,
) -> Path:
    """Write the merged metadata record plus a harvest audit trail."""
    payload = meta.to_dict(include_raw=include_raw)
    payload["harvest"] = {
        "extraction_status": extraction_status(doc, figure_report),
        "fulltext_source": fulltext.source,
        "fulltext_format": fulltext.format,
        "fulltext_is_native_xml": fulltext.is_native_xml,
        "fulltext_attempts": fulltext.attempts,
        "fulltext_errors": fulltext.errors,
        "figure_method": figure_report.method if figure_report else "none",
        "figures_saved": figure_report.count if figure_report else 0,
        "figure_failures": figure_report.failed if figure_report else [],
        "figure_notes": figure_report.notes if figure_report else [],
    }
    if doc is not None:
        payload["document"] = {
            "schema": doc.schema,
            "body_word_count": doc.body_word_count(),
            "section_count": len(doc.sections),
            "figure_count": len(doc.figures),
            "table_count": len(doc.tables),
            "reference_count": len(doc.references),
            "parse_errors": doc.parse_errors,
        }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return path


_RESEARCH_QUESTIONS = (
    "What are you trying to do?",
    "What is the problem, how is it done today, and what are the limits of current practice?",
    "What is new in the approach, including core idea, math, and method, and why does the paper claim it will succeed?",
    "Who cares? If successful, what difference does it make?",
    "What are the risks?",
    "How much will it cost?",
    "What are the experiments and results?",
)

_REVIEW_SECTIONS = (
    "Review scope",
    "Why this review exists now",
    "Taxonomy or organizing framework",
    "Literature selection and evidence base",
    "Field landscape and main themes",
    "Consensus findings",
    "Disagreements, controversies, and heterogeneity",
    "Evidence quality and bias",
    "Gaps and future directions",
    "Important figures and tables",
    "Bottom-line takeaways",
)

_REVIEW_MARKERS = (
    "review",
    "survey",
    "systematic review",
    "meta-analysis",
    "meta analysis",
    "scoping review",
    "overview",
    "tutorial",
    "perspective",
    "state of the art",
    "advances in",
    "recent progress",
)


def classify_paper_type(meta: PaperMetadata, doc: Document | None) -> str:
    """Guess "review" or "research" from the title, type field and section names."""
    haystack = " ".join(
        [
            (meta.title or "").lower(),
            (meta.paper_type or "").lower(),
            " ".join(str(s).lower() for s in meta.subjects),
        ]
    )
    if any(marker in haystack for marker in _REVIEW_MARKERS):
        return "review"
    if doc is not None:
        headings = " ".join((s.title or "").lower() for s in doc.sections)
        # A methods-and-results spine is the clearest signal of original research.
        if any(word in headings for word in ("method", "materials", "experiment")) and any(
            word in headings for word in ("result", "finding", "evaluation")
        ):
            return "research"
        if "search strategy" in headings or "inclusion criteria" in headings:
            return "review"
    return "research"


def write_prompt(
    path: Path,
    meta: PaperMetadata,
    doc: Document | None,
    paper_type: str,
    *,
    figure_report: FigureReport | None = None,
    skill_md: Path | None = None,
) -> Path:
    """Write the instruction file the host agent follows to produce analysis.md.

    The host agent is whatever model is already running this skill, so no LLM
    endpoint or key is referenced here.
    """
    lines: list[str] = []
    out = lines.append
    title = meta.title or (doc.title if doc else "") or "Untitled"
    body_words = doc.body_word_count() if doc else 0

    out("# Analysis task: write `analysis.md`")
    out("")
    out(
        "This file was generated by the sci-extract harvester. You are the agent "
        "that will write the analysis. Follow the steps below, then delete nothing."
    )
    out("")
    out("## Inputs")
    out("")
    out(f"- **Paper:** {title}")
    if meta.doi:
        out(f"- **DOI:** {meta.doi}")
    out(f"- **Source capture:** `./{RAW_NAME}` (read this first, in full)")
    out(f"- **Merged metadata:** `./{METADATA_NAME}`")
    if body_words:
        out(f"- **Full text available:** yes, {body_words} words of body text")
    else:
        out(
            "- **Full text available:** no. Only metadata and the abstract were "
            "retrievable, so scope the analysis to what the abstract supports and "
            "say plainly which questions cannot be answered from it."
        )
    out(f"- **Capture status:** {extraction_status(doc, figure_report)}")
    if figure_report and figure_report.method == "pdf-embedded":
        out(
            "  - Figures were cropped from the PDF and their captions are matched "
            "by order, so verify a figure really shows what its caption claims "
            "before citing it."
        )
    out(f"- **Detected paper type:** {paper_type}")
    out("")

    out("## Output")
    out("")
    out(f"Write your analysis to `./{ANALYSIS_NAME}` in this same directory.")
    out("")
    out("- Write in Chinese. Keep technical terms, proper nouns and math in English.")
    out(
        "- Do not use em-dashes or en-dashes anywhere. Use commas, semicolons, "
        "parentheses, or new sentences instead."
    )
    out(
        "- For display math use `\\left` and `\\right` for brackets, keep inline "
        "math on one line, and define every symbol you introduce."
    )
    out(
        f"- Reference figures by their relative path from `{RAW_NAME}` when a figure "
        "carries an argument, for example `![Fig. 1](figures/01-fig-1.jpg)`."
    )
    out("")

    if paper_type == "review":
        out("## Template: Review Literature Extraction Mode")
        out("")
        out("Produce these eleven labeled sections, in order:")
        out("")
        for index, heading in enumerate(_REVIEW_SECTIONS, start=1):
            out(f"{index}. {heading}")
    else:
        out("## Template: modified Heilmeier questions")
        out("")
        out("Answer these seven questions as labeled `##` subsections, in order:")
        out("")
        for index, question in enumerate(_RESEARCH_QUESTIONS, start=1):
            out(f"{index}. {question}")
        out("")
        out(
            "Questions 1 and 3 are strictly descriptive: no personal evaluation and "
            "no first-person markers. Questions 4, 5 and 6 are where your judgment "
            "belongs."
        )
    out("")

    out("## Rules")
    out("")
    out(
        "- Every personal judgment, in the sections that allow one, must carry a "
        "first-person marker such as \"In my opinion,\" or \"My analysis is that,\" "
        "so paper content stays distinguishable from your analysis."
    )
    out(
        "- Every external citation must come from a search you actually ran in this "
        "turn. No citations from memory. Repeating what the paper itself says about "
        "a work it cites is the one exception."
    )
    out("- Do not invent numbers, baselines, or results that are not in the paper.")
    out("- Do not add a summary section before the template. The template is the summary.")
    out("- Keep it tight. Do not repeat the same point under several headings.")
    out("")
    reference = skill_md if skill_md else Path("SKILL.md")
    out(
        f"The authoritative version of this template, including the per-question "
        f"rules on opinions and citations, is in `{reference}`. Consult it if any "
        "instruction above is ambiguous."
    )
    out("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_xml(path: Path, fulltext: FullText) -> Path | None:
    """Save the publisher XML exactly as received.

    Only genuine publisher XML is written. When no source returned any, no file
    is produced: a document synthesized out of metadata fields would look like
    publisher XML while carrying none of its content.
    """
    if not fulltext.found or not fulltext.xml:
        return None
    path.write_text(fulltext.xml, encoding="utf-8")
    return path


def render_all(
    directory: Path,
    meta: PaperMetadata,
    doc: Document | None,
    fulltext: FullText,
    figure_report: FigureReport | None,
    *,
    pdf_path: Path | None = None,
    skill_md: Path | None = None,
    include_raw_metadata: bool = False,
) -> RenderResult:
    """Write every output file for one paper into `directory`."""
    directory.mkdir(parents=True, exist_ok=True)
    result = RenderResult(directory=directory, pdf=pdf_path)

    result.raw = write_raw(directory / RAW_NAME, meta, doc, fulltext, figure_report)
    result.metadata = write_metadata(
        directory / METADATA_NAME,
        meta,
        doc,
        fulltext,
        figure_report,
        include_raw=include_raw_metadata,
    )
    result.xml = write_xml(directory / XML_NAME, fulltext)
    result.prompt = write_prompt(
        directory / PROMPT_NAME,
        meta,
        doc,
        classify_paper_type(meta, doc),
        figure_report=figure_report,
        skill_md=skill_md,
    )
    result.stale_analysis = (directory / ANALYSIS_NAME).exists()
    return result
