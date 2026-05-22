from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .integrations.extract.core_insights import CoreInsightsExtractor
from .models import Deck
from .parser import parse_deck
from .renderer import render_deck


def generate_paper_deck(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    theme: str = "academic-blue",
    author: str = "",
    affiliation: str = "Literature Report",
    report_date: str = "",
    title: str = "",
    dpi: int = 300,
    max_figures: int = 6,
    extract_figures: bool = True,
    paper_type: str = "auto",
    verbose: bool = False,
) -> dict[str, Any]:
    """Run the integrated PDF -> insights -> figures -> HTML deck workflow."""
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf}")
    if pdf.suffix.lower() != ".pdf":
        raise ValueError(f"Input must be a PDF file: {pdf}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    figures_dir = out / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    extractor = CoreInsightsExtractor(verbose=verbose)
    insights = extractor.extract_from_pdf(str(pdf), paper_type=paper_type)
    if title:
        insights.setdefault("metadata", {})["title"] = title
    (out / "structured_insights.json").write_text(
        json.dumps(insights, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    figure_manifest: list[dict[str, Any]] = []
    figure_error = ""
    if extract_figures:
        try:
            figure_manifest = extract_paper_figures(pdf, figures_dir, dpi=dpi, max_figures=max_figures)
            for fig in figure_manifest:
                fig["image_path"] = _relative_image(fig.get("image_path", ""), out)
        except Exception as exc:  # Figure extraction should not block deck creation.
            figure_error = f"{type(exc).__name__}: {exc}"
    (out / "figure_manifest.json").write_text(
        json.dumps({"figures": figure_manifest, "error": figure_error}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    markdown = build_paper_deck_markdown(
        insights,
        figure_manifest,
        theme=theme,
        author=author,
        affiliation=affiliation,
        report_date=report_date or date.today().isoformat(),
        source_pdf=pdf,
        base_dir=out,
    )
    deck_md = out / f"{pdf.stem}-deck.md"
    deck_md.write_text(markdown, encoding="utf-8")
    deck: Deck = parse_deck(deck_md)
    if theme:
        deck.theme = theme
    html = render_deck(deck, out)
    return {
        "html": str(html),
        "deck_markdown": str(deck_md),
        "structured_insights": str(out / "structured_insights.json"),
        "figure_manifest": str(out / "figure_manifest.json"),
        "figures_dir": str(figures_dir),
        "figure_error": figure_error,
    }


def extract_paper_figures(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 300,
    max_figures: int = 6,
) -> list[dict[str, Any]]:
    """Extract detected figures using the installed sci-figure package (v2)."""
    from sci_figure.figure_extractor import FigureExtractor
    from sci_figure.image_processor import ImageProcessor

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    with FigureExtractor(str(pdf_path), dpi=dpi) as extractor:
        figures = extractor.detect_all()
        processor = ImageProcessor(output_dir=str(output), fmt="png")
        manifest: list[dict[str, Any]] = []
        for fig in figures[:max_figures]:
            image_path = processor.save_figure(fig["image"], fig["number"])
            manifest.append({
                "number": fig.get("number"),
                "page": fig.get("page"),
                "caption": fig.get("caption_text", ""),
                "image_path": image_path,
                "figure_type": fig.get("figure_type", "figure"),
                "sublabels": fig.get("sublabels", []),
            })
        return manifest


def build_paper_deck_markdown(
    insights: dict[str, Any],
    figures: list[dict[str, Any]],
    *,
    theme: str,
    author: str,
    affiliation: str,
    report_date: str,
    source_pdf: str | Path,
    base_dir: str | Path,
) -> str:
    """Convert structured insights and figure metadata into sci-html Markdown."""
    if insights.get("paper_type") == "review":
        return _build_review_paper_deck_markdown(
            insights,
            figures,
            theme=theme,
            author=author,
            affiliation=affiliation,
            report_date=report_date,
            source_pdf=source_pdf,
            base_dir=base_dir,
        )

    meta = insights.get("metadata", {})
    core = insights.get("core_insights", {})
    title = _clean(meta.get("title")) or Path(source_pdf).stem
    authors = _join(meta.get("authors")) or "Unknown"
    journal = _clean(meta.get("journal")) or "Unknown"
    year = _clean(meta.get("year")) or "Unknown"
    doi = _clean(meta.get("doi")) or "N/A"

    lines = [
        "---",
        f"title: {title}",
        f"author: {author}",
        f"affiliation: {affiliation}",
        f"date: {report_date}",
        f"theme: {theme}",
        "---",
        "",
        "# Paper Snapshot",
        "",
        f"- **Title**: {title}.",
        f"- **Authors**: {authors}.",
        f"- **Source**: {journal}, {year}.",
        f"- **DOI**: {doi}.",
        f"- **Paper Type**: {insights.get('paper_type', 'research')}.",
        "",
        "---",
        "layout: section",
        "subtitle: 01",
        "",
        "# Research Context",
        "",
        "---",
        "",
        "# Research Problem",
        "",
        *_bullets(core.get("research_problem"), fallback="The extraction engine did not find a clear research-problem statement."),
        "",
        "---",
        "",
        "# Method and Core Idea",
        "",
        *_bullets(core.get("methodology"), fallback="The extraction engine did not find a clear method statement."),
        "",
        "---",
        "layout: section",
        "subtitle: 02",
        "",
        "# Findings and Contribution",
        "",
        "---",
        "",
        "# Key Results",
        "",
        *_bullets(core.get("key_results"), fallback="The extraction engine did not find explicit result statements."),
        "",
        "---",
        "",
        "# Innovation",
        "",
        *_bullets(core.get("innovation"), fallback="The extraction engine did not find explicit innovation statements."),
        "",
    ]

    if figures:
        lines.extend([
            "---",
            "layout: section",
            "subtitle: 03",
            "",
            "# Key Figures",
            "",
        ])
        for fig in figures:
            image = _relative_image(fig.get("image_path", ""), base_dir)
            caption = _shorten(_clean(fig.get("caption")), 220)
            number = fig.get("number", "")
            lines.extend([
                "---",
                "",
                f"# Figure {number}",
                "",
                f"- **Role**: Visual evidence extracted from the source paper.",
                f"- **Page**: {fig.get('page', 'Unknown')}.",
                f"- **Caption**: {caption or 'Caption unavailable.'}",
                "",
                f"![Figure {number}]({image})",
                "",
            ])

    lines.extend([
        "---",
        "layout: section",
        "subtitle: 04",
        "",
        "# Applications and Limits",
        "",
        "---",
        "",
        "# Applications",
        "",
        *_bullets(core.get("application"), fallback="The extraction engine did not find explicit application statements."),
        "",
        "---",
        "",
        "# Limitations",
        "",
        *_bullets(core.get("limitations"), fallback="The extraction engine did not find explicit limitation statements."),
        "",
        "---",
        "",
        "# Take-Home Message",
        "",
        f"- This deck was generated by **sci-html** from `{Path(source_pdf).name}`.",
        "- The workflow integrates **paper insight extraction**, **figure extraction**, and **HTML slide rendering**.",
        "- Manually review extracted claims before using the deck in a formal presentation.",
    ])
    return "\n".join(lines).strip() + "\n"


def _build_review_paper_deck_markdown(
    insights: dict[str, Any],
    figures: list[dict[str, Any]],
    *,
    theme: str,
    author: str,
    affiliation: str,
    report_date: str,
    source_pdf: str | Path,
    base_dir: str | Path,
) -> str:
    """Build a deck optimized for review, survey, and meta-analysis papers."""
    meta = insights.get("metadata", {})
    core = insights.get("core_insights", {})
    title = _clean(meta.get("title")) or Path(source_pdf).stem
    authors = _join(meta.get("authors")) or "Unknown"
    journal = _clean(meta.get("journal")) or "Unknown"
    year = _clean(meta.get("year")) or "Unknown"
    doi = _clean(meta.get("doi")) or "N/A"
    review_type = _clean(core.get("review_type")) or "Review literature"

    lines = [
        "---",
        f"title: {title}",
        f"author: {author}",
        f"affiliation: {affiliation}",
        f"date: {report_date}",
        f"theme: {theme}",
        "---",
        "",
        "# Paper Snapshot",
        "",
        f"- **Title**: {title}.",
        f"- **Authors**: {authors}.",
        f"- **Source**: {journal}, {year}.",
        f"- **DOI**: {doi}.",
        f"- **Paper Type**: {review_type}.",
        "",
        "---",
        "layout: section",
        "subtitle: 01",
        "",
        "# Review Map",
        "",
        "---",
        "",
        "# Review Scope",
        "",
        *_bullets(core.get("review_scope"), fallback="The extraction engine did not find a clear review-scope statement."),
        "",
        "---",
        "",
        "# Taxonomy and Themes",
        "",
        *_bullets(
            _merge_values(core.get("taxonomy"), core.get("major_themes")),
            fallback="The extraction engine did not find a clear taxonomy or theme structure.",
        ),
        "",
        "---",
        "layout: section",
        "subtitle: 02",
        "",
        "# Evidence and Debate",
        "",
        "---",
        "",
        "# Evidence Base",
        "",
        *_bullets(core.get("literature_selection"), fallback="The extraction engine did not find explicit literature-selection details."),
        "",
        "---",
        "",
        "# Consensus and Controversies",
        "",
        *_bullets(
            _merge_values(core.get("consensus_findings"), core.get("controversies")),
            fallback="The extraction engine did not find clear consensus or controversy statements.",
        ),
        "",
        "---",
        "",
        "# Evidence Quality",
        "",
        *_bullets(core.get("evidence_quality"), fallback="The extraction engine did not find explicit evidence-quality statements."),
        "",
        "---",
        "layout: section",
        "subtitle: 03",
        "",
        "# Gaps and Future Work",
        "",
        "---",
        "",
        "# Research Gaps",
        "",
        *_bullets(core.get("research_gaps"), fallback="The extraction engine did not find explicit research gaps."),
        "",
        "---",
        "",
        "# Future Directions",
        "",
        *_bullets(core.get("future_directions"), fallback="The extraction engine did not find explicit future directions."),
        "",
    ]

    important_tables = _as_list(core.get("key_tables_figures"))
    if important_tables or figures:
        lines.extend([
            "---",
            "layout: section",
            "subtitle: 04",
            "",
            "# Important Figures and Tables",
            "",
        ])
    if important_tables:
        lines.extend([
            "---",
            "",
            "# Key Tables and Figures",
            "",
            *_bullets(important_tables, fallback="No organizing figures or tables were identified."),
            "",
        ])
    for fig in figures:
        image = _relative_image(fig.get("image_path", ""), base_dir)
        caption = _shorten(_clean(fig.get("caption")), 220)
        number = fig.get("number", "")
        lines.extend([
            "---",
            "",
            f"# Figure {number}",
            "",
            "- **Role**: Visual evidence extracted from the source review.",
            f"- **Page**: {fig.get('page', 'Unknown')}.",
            f"- **Caption**: {caption or 'Caption unavailable.'}",
            "",
            f"![Figure {number}]({image})",
            "",
        ])

    lines.extend([
        "---",
        "",
        "# Bottom-Line Takeaways",
        "",
        *_bullets(
            _merge_values(core.get("consensus_findings"), core.get("research_gaps"), core.get("future_directions")),
            fallback="Manually review the extracted map before using it in a formal presentation.",
            limit=4,
        ),
        "",
        "---",
        "",
        "# Take-Home Message",
        "",
        f"- This deck was generated by **sci-html** from `{Path(source_pdf).name}`.",
        "- The workflow detected review-literature structure and organized the deck around scope, taxonomy, evidence, controversy, and gaps.",
        "- Manually review extracted claims before using the deck in a formal presentation.",
    ])
    return "\n".join(lines).strip() + "\n"


def _bullets(value: Any, *, fallback: str, limit: int = 5) -> list[str]:
    items = _as_list(value)
    if not items:
        items = [fallback]
    return [f"- {_emphasize(_shorten(item, 260))}" for item in items[:limit]]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]
    result = []
    for item in raw_items:
        cleaned = _clean(item)
        if cleaned and cleaned.lower() != "not found":
            result.append(cleaned)
    return result


def _merge_values(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        merged.extend(_as_list(value))
    return merged


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _join(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_clean(item) for item in value if _clean(item))
    return _clean(value)


def _shorten(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "..."


def _relative_image(image_path: str, base_dir: str | Path) -> str:
    path = Path(image_path)
    try:
        return path.relative_to(Path(base_dir)).as_posix()
    except ValueError:
        return path.as_posix()


def _emphasize(text: str) -> str:
    keywords = [
        "problem",
        "method",
        "result",
        "innovation",
        "application",
        "limitation",
        "challenge",
        "efficiency",
        "performance",
        "mechanism",
    ]
    lower = text.lower()
    for keyword in keywords:
        index = lower.find(keyword)
        if index >= 0:
            return text[:index] + "**" + text[index : index + len(keyword)] + "**" + text[index + len(keyword) :]
    return text
