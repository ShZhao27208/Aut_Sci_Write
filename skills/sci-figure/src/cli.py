#!/usr/bin/env python
"""Package CLI for sci-figure."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import traceback

from .figure_detector import FigureDetector
from .image_processor import ImageProcessor
from .pdf_parser import PDFParser
from .subfigure_splitter import SubfigureSplitter
from .utils import check_dependencies, setup_logger, validate_pdf_path_bool


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="sh-sci-fig",
        description="Extract figures and sub-figures from academic PDF papers.",
    )
    parser.add_argument("input", help="Path to the PDF file")
    parser.add_argument("-f", "--figure", type=int, help="Figure number to extract")
    parser.add_argument("-s", "--subfigure", help="Sub-figure label to extract")
    parser.add_argument("-o", "--output", default=".", help="Output directory")
    parser.add_argument("-d", "--dpi", type=int, default=600, help="Output resolution in DPI")
    parser.add_argument("-l", "--list", action="store_true", help="List available figures")
    parser.add_argument("--all", action="store_true", dest="extract_all", help="Extract all figures")
    parser.add_argument("--format", default="png", choices=["png", "jpg", "jpeg"], help="Output image format")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress info messages")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logger = setup_logger(level=logging.WARNING if args.quiet else logging.INFO)

    dep_errors = check_dependencies()
    if dep_errors:
        for error in dep_errors:
            logger.error(error)
        return 1

    if not validate_pdf_path_bool(args.input):
        if not os.path.exists(args.input):
            logger.error("File not found: %s", args.input)
        elif not args.input.lower().endswith(".pdf"):
            logger.error("Not a PDF file: %s", args.input)
        else:
            logger.error("Invalid PDF file: %s", args.input)
        return 1

    if args.dpi < 72 or args.dpi > 2400:
        logger.error("DPI must be between 72 and 2400, got %s", args.dpi)
        return 1

    try:
        os.makedirs(args.output, exist_ok=True)
    except OSError as exc:
        logger.error("Cannot create output directory '%s': %s", args.output, exc)
        return 1

    pdf_parser = None
    try:
        pdf_parser = PDFParser(args.input, dpi=args.dpi)
        detector = FigureDetector(pdf_parser)
        figures = detector.detect_all_figures()

        if args.list:
            if not figures:
                logger.info("No figures detected in this PDF.")
            else:
                logger.info("Found %s figure(s):", len(figures))
                for fig in figures:
                    sublabels = fig.get("sublabels", [])
                    suffix = f" (sub-figures: {', '.join(sublabels)})" if sublabels else ""
                    logger.info("  Figure %s - page %s%s", fig["number"], fig["page"], suffix)
            return 0

        if args.extract_all:
            if not figures:
                logger.warning("No figures detected. Nothing to extract.")
                return 0
            processor = ImageProcessor(output_dir=args.output, fmt=args.format)
            count = 0
            for fig in figures:
                try:
                    logger.info("Extracted: %s", processor.save_figure(fig["image"], fig["number"]))
                    count += 1
                except Exception as exc:
                    logger.warning("Failed to save Figure %s: %s", fig["number"], exc)
            logger.info("Done. Extracted %s figure(s).", count)
            return 0

        if args.figure is None:
            logger.error("Specify -f/--figure, or use --list / --all.")
            return 1

        target = detector.get_figure(args.figure)
        if target is None:
            available = [str(fig["number"]) for fig in figures]
            logger.error(
                "Figure %s not found. Available figures: %s",
                args.figure,
                ", ".join(available) if available else "none detected",
            )
            return 1

        processor = ImageProcessor(output_dir=args.output, fmt=args.format)
        if args.subfigure:
            splitter = SubfigureSplitter(pdf_parser)
            subfig_image = splitter.extract_subfigure(target, args.subfigure)
            if subfig_image is None:
                logger.warning("Sub-figure '%s' not found; saving entire figure.", args.subfigure)
                output_path = processor.save_figure(target["image"], args.figure)
            else:
                output_path = processor.save_subfigure(subfig_image, args.figure, args.subfigure)
        else:
            output_path = processor.save_figure(target["image"], args.figure)
        logger.info("Extracted: %s", output_path)
        return 0
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return 130
    except MemoryError:
        logger.error("Out of memory. Try a lower DPI, for example -d 300.")
        return 1
    except Exception as exc:
        logger.error("Unexpected error: %s", exc)
        logger.error(traceback.format_exc())
        return 1
    finally:
        if pdf_parser is not None:
            pdf_parser.close()


if __name__ == "__main__":
    raise SystemExit(main())
