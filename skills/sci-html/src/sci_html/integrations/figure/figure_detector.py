#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Figure Detector Module

Responsibilities:
- Locate "Figure X" / "Fig. X" caption labels in extracted text
- Distinguish captions from in-text references
- Determine figure region boundaries on each page
- Crop figure images from rendered pages
- Validate figure dimensions and handle edge cases
"""

import re
import numpy as np
from .utils import get_logger
from .exceptions import FigureNotFoundError

logger = get_logger()

# Regex patterns for figure captions (line-start anchored)
# Matches: "Fig. 1.", "Fig. 1 ", "Figure 1.", "Figure 1 ", "FIGURE 1"
# Also matches Chinese labels through Unicode escapes.
# Updated to handle both "Fig." and "Figure" with flexible spacing
CAPTION_PATTERNS = [
    re.compile(r"^(Fig\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),  # Fig. or Fig
    re.compile(r"^(Figure\s+(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(
        r"^(FIGURE\s+(\d+))\s*[\.:\s]",
    ),
    re.compile(r"^(\u56fe\s*(\d+))\s*[\.:：、\s]"),
    # Scheme patterns (chemistry papers)
    re.compile(r"^(Scheme\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(\u65b9\u6848\s*(\d+))\s*[\.:：、\s]"),
    re.compile(r"^(\u793a\u610f\u56fe\s*(\d+))\s*[\.:：、\s]"),
    # Chart patterns
    re.compile(r"^(Chart\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    # Supplementary figure patterns
    re.compile(r"^(Supplementary\s+Fig(?:ure)?\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(Supp\.?\s+Fig\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(S\.?\s*Fig\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(Supplementary\s+Scheme\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(\u9644\u56fe\s*(\d+))\s*[\.:：、\s]"),
    re.compile(r"^(\u8865\u5145\u56fe\s*(\d+))\s*[\.:：、\s]"),
    # Extended Data (Nature journals)
    re.compile(r"^(Extended\s+Data\s+Fig(?:ure)?\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
]

# Maps pattern index to figure type
# (index corresponds to position in CAPTION_PATTERNS list)
FIGURE_TYPE_BY_PATTERN = {
    0: "figure",         # Fig.
    1: "figure",         # Figure
    2: "figure",         # FIGURE
    3: "figure",         # Chinese Figure
    4: "scheme",         # Scheme
    5: "scheme",         # Chinese Scheme
    6: "scheme",         # Chinese schematic
    7: "chart",          # Chart
    8: "supplementary",  # Supplementary Figure
    9: "supplementary",  # Supp. Fig.
    10: "supplementary", # S. Fig.
    11: "supplementary", # Supplementary Scheme
    12: "supplementary", # 闄勫浘
    13: "supplementary", # Chinese Supplementary Figure
    14: "extended_data", # Extended Data Figure
}

# Multiple sublabel patterns (in priority order)
SUBLABEL_PATTERNS = [
    re.compile(r"\(([a-z])\)"),           # (a), (b), (c) 鈥?original
    re.compile(r"\(([A-Z])\)"),           # (A), (B), (C) 鈥?uppercase
    re.compile(r"(?<!\w)([a-z])\)"),      # a), b), c) 鈥?no left paren
    re.compile(r"\((i{1,3}|iv|vi{0,3}|ix|xi{0,3})\)", re.IGNORECASE),  # (i), (ii), (iii)
    re.compile(r"\((\d+)\)"),             # (1), (2), (3) 鈥?numeric
    re.compile(r"(?<!\w)([a-z])\.(?=\s)", re.IGNORECASE),  # a. b. c. 鈥?dot format
]

# Minimum figure dimensions (in pixels) to consider valid
MIN_FIGURE_WIDTH_PX = 50
MIN_FIGURE_HEIGHT_PX = 50


def _detect_sublabel_format(label: str, caption_text: str) -> str:
    """Detect the format used for this sublabel in the caption."""
    patterns_and_formats = [
        (re.compile(rf"\({re.escape(label)}\)", re.IGNORECASE), f"({label})"),
        (re.compile(rf"{re.escape(label)}\)"), f"{label})"),
        (re.compile(rf"(?<!\w){re.escape(label)}\.(?=\s)", re.IGNORECASE), f"{label}."),
    ]
    for pattern, fmt in patterns_and_formats:
        if pattern.search(caption_text):
            return fmt
    return f"({label})"  # default


class FigureDetector:
    """Detect and locate figures in PDF pages using text label positions."""

    def __init__(self, pdf_parser):
        self.pdf_parser = pdf_parser
        self._figures = None  # lazy cache

    def detect_all_figures(self) -> list:
        """
        Scan entire PDF and return a list of detected figures.

        Algorithm:
        1. Extract text lines from every page
        2. Identify caption lines (starting with "Fig. N" / "Figure N")
        3. For each caption, determine the figure image region above it
        4. Render the page and crop the figure region

        Returns:
            list of dicts with keys:
                number, page, bbox, bbox_pdf, caption, caption_full,
                caption_bbox_pdf, sublabels, sublabel_details,
                figure_type, is_supplementary, image
        """
        if self._figures is not None:
            return self._figures

        raw_captions = self._find_all_captions()

        if not raw_captions:
            logger.warning("No figure captions detected in this PDF.")
            self._figures = []
            return self._figures

        logger.info(f"Found {len(raw_captions)} figure caption(s)")

        # Build figure regions
        figures = []
        # Group captions by page for boundary calculation
        page_captions = {}
        for cap in raw_captions:
            pg = cap["page"]
            if pg not in page_captions:
                page_captions[pg] = []
            page_captions[pg].append(cap)

        # Cache rendered pages to avoid re-rendering
        rendered_pages = {}

        for cap in raw_captions:
            page_num = cap["page"]

            # Get all text lines on this page for boundary detection
            try:
                all_lines = self.pdf_parser.extract_lines(page_num)
            except Exception as e:
                logger.warning(
                    f"Figure {cap['number']}: failed to extract text on "
                    f"page {page_num}: {e}. Skipping."
                )
                continue

            # Determine figure bounding box (in PDF coords)
            bbox_pdf = self._compute_figure_bbox(
                cap, all_lines, page_num, page_captions.get(page_num, [])
            )

            # Convert to pixel coords
            bbox_px = self.pdf_parser.pdf_to_pixel_coords(bbox_pdf)

            # Render page (cached)
            if page_num not in rendered_pages:
                try:
                    rendered_pages[page_num] = self.pdf_parser.render_page(page_num)
                except Exception as e:
                    logger.warning(
                        f"Figure {cap['number']}: failed to render "
                        f"page {page_num}: {e}. Skipping."
                    )
                    continue
            page_img = rendered_pages[page_num]

            # Crop figure image
            x0, y0, x1, y1 = bbox_px
            h, w = page_img.shape[:2]
            # Clamp to image bounds
            x0 = max(0, x0)
            y0 = max(0, y0)
            x1 = min(w, x1)
            y1 = min(h, y1)

            # Validate crop region
            if x1 <= x0 or y1 <= y0:
                logger.warning(
                    f"Figure {cap['number']}: invalid crop region "
                    f"({x0},{y0},{x1},{y1}), skipping"
                )
                continue

            crop_w = x1 - x0
            crop_h = y1 - y0

            if crop_w < MIN_FIGURE_WIDTH_PX or crop_h < MIN_FIGURE_HEIGHT_PX:
                logger.warning(
                    f"Figure {cap['number']}: crop too small "
                    f"({crop_w}x{crop_h} px), skipping"
                )
                continue

            fig_image = page_img[y0:y1, x0:x1].copy()

            # Detect sub-figure labels from caption text
            sublabels = self._extract_sublabels(cap["caption"])
            figure_type = cap.get("figure_type", "figure")

            figures.append(
                {
                    "number": cap["number"],
                    "page": page_num,
                    "bbox": bbox_px,
                    "bbox_pdf": bbox_pdf,
                    "caption": cap["caption"][:200],
                    "caption_full": cap["caption"],
                    "caption_bbox_pdf": (cap["x0"], cap["y0"], cap["x1"], cap["y1"]),
                    "sublabels": sublabels,
                    "sublabel_details": [
                        {
                            "label": lbl,
                            "format": _detect_sublabel_format(lbl, cap["caption"]),
                        }
                        for lbl in sublabels
                    ],
                    "figure_type": figure_type,
                    "is_supplementary": figure_type in ("supplementary", "extended_data"),
                    "image": fig_image,
                }
            )

            logger.info(
                f"Figure {cap['number']}: page {page_num}, "
                f"crop {fig_image.shape[1]}x{fig_image.shape[0]} px, "
                f"sub-labels: {sublabels if sublabels else 'none'}"
            )

        self._figures = figures
        return self._figures

    def get_figure(self, figure_num: int):
        """
        Get a specific figure by its number.

        Args:
            figure_num: the figure number to retrieve

        Returns:
            dict with figure info, or None if not found
        """
        figures = self.detect_all_figures()
        for fig in figures:
            if fig["number"] == figure_num:
                return fig
        return None

    def get_figure_or_raise(self, figure_num: int) -> dict:
        """
        Get a specific figure by its number, raising if not found.

        Args:
            figure_num: the figure number to retrieve

        Returns:
            dict with figure info

        Raises:
            FigureNotFoundError: if figure_num doesn't exist
        """
        fig = self.get_figure(figure_num)
        if fig is None:
            available = [f["number"] for f in self.detect_all_figures()]
            raise FigureNotFoundError(figure_num, available)
        return fig

    def list_figures(self) -> list:
        """Return a summary list of detected figures (without image data)."""
        figures = self.detect_all_figures()
        return [
            {
                "number": f["number"],
                "page": f["page"],
                "caption": f["caption"][:120],
                "sublabels": f["sublabels"],
            }
            for f in figures
        ]

    def get_available_numbers(self) -> list:
        """Return sorted list of available figure numbers."""
        return sorted(f["number"] for f in self.detect_all_figures())

    # --- Private Methods ---

    def _find_all_captions(self) -> list:
        """
        Scan all pages and find figure caption lines.

        A caption is a line that STARTS with "Fig. N" or "Figure N" pattern.
        In-text references like "as shown in Fig. 1" are excluded because
        the pattern doesn't appear at line start.

        Uses two methods:
        1. pdfplumber extract_lines (primary, more accurate positioning)
        2. PyMuPDF get_text() (fallback, catches captions missed by pdfplumber)

        Returns:
            list of dicts: [
                {
                    "number": int,
                    "page": int,
                    "caption": str,        # full caption text
                    "figure_type": str,    # figure type from FIGURE_TYPE_BY_PATTERN
                    "x0": float, "y0": float, "x1": float, "y1": float,
                },
            ]
        """
        captions = []
        seen_figures = set()  # track (page, number) to avoid duplicates

        total_pages = self.pdf_parser.get_page_count()
        for page_num in range(total_pages):
            # Method 1: Try pdfplumber extract_lines
            try:
                lines = self.pdf_parser.extract_lines(page_num)
            except Exception as e:
                logger.warning(f"Skipping page {page_num}: text extraction failed: {e}")
                lines = []

            for line in lines:
                text = line["text"].strip()
                if not text:
                    continue

                fig_num, pattern_idx = self._match_caption(text)
                if fig_num is not None:
                    key = (page_num, fig_num)
                    if key in seen_figures:
                        continue
                    if len(text) < 6:
                        continue

                    seen_figures.add(key)
                    figure_type = FIGURE_TYPE_BY_PATTERN.get(pattern_idx, "figure")
                    captions.append(
                        {
                            "number": fig_num,
                            "page": page_num,
                            "caption": text,
                            "figure_type": figure_type,
                            "x0": line["x0"],
                            "y0": line["y0"],
                            "x1": line["x1"],
                            "y1": line["y1"],
                        }
                    )

            # Method 2: Fallback to PyMuPDF get_text() to catch missed captions
            # This is slower but catches captions in special text boxes
            try:
                import fitz
                page = self.pdf_parser._fitz_doc[page_num]
                full_text = page.get_text()

                # Look for figure numbers in the full text
                for match in re.finditer(r'\b(Fig\.?\s*(\d+))\b', full_text, re.IGNORECASE):
                    fig_num = int(match.group(2))
                    key = (page_num, fig_num)

                    if key not in seen_figures:
                        # Extract context around the match (up to 200 chars)
                        start = max(0, match.start() - 10)
                        end = min(len(full_text), match.end() + 150)
                        caption_text = full_text[start:end].strip()

                        if len(caption_text) >= 6:
                            seen_figures.add(key)
                            # Use approximate coordinates (page center)
                            page_w, page_h = self.pdf_parser.get_page_size(page_num)
                            captions.append(
                                {
                                    "number": fig_num,
                                    "page": page_num,
                                    "caption": caption_text,
                                    "figure_type": "figure",
                                    "x0": 30.0,
                                    "y0": page_h * 0.5,
                                    "x1": page_w - 30.0,
                                    "y1": page_h * 0.5 + 20.0,
                                }
                            )
            except Exception as e:
                logger.debug(f"PyMuPDF fallback on page {page_num} failed: {e}")

        # Deduplicate: if same figure number found on multiple pages,
        # keep the one with the longest caption (likely the real caption)
        unique_captions = {}
        for cap in captions:
            num = cap["number"]
            if num not in unique_captions or len(cap["caption"]) > len(
                unique_captions[num]["caption"]
            ):
                unique_captions[num] = cap

        result = sorted(unique_captions.values(), key=lambda c: c["number"])
        return result

    def _match_caption(self, text: str):
        """
        Check if a line of text is a figure caption.

        Returns:
            (figure_num: int, pattern_idx: int) if matched, (None, None) otherwise.
        """
        text_stripped = text.strip()
        for idx, pattern in enumerate(CAPTION_PATTERNS):
            m = pattern.match(text_stripped)
            if m:
                return int(m.group(2)), idx
        return None, None

    def _compute_figure_bbox(
        self, caption: dict, all_lines: list, page_num: int, page_captions: list
    ) -> tuple:
        """
        Compute the bounding box of a figure's image region.

        Strategy:
        - Bottom boundary: caption's y0 (figure is ABOVE its caption)
        - Top boundary: find the nearest text line ABOVE the figure
          that is NOT part of the figure (i.e., body text or previous caption)
        - Left/Right: use page margins (slightly inset from edges)

        Args:
            caption: caption dict with position info
            all_lines: all text lines on this page
            page_num: page number
            page_captions: all captions on this page

        Returns:
            (x0, y0, x1, y1) in PDF coordinate space
        """
        page_w, page_h = self.pdf_parser.get_page_size(page_num)

        # Figure bottom = caption top (with small gap)
        fig_bottom = caption["y0"] - 2.0

        # Find the top boundary by looking for text lines above the caption
        # that are body text (not part of the figure)
        fig_top = self._find_figure_top(caption, all_lines, page_captions, page_h)

        # Left/right: use page content margins
        # Typically academic papers have margins around 36-72 points
        margin_x = 30.0
        fig_left = margin_x
        fig_right = page_w - margin_x

        # Sanity check
        if fig_top >= fig_bottom:
            # Fallback: use a reasonable height (40% of page)
            fig_top = max(0, fig_bottom - page_h * 0.4)

        return (fig_left, fig_top, fig_right, fig_bottom)

    def _find_figure_top(
        self, caption: dict, all_lines: list, page_captions: list, page_h: float
    ) -> float:
        """
        Find the top boundary of a figure by analyzing text above it.

        Logic:
        - Look upward from the caption position
        - Find body text lines (short lines are likely labels inside figure)
        - A "body text" line is one that spans a significant width
        - The figure top is just below the last body text line above it

        Returns:
            y coordinate (PDF points) for the top of the figure
        """
        caption_y = caption["y0"]

        # Collect lines above the caption, sorted by y descending (nearest first)
        lines_above = [
            l
            for l in all_lines
            if l["y1"] < caption_y - 5.0  # must be clearly above caption
        ]
        lines_above.sort(key=lambda l: l["y1"], reverse=True)

        # Also check if there's another caption above (for multi-figure pages)
        other_caption_bottoms = []
        for cap in page_captions:
            if cap["number"] != caption["number"] and cap["y1"] < caption_y:
                # The previous caption's bottom (including its text) is a boundary
                other_caption_bottoms.append(cap["y1"])

        if not lines_above:
            # No text above 鈥?figure starts at page top
            return 20.0

        # Walk upward through lines above the caption
        # Looking for non-figure-content: body text lines
        # Body text typically has width > 200 points and is left-aligned
        # Figure internal text (axis labels, etc.) is typically short

        # Strategy: find the first "gap" 鈥?a vertical space > threshold
        # between consecutive text lines, indicating figure boundary
        gap_threshold = 15.0  # points 鈥?typical paragraph gap

        previous_bottom = caption_y
        for line in lines_above:
            gap = previous_bottom - line["y1"]
            line_width = line["x1"] - line["x0"]

            # If there's a significant gap AND the line above is wide (body text),
            # this gap likely separates figure from body text
            if gap > gap_threshold and line_width > 150:
                return line["y1"] + 3.0  # figure starts just below this text

            # If we hit another figure caption, stop
            fig_num, _ = self._match_caption(line["text"])
            if fig_num is not None:
                return line["y1"] + 3.0

            previous_bottom = line["y0"]

        # Also respect other caption boundaries
        if other_caption_bottoms:
            max_other_bottom = max(other_caption_bottoms)
            return max(max_other_bottom + 5.0, 20.0)

        # Fallback: use page top margin
        return 20.0

    def _extract_sublabels(self, caption_text: str) -> list:
        """
        Extract sub-figure labels from caption text.
        Supports: (a), (A), a), (i), (1), a.
        Returns sorted list of unique lowercase labels.
        """
        all_matches = []
        for pattern in SUBLABEL_PATTERNS:
            matches = pattern.findall(caption_text)
            all_matches.extend(m.lower() for m in matches)

        # Deduplicate and sort
        unique = sorted(set(all_matches))
        return unique

