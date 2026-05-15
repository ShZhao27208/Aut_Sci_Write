from __future__ import annotations

import argparse
from pathlib import Path

from .parser import parse_deck
from .renderer import render_deck


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sci-html", description="Generate academic HTML slide decks.")
    subparsers = parser.add_subparsers(dest="command")
    generate = subparsers.add_parser("generate", help="Generate an HTML deck from Markdown, outline text, or JSON.")
    generate.add_argument("input", help="Input Markdown, structured outline, or JSON deck file.")
    generate.add_argument("-o", "--output", default="html-deck", help="Output directory or HTML file.")
    generate.add_argument("--theme", default="", help="Theme name, such as academic-blue or journal-dark.")
    generate.add_argument("--single-file", action="store_true", help=argparse.SUPPRESS)
    generate.add_argument("--title", default="", help="Override deck title.")
    generate.add_argument("--author", default="", help="Override author/presenter.")
    paper = subparsers.add_parser("paper", help="Generate an HTML deck directly from a PDF paper.")
    paper.add_argument("input", help="Input PDF paper.")
    paper.add_argument("-o", "--output", default="paper-html-deck", help="Output deck directory.")
    paper.add_argument("--theme", default="academic-blue", help="Theme name, such as academic-blue or journal-dark.")
    paper.add_argument("--title", default="", help="Override paper/deck title.")
    paper.add_argument("--author", default="", help="Override presenter.")
    paper.add_argument("--affiliation", default="Literature Report", help="Presenter affiliation or report type.")
    paper.add_argument("--date", default="", help="Report date, defaults to today.")
    paper.add_argument("--dpi", type=int, default=300, help="Figure extraction DPI.")
    paper.add_argument("--max-figures", type=int, default=6, help="Maximum number of extracted figures to include.")
    paper.add_argument("--paper-type", choices=["auto", "research", "review"], default="auto", help="Paper type routing for insight extraction.")
    paper.add_argument("--no-figures", action="store_true", help="Skip figure extraction.")
    paper.add_argument("--verbose", action="store_true", help="Verbose extraction output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "generate":
        deck = parse_deck(Path(args.input))
        if args.title:
            deck.title = args.title
        if args.author:
            deck.author = args.author
        if args.theme:
            deck.theme = args.theme
        if args.single_file:
            print("Note: --single-file is no longer supported and was ignored; sci-html always writes a deck directory.")
        output = Path(args.output)
        if output.suffix.lower() == ".html":
            output = output.with_suffix("")
            print(f"Note: HTML file output was converted to deck directory: {output}")
        result = render_deck(deck, output, single_file=False)
        print(f"Generated HTML deck: {result}")
        print("Controls: click/Right/Space next, Left previous, Home/End, F fullscreen.")
        return 0
    if args.command == "paper":
        from .paper_pipeline import generate_paper_deck

        result = generate_paper_deck(
            Path(args.input),
            Path(args.output),
            theme=args.theme,
            author=args.author,
            affiliation=args.affiliation,
            report_date=args.date,
            title=args.title,
            dpi=args.dpi,
            max_figures=args.max_figures,
            extract_figures=not args.no_figures,
            paper_type=args.paper_type,
            verbose=args.verbose,
        )
        print(f"Generated paper HTML deck: {result['html']}")
        print(f"Structured insights: {result['structured_insights']}")
        print(f"Figure manifest: {result['figure_manifest']}")
        if result.get("figure_error"):
            print(f"Figure extraction warning: {result['figure_error']}")
        print("Controls: click/Right/Space next, Left previous, Home/End, F fullscreen.")
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
