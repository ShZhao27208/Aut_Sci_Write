"""
CLI for sci-figure v2.0.

Usage:
    sh-sci-fig paper.pdf --list
    sh-sci-fig paper.pdf -f 2
    sh-sci-fig paper.pdf -f 2 -s c
    sh-sci-fig paper.pdf --all
    sh-sci-fig paper.pdf --render-page 3
    sh-sci-fig paper.pdf -f 2 --bbox "120,85,1650,980" --page 3
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import traceback

from sci_figure.figure_extractor import FigureExtractor
from sci_figure.subfigure_splitter import SubfigureSplitter
from sci_figure.image_processor import ImageProcessor
from sci_figure.annotator import PageAnnotator
from sci_figure.pdf_parser import PDFParser
from sci_figure.utils import setup_logger, validate_pdf_path


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(
        prog="sh-sci-fig",
        description="Extract figures from academic PDFs (v2.0 — CV engine)",
    )
    p.add_argument("input", help="PDF file path")

    # Extraction
    g1 = p.add_argument_group("extraction")
    g1.add_argument("-f", "--figure", type=int, help="Figure number to extract")
    g1.add_argument("-s", "--subfigure", help="Sub-figure label (a, b, c...)")
    g1.add_argument("--all", action="store_true", dest="extract_all", help="Extract all figures")
    g1.add_argument("-l", "--list", action="store_true", help="List available figures")

    # Strategy
    g2 = p.add_argument_group("strategy")
    g2.add_argument(
        "--strategy", choices=["hybrid", "native", "cv"], default="hybrid",
        help="Detection strategy (default: hybrid)"
    )
    g2.add_argument("--bbox", help="Manual crop: \"x0,y0,x1,y1\" in pixels")
    g2.add_argument("--page", type=int, help="Page number for --bbox (0-indexed)")

    # Output
    g3 = p.add_argument_group("output")
    g3.add_argument("-o", "--output", default=".", help="Output directory")
    g3.add_argument("-d", "--dpi", type=int, default=600, help="Resolution (default: 600)")
    g3.add_argument("--format", default="png", choices=["png", "jpg", "jpeg"])
    g3.add_argument("--no-trim", action="store_true", help="Disable whitespace trimming")

    # Verification
    g4 = p.add_argument_group("verification")
    g4.add_argument("--render-page", type=int, metavar="NUM", help="Output annotated page render")
    g4.add_argument("--annotate", action="store_true", help="Add detection boxes to output")

    # OCR
    g5 = p.add_argument_group("ocr")
    g5.add_argument(
        "--ocr", choices=["tesseract", "easyocr", "none"], default="tesseract",
        help="OCR engine for subfigure labels (default: tesseract)"
    )

    # Misc
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--debug", action="store_true", help="Verbose debug output")

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    level = logging.DEBUG if args.debug else (logging.WARNING if args.quiet else logging.INFO)
    setup_logger(level=level)
    logger = logging.getLogger("sci_figure")

    # Validate input
    try:
        pdf_path = validate_pdf_path(args.input)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        return 1

    if args.dpi < 72 or args.dpi > 2400:
        logger.error(f"DPI must be 72-2400, got {args.dpi}")
        return 1

    os.makedirs(args.output, exist_ok=True)

    try:
        # Manual bbox extraction
        if args.bbox:
            return _handle_bbox(args, pdf_path, logger)

        # Render page (multimodal verification)
        if args.render_page is not None:
            return _handle_render_page(args, pdf_path, logger)

        # Standard extraction
        with FigureExtractor(pdf_path, dpi=args.dpi, strategy=args.strategy) as extractor:
            figures = extractor.detect_all()

            if args.list:
                return _handle_list(figures, logger)

            if args.extract_all:
                return _handle_extract_all(args, figures, extractor, logger)

            if args.figure is None:
                logger.error("Specify -f/--figure, --list, --all, or --bbox.")
                return 1

            return _handle_single(args, figures, extractor, logger)

    except KeyboardInterrupt:
        logger.warning("Interrupted.")
        return 130
    except MemoryError:
        logger.error("Out of memory. Try lower DPI (-d 300).")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.debug:
            traceback.print_exc()
        return 1


def _handle_bbox(args, pdf_path, logger):
    """Manual bbox extraction for multimodal correction."""
    if args.page is None:
        logger.error("--bbox requires --page")
        return 1

    try:
        coords = [int(x.strip()) for x in args.bbox.split(",")]
        if len(coords) != 4:
            raise ValueError
    except ValueError:
        logger.error("--bbox format: \"x0,y0,x1,y1\" (integers)")
        return 1

    with PDFParser(pdf_path, dpi=args.dpi) as parser:
        page_img = parser.render_page(args.page)
        h, w = page_img.shape[:2]
        x0, y0, x1, y1 = coords
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)

        if x1 <= x0 or y1 <= y0:
            logger.error("Invalid bbox coordinates")
            return 1

        crop = page_img[y0:y1, x0:x1].copy()
        proc = ImageProcessor(output_dir=args.output, fmt=args.format)
        fig_num = args.figure or 0
        path = proc.save_figure(crop, fig_num)
        logger.info(f"Extracted: {path}")
    return 0


def _handle_render_page(args, pdf_path, logger):
    """Render page with detection annotations."""
    with FigureExtractor(pdf_path, dpi=args.dpi, strategy=args.strategy) as extractor:
        figures = extractor.detect_all()
        page_img = extractor._parser.render_page(args.render_page)

        page_figs = [f for f in figures if f["page"] == args.render_page]
        annotator = PageAnnotator()
        annotated = annotator.annotate_detections(page_img, page_figs)
        annotator.save(annotated, os.path.join(args.output, f"page_{args.render_page}_annotated.png"))
    return 0


def _handle_list(figures, logger):
    if not figures:
        logger.info("No figures detected.")
    else:
        logger.info(f"Found {len(figures)} figure(s):")
        for fig in figures:
            subs = fig.get("sublabels", [])
            suffix = f" (sub: {', '.join(subs)})" if subs else ""
            engine = fig.get("engine_used", "?")
            logger.info(f"  Figure {fig['number']} — page {fig['page']} [{engine}]{suffix}")
    return 0


def _handle_extract_all(args, figures, extractor, logger):
    if not figures:
        logger.warning("No figures to extract.")
        return 0

    proc = ImageProcessor(output_dir=args.output, fmt=args.format)
    count = 0
    for fig in figures:
        try:
            proc.save_figure(fig["image"], fig["number"])
            count += 1
        except Exception as e:
            logger.warning(f"Failed Figure {fig['number']}: {e}")

    logger.info(f"Extracted {count}/{len(figures)} figure(s).")
    return 0


def _handle_single(args, figures, extractor, logger):
    target = extractor.get_figure(args.figure)
    if target is None:
        available = [str(f["number"]) for f in figures]
        logger.error(
            f"Figure {args.figure} not found. "
            f"Available: {', '.join(available) or 'none'}"
        )
        return 1

    proc = ImageProcessor(output_dir=args.output, fmt=args.format)

    if args.subfigure:
        splitter = SubfigureSplitter(ocr_engine=args.ocr)
        subfigs = splitter.split(
            target["image"], target["sublabels"], target_label=args.subfigure
        )
        label = args.subfigure.lower()
        if label in subfigs:
            path = proc.save_subfigure(subfigs[label], args.figure, label)
        else:
            logger.warning(f"Sub-figure '{args.subfigure}' not found; saving full figure.")
            path = proc.save_figure(target["image"], args.figure)
    else:
        path = proc.save_figure(target["image"], args.figure)

    logger.info(f"Extracted: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
