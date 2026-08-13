#!/usr/bin/env python3
"""Harvest a paper into an agent-readable directory.

Given a DOI, PMID, PMCID, arXiv ID, exact title, or search query, this collects
complete metadata from every configured database, the native publisher XML, the
full text, and the figures, then writes:

    {year}_{author}_{short-title}/
        raw.md                verbatim capture, figures embedded inline
        analysis.md           written by the host agent, not by this script
        metadata.json         merged record plus a harvest audit trail
        fulltext.xml          publisher XML exactly as received
        figures/              publication-resolution images
        paper.pdf             kept alongside the markdown
        _analysis_prompt.md   instructions for producing analysis.md

The analysis step is deliberately not performed here. Whichever agent runs this
skill writes `analysis.md` by following `_analysis_prompt.md`, so no separate LLM
endpoint or API key is involved.

Usage:
    python3 harvest_paper.py 10.1038/s41586-020-2649-2
    python3 harvest_paper.py PMC7759461 --output-dir ./papers
    python3 harvest_paper.py "array programming with numpy" --pick 1
    python3 harvest_paper.py --batch dois.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from harvester import env, figures, fulltext, identify, jats, metadata, render

DEFAULT_OUTPUT_DIR = "sci_extract_out"
SKILL_MD = Path(__file__).resolve().parent / "SKILL.md"
# Below this share of matching title words, an unattended pick gets a warning.
TITLE_MATCH_FLOOR = 0.6


@dataclass
class HarvestOutcome:
    """What one paper's harvest produced."""

    query: str
    directory: Path | None = None
    title: str = ""
    doi: str = ""
    figures_saved: int = 0
    figure_method: str = ""
    body_words: int = 0
    fulltext_source: str = ""
    has_xml: bool = False
    has_pdf: bool = False
    stale_analysis: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.directory is not None and not self.error


def harvest(
    raw_input: str,
    output_root: Path,
    *,
    pick: int | None = None,
    limit: int = 10,
    skip_pdf: bool = False,
    skip_figures: bool = False,
    include_raw_metadata: bool = False,
    assume_yes: bool = False,
    verbose: bool = False,
) -> HarvestOutcome:
    """Harvest one paper. Returns an outcome rather than raising."""
    outcome = HarvestOutcome(query=raw_input)
    ref = identify.classify(raw_input)

    if verbose:
        print(f"[input] {ref.label()}", flush=True)

    if ref.is_searchable:
        resolved = _resolve_by_search(
            ref, limit=limit, pick=pick, assume_yes=assume_yes, verbose=verbose
        )
        if resolved is None:
            outcome.error = "no match selected"
            return outcome
        ref = resolved

    if verbose:
        print("[metadata] querying databases", flush=True)
    meta = metadata.collect(ref, verbose=verbose)
    if not meta.title and not meta.doi:
        outcome.error = "no database returned a record for this identifier"
        return outcome
    outcome.title = meta.title
    outcome.doi = meta.doi

    if verbose:
        print("[fulltext] looking for open access XML", flush=True)
    text = fulltext.retrieve(meta, verbose=verbose)
    outcome.fulltext_source = text.source

    doc = None
    if text.found and text.xml:
        doc = jats.parse(text.xml, text.format)
        outcome.body_words = doc.body_word_count()
        if verbose:
            print(
                f"[parse] {doc.body_word_count()} body words, "
                f"{len(doc.figures)} figures, {len(doc.references)} references",
                flush=True,
            )

    directory = output_root / render.paper_dirname(meta)
    directory.mkdir(parents=True, exist_ok=True)

    pdf_path: Path | None = None
    if not skip_pdf:
        for pdf_url in fulltext.resolve_pdf_urls(meta):
            pdf_path = figures.download_pdf(pdf_url, directory / render.PDF_NAME)
            if verbose:
                print(
                    f"[pdf] {'saved' if pdf_path else 'unavailable'}: {pdf_url}",
                    flush=True,
                )
            if pdf_path:
                break

    report = None
    if doc is not None and not skip_figures:
        report = figures.download(
            doc,
            meta,
            directory / "figures",
            pdf_path=pdf_path,
            verbose=verbose,
        )
        outcome.figures_saved = report.count
        outcome.figure_method = report.method
    elif skip_figures:
        # Say so explicitly. Left as None, the capture would report "no figures"
        # and read as though the images had been unavailable.
        report = figures.FigureReport(method="skipped")

    result = render.render_all(
        directory,
        meta,
        doc,
        text,
        report,
        pdf_path=pdf_path,
        skill_md=SKILL_MD,
        include_raw_metadata=include_raw_metadata,
    )
    outcome.directory = directory
    outcome.has_xml = result.xml is not None
    outcome.has_pdf = pdf_path is not None
    outcome.stale_analysis = result.stale_analysis
    return outcome


