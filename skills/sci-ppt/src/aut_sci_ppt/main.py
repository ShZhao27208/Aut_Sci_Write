"""Stable CLI wrapper for aut-sci-ppt."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .agent import PPTAgent
from .enhanced_agent import EnhancedPPTAgent
from .paper_workflow import auto_generate_ppt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aut-sci-ppt", description="Generate academic PPTX files.")
    subparsers = parser.add_subparsers(dest="command")

    generate = subparsers.add_parser("generate", help="Generate PPTX from a text or markdown file.")
    generate.add_argument("input", help="Input .txt/.md file.")
    generate.add_argument("-o", "--output", default="output.pptx", help="Output .pptx path.")
    generate.add_argument("--scene", default="default", help="Parser scene hint.")

    pdf = subparsers.add_parser("from-pdf", help="Generate PPTX from a PDF workflow.")
    pdf.add_argument("pdf", help="Input PDF path.")
    pdf.add_argument("-o", "--output", help="Output .pptx path.")
    pdf.add_argument("--author", default="", help="Presenter name.")
    pdf.add_argument("--advisor", default="", help="Advisor name.")
    pdf.add_argument("--date", default="", help="Presentation date.")
    pdf.add_argument("--direction", default="", help="Research direction.")
    pdf.add_argument("--translate", action="store_true", help="Translate extracted outline content to Chinese if MOONSHOT_API_KEY is configured.")

    enhanced = subparsers.add_parser("enhanced-from-pdf", help="Generate PPTX from PDF with academic parsing.")
    enhanced.add_argument("pdf", help="Input PDF path.")
    enhanced.add_argument("-o", "--output", default="output.pptx", help="Output .pptx path.")
    enhanced.add_argument("--no-formulas", action="store_true", help="Skip formula rendering.")

    subparsers.add_parser("interactive", help="Start the interactive workflow.")
    return parser


def run_generate(args: argparse.Namespace) -> str:
    input_path = Path(args.input)
    text = input_path.read_text(encoding="utf-8")
    return PPTAgent(scene=args.scene).generate(text, args.output)


def run_from_pdf(args: argparse.Namespace) -> str:
    return auto_generate_ppt(
        args.pdf,
        output_path=args.output,
        author=args.author,
        advisor=args.advisor,
        date=args.date,
        direction=args.direction,
        translate=args.translate,
    )


def run_enhanced_from_pdf(args: argparse.Namespace):
    return EnhancedPPTAgent().generate_from_pdf(
        args.pdf,
        args.output,
        enable_formula_rendering=not args.no_formulas,
    )


def run_interactive() -> None:
    print("aut-sci-ppt interactive mode")
    print("1. Generate from text input")
    print("2. Generate from PDF")
    print("3. Enhanced PDF mode")
    mode = input("Choose mode [1]: ").strip() or "1"

    if mode == "2":
        pdf_path = input("PDF path: ").strip().strip('"')
        if not os.path.exists(pdf_path):
            print(f"PDF not found: {pdf_path}")
            return
        output_path = input("Output .pptx path [auto]: ").strip() or None
        result = auto_generate_ppt(pdf_path, output_path=output_path)
        print(result)
        return

    if mode == "3":
        pdf_path = input("PDF path: ").strip().strip('"')
        if not os.path.exists(pdf_path):
            print(f"PDF not found: {pdf_path}")
            return
        output_path = input("Output .pptx path [output.pptx]: ").strip() or "output.pptx"
        render_formulas = (input("Render formulas? [Y/n]: ").strip().lower() != "n")
        result = EnhancedPPTAgent().generate_from_pdf(
            pdf_path,
            output_path,
            enable_formula_rendering=render_formulas,
        )
        print(result or "No PPT generated.")
        return

    print("Enter slide text. Type END on its own line to finish.")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    output_path = input("Output .pptx path [output.pptx]: ").strip() or "output.pptx"
    result = PPTAgent().generate("\n".join(lines), output_path)
    print(result)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            print(run_generate(args))
        elif args.command == "from-pdf":
            print(run_from_pdf(args))
        elif args.command == "enhanced-from-pdf":
            result = run_enhanced_from_pdf(args)
            print(result or "No PPT generated.")
        elif args.command == "interactive":
            run_interactive()
        else:
            parser.print_help()
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