def _resolve_by_search(
    ref: identify.PaperRef,
    *,
    limit: int,
    pick: int | None,
    assume_yes: bool,
    verbose: bool,
) -> identify.PaperRef | None:
    """Turn a title or query into a concrete identifier, confirming the choice."""
    exact = ref.kind == "title"
    results = metadata.search(ref.value, limit=limit, exact_title=exact)
    if not results:
        print(f"No results for: {ref.value}", file=sys.stderr)
        return None

    if pick is not None:
        if not 1 <= pick <= len(results):
            print(
                f"--pick {pick} is out of range; {len(results)} results found",
                file=sys.stderr,
            )
            return None
        chosen = results[pick - 1]
    elif assume_yes or len(results) == 1:
        chosen = results[0]
        if not assume_yes:
            print(f"Single match: {_describe(chosen)}")
    else:
        _print_candidates(results)
        chosen = _prompt_for_choice(results)
        if chosen is None:
            return None

    if verbose:
        print(f"[selected] {_describe(chosen)}", flush=True)
    if assume_yes and pick is None and ref.kind == "title":
        # An unattended run took the top hit without anyone seeing the list, so a
        # title that only partly matches has to be surfaced rather than assumed
        # correct.
        overlap = _title_overlap(ref.value, chosen.get("title") or "")
        if overlap < TITLE_MATCH_FLOOR:
            print(
                f"WARNING {ref.value!r}\n"
                f"        auto-selected {chosen.get('title') or '(untitled)'!r}\n"
                f"        only {overlap:.0%} of the requested title's words match; "
                "verify this is the intended paper.",
                file=sys.stderr,
            )
    return identify.classify(chosen.get("doi") or chosen.get("title") or ref.value)


def _title_overlap(requested: str, chosen: str) -> float:
    """Share of the requested title's words that appear in the chosen title."""
    want = set(re.findall(r"[a-z0-9]+", requested.lower()))
    got = set(re.findall(r"[a-z0-9]+", chosen.lower()))
    if not want:
        return 1.0
    return len(want & got) / len(want)


def _print_candidates(results: list[dict]) -> None:
    print(f"\n{len(results)} candidates:\n")
    for index, item in enumerate(results, start=1):
        print(f"  [{index}] {_describe(item)}")
    print()


def _describe(item: dict) -> str:
    bits = [item.get("title") or "Untitled"]
    meta_bits = [
        str(item.get(key))
        for key in ("first_author", "year", "journal")
        if item.get(key)
    ]
    if meta_bits:
        bits.append(f"({', '.join(meta_bits)})")
    if item.get("citations"):
        bits.append(f"[{item['citations']} citations]")
    if item.get("doi"):
        bits.append(f"doi:{item['doi']}")
    return " ".join(bits)


def _prompt_for_choice(results: list[dict]) -> dict | None:
    """Ask which candidate to harvest. Non-interactive callers should use --pick."""
    if not sys.stdin.isatty():
        print(
            "Multiple candidates found and stdin is not interactive. "
            "Re-run with --pick N to choose one.",
            file=sys.stderr,
        )
        return None
    try:
        answer = input("Harvest which one? [number, or blank to cancel]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not answer:
        return None
    try:
        index = int(answer)
    except ValueError:
        print(f"Not a number: {answer}", file=sys.stderr)
        return None
    if not 1 <= index <= len(results):
        print(f"Out of range: {index}", file=sys.stderr)
        return None
    return results[index - 1]


def _read_batch(path: Path) -> list[str]:
    entries: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            entries.append(stripped)
    return entries


def _report(outcome: HarvestOutcome) -> None:
    if not outcome.ok:
        print(f"FAILED  {outcome.query}: {outcome.error}")
        return
    parts = [f"{outcome.body_words} body words" if outcome.body_words else "metadata only"]
    if outcome.figures_saved:
        parts.append(f"{outcome.figures_saved} figures ({outcome.figure_method})")
    if outcome.has_xml:
        parts.append(f"XML ({outcome.fulltext_source})")
    if outcome.has_pdf:
        parts.append("PDF")
    print(f"OK      {outcome.directory}")
    print(f"        {outcome.title[:88]}")
    print(f"        {', '.join(parts)}")
    if outcome.stale_analysis:
        print(
            f"        NOTE: {render.ANALYSIS_NAME} predates this run and may no "
            "longer match the capture; rewrite it."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Harvest complete paper metadata, XML, full text and figures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Accepts a DOI, PMID, PMCID, arXiv ID, exact title, or search query.\n"
            "Titles and queries list candidates and ask before harvesting; pass\n"
            "--pick N to choose non-interactively."
        ),
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="DOI, PMID, PMCID, arXiv ID, title, or search query",
    )
    parser.add_argument("--batch", metavar="FILE", help="File with one identifier per line")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output root, one subdirectory per paper (default: ./{DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--pick", type=int, metavar="N", help="Choose candidate N without prompting")
    parser.add_argument("--limit", type=int, default=10, help="Candidates to list for a query")
    parser.add_argument("--yes", action="store_true", help="Accept the top search result")
    parser.add_argument("--skip-pdf", action="store_true", help="Do not download the PDF")
    parser.add_argument("--skip-figures", action="store_true", help="Do not download figures")
    parser.add_argument(
        "--include-raw-metadata",
        action="store_true",
        help="Keep each database's unmerged response in metadata.json",
    )
    parser.add_argument("--sources", action="store_true", help="List configured sources and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose progress output")
    args = parser.parse_args()

    if args.sources:
        return _show_sources()

    if not args.query and not args.batch:
        parser.error("provide an identifier, --batch FILE, or --sources")

    queries = _read_batch(Path(args.batch)) if args.batch else [args.query]
    if args.batch and not queries:
        print(f"No identifiers found in {args.batch}", file=sys.stderr)
        return 1

    output_root = Path(args.output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    outcomes: list[HarvestOutcome] = []
    for index, query in enumerate(queries, start=1):
        if len(queries) > 1:
            print(f"\n=== [{index}/{len(queries)}] {query} ===")
        outcomes.append(
            harvest(
                query,
                output_root,
                pick=args.pick,
                limit=args.limit,
                skip_pdf=args.skip_pdf,
                skip_figures=args.skip_figures,
                include_raw_metadata=args.include_raw_metadata,
                # A batch run cannot stop to ask about every ambiguous title.
                assume_yes=args.yes or len(queries) > 1,
                verbose=args.verbose,
            )
        )

    print()
    for outcome in outcomes:
        _report(outcome)

    succeeded = [o for o in outcomes if o.ok]
    if len(queries) > 1:
        print(f"\n{len(succeeded)}/{len(outcomes)} harvested into {output_root}")
    if succeeded:
        print(
            f"\nNext: read each {render.PROMPT_NAME} and write {render.ANALYSIS_NAME} "
            "in that directory."
        )
    return 0 if succeeded else 1


def _show_sources() -> int:
    available = env.available_sources()
    print("Metadata and full text sources:\n")
    for name, ready in sorted(available.items()):
        keyless = name in env.KEYLESS_SOURCES
        if ready:
            status = "ready (no key needed)" if keyless else "ready"
        else:
            needed = ", ".join(env.SOURCE_CREDENTIALS.get(name, ()))
            status = f"not configured (set {needed})" if needed else "unavailable"
        print(f"  {name:18} {status}")
    print(f"\nCredentials are read from {env.env_file_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
