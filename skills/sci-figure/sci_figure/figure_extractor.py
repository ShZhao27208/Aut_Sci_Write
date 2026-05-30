"""
Figure Extractor — three-engine fusion orchestrator.

Coordinates Native extraction, CV region detection, and Caption-anchored
fallback to produce the most accurate figure bounding boxes.

Pipeline:
1. Caption detection → identify which pages have figures
2. For each caption, run engines in priority order:
   A. Native (PyMuPDF embedded images) — pixel-perfect for raster
   B. CV (connected component analysis) — works for vector + raster
   C. Caption-anchored heuristic — last resort fallback
3. Boundary refinement (trim whitespace, column constraint)
4. Output cropped figure images
"""

from __future__ import annotations

import cv2
import numpy as np
from sci_figure.pdf_parser import PDFParser
from sci_figure.caption_detector import CaptionDetector
from sci_figure.native_extractor import NativeExtractor
from sci_figure.region_detector import RegionDetector
from sci_figure.column_detector import ColumnDetector
from sci_figure.utils import get_logger

logger = get_logger()


class FigureExtractor:
    """Three-engine fusion figure extractor."""

    def __init__(self, pdf_path: str, dpi: int = 600, strategy: str = "hybrid"):
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.strategy = strategy

        self._parser = PDFParser(pdf_path, dpi=dpi)
        self._caption_detector = CaptionDetector(self._parser.plumber_doc)
        self._native_extractor = NativeExtractor(self._parser.fitz_doc)
        self._region_detector = RegionDetector()
        self._column_detector = ColumnDetector()

        self._figures: list[dict] | None = None

    def detect_all(self) -> list[dict]:
        """
        Detect and extract all figures from the PDF.

        Returns:
            List of figure dicts:
            [{
                "number": int,
                "page": int,
                "bbox_pdf": tuple,
                "bbox_px": tuple,
                "caption_text": str,
                "figure_type": str,
                "sublabels": list,
                "image": np.ndarray,
                "engine_used": str,
            }, ...]
        """
        if self._figures is not None:
            return self._figures

        captions = self._caption_detector.detect_all()
        if not captions:
            logger.warning("No figure captions found in PDF.")
            self._figures = []
            return self._figures

        logger.info(f"Processing {len(captions)} figure(s)...")
        figures = []
        used_xrefs: dict[int, set[int]] = {}

        for cap in captions:
            page_num = cap["page"]
            if page_num not in used_xrefs:
                used_xrefs[page_num] = set()

            fig = self._extract_single(cap, used_xrefs[page_num])
            if fig is not None:
                figures.append(fig)

        self._figures = figures
        logger.info(f"Successfully extracted {len(figures)} figure(s)")
        return self._figures

    def get_figure(self, figure_num: int) -> dict | None:
        """Get a specific figure by number."""
        for fig in self.detect_all():
            if fig["number"] == figure_num:
                return fig
        return None

    def list_figures(self) -> list[dict]:
        """List detected figures without image data."""
        return [
            {k: v for k, v in fig.items() if k != "image"}
            for fig in self.detect_all()
        ]

    def extract_by_bbox(
        self, page_num: int, bbox_px: tuple
    ) -> np.ndarray:
        """Manual extraction: crop by pixel coordinates (for multimodal correction)."""
        page_img = self._parser.render_page(page_num)
        h, w = page_img.shape[:2]
        x0, y0, x1, y1 = bbox_px
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(w, int(x1)), min(h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return np.array([], dtype=np.uint8)
        return page_img[y0:y1, x0:x1].copy()

    def close(self):
        self._parser.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    # --- Internal pipeline ---

    def _extract_single(self, caption: dict, used_xrefs: set[int]) -> dict | None:
        """Extract a single figure using the three-engine pipeline."""
        page_num = caption["page"]
        page_img = self._parser.render_page(page_num)
        page_w, page_h = self._parser.get_page_size(page_num)
        h_px, w_px = page_img.shape[:2]

        # Detect column layout
        layout = self._column_detector.detect(page_img)
        caption_col = self._column_detector.get_column_for_position(
            caption["column_hint"] * self._parser._scale, layout
        )
        col_bounds_px = layout["column_boundaries"][caption_col] if layout["n_columns"] > 1 else None
        col_bounds_pdf = None
        if col_bounds_px:
            col_bounds_pdf = (
                col_bounds_px[0] / self._parser._scale,
                col_bounds_px[1] / self._parser._scale,
            )

        bbox_pdf = None
        engine_used = "none"
        matched_xref: int | None = None

        # Engine A: Native extraction (raster images)
        if self.strategy in ("hybrid", "native"):
            bbox_pdf, matched_xref = self._try_native(
                page_num, caption, page_w, page_h, col_bounds_pdf, used_xrefs
            )
            if bbox_pdf:
                engine_used = "native"

        # Engine B: CV region detection
        if bbox_pdf is None and self.strategy in ("hybrid", "cv"):
            bbox_pdf = self._try_cv(page_img, caption, h_px, w_px, col_bounds_px)
            if bbox_pdf:
                engine_used = "cv"

        # Engine C: Caption-anchored fallback
        if bbox_pdf is None:
            bbox_pdf = self._fallback_caption_anchored(caption, page_w, page_h)
            if bbox_pdf:
                engine_used = "fallback"

        if bbox_pdf is None:
            logger.warning(f"Figure {caption['number']}: all engines failed")
            return None

        # Record claimed xref so other captions on this page won't reuse it
        if matched_xref is not None:
            used_xrefs.add(matched_xref)

        # Boundary refinement
        bbox_pdf = self._refine_bbox(bbox_pdf, page_w, page_h, col_bounds_pdf)

        # Crop image
        bbox_px = self._parser.pdf_to_pixel(bbox_pdf)
        x0, y0, x1, y1 = bbox_px
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w_px, x1), min(h_px, y1)

        if x1 - x0 < 30 or y1 - y0 < 30:
            logger.warning(f"Figure {caption['number']}: crop too small, skipping")
            return None

        image = page_img[y0:y1, x0:x1].copy()
        image = self._trim_whitespace(image)

        if image.size == 0:
            return None

        # Validate: reject if the crop is predominantly text
        if not self._is_figure_content(image):
            logger.warning(
                f"Figure {caption['number']}: rejected (text-only content, "
                f"engine={engine_used})"
            )
            # If native/cv failed validation, try next engine
            if engine_used == "native" and self.strategy == "hybrid":
                bbox_pdf = self._try_cv(page_img, caption, h_px, w_px, col_bounds_px)
                if bbox_pdf:
                    bbox_pdf = self._refine_bbox(bbox_pdf, page_w, page_h, col_bounds_pdf)
                    bbox_px = self._parser.pdf_to_pixel(bbox_pdf)
                    x0, y0, x1, y1 = bbox_px
                    x0, y0 = max(0, x0), max(0, y0)
                    x1, y1 = min(w_px, x1), min(h_px, y1)
                    if x1 - x0 >= 30 and y1 - y0 >= 30:
                        image = page_img[y0:y1, x0:x1].copy()
                        image = self._trim_whitespace(image)
                        if image.size > 0 and self._is_figure_content(image):
                            engine_used = "cv"
                            logger.info(
                                f"Figure {caption['number']}: recovered via CV "
                                f"({image.shape[1]}x{image.shape[0]}px)"
                            )
                        else:
                            return None
                    else:
                        return None
                else:
                    return None
            else:
                return None

        logger.info(
            f"Figure {caption['number']}: {image.shape[1]}x{image.shape[0]}px "
            f"(engine={engine_used})"
        )

        return {
            "number": caption["number"],
            "page": page_num,
            "bbox_pdf": bbox_pdf,
            "bbox_px": (x0, y0, x1, y1),
            "caption_text": caption["caption_text"],
            "figure_type": caption["figure_type"],
            "sublabels": caption["sublabels"],
            "image": image,
            "engine_used": engine_used,
        }

    def _try_native(
        self, page_num, caption, page_w, page_h, col_bounds_pdf, exclude_xrefs: set[int]
    ) -> tuple[tuple | None, int | None]:
        """Engine A: try PyMuPDF native image extraction.

        Returns:
            (bbox_pdf, matched_xref) or (None, None) if no match.
        """
        images = self._native_extractor.extract_page_images(page_num)
        if not images:
            return None, None

        images = self._native_extractor.merge_adjacent_images(images)
        match = self._native_extractor.match_to_caption(
            images, caption["bbox_pdf"], (page_w, page_h), col_bounds_pdf,
            exclude_xrefs=exclude_xrefs,
        )
        if match:
            return match["bbox_pdf"], match["xref"]
        return None, None

    def _try_cv(self, page_img, caption, page_height_px, page_width_px, col_bounds_px):
        """Engine B: try CV connected-component region detection."""
        regions = self._region_detector.detect_regions(page_img)
        if not regions:
            return None

        caption_bbox_px = self._parser.pdf_to_pixel(caption["bbox_pdf"])
        match = self._region_detector.match_to_caption(
            regions, caption_bbox_px, page_height_px, page_width_px, col_bounds_px
        )
        if match:
            return self._parser.pixel_to_pdf(match["bbox"])
        return None

    def _fallback_caption_anchored(self, caption, page_w, page_h):
        """Engine C: simple heuristic — figure is above caption, same width."""
        cap_x0, cap_y0, cap_x1, cap_y1 = caption["bbox_pdf"]

        fig_bottom = cap_y0 - 3.0
        fig_top = max(10.0, fig_bottom - page_h * 0.35)
        fig_left = max(20.0, cap_x0 - 10.0)
        fig_right = min(page_w - 20.0, cap_x1 + 10.0)

        # Expand width if caption is narrow (common in double-column)
        if (fig_right - fig_left) < page_w * 0.3:
            center = (fig_left + fig_right) / 2
            half_width = page_w * 0.2
            fig_left = max(20.0, center - half_width)
            fig_right = min(page_w - 20.0, center + half_width)

        if fig_top >= fig_bottom:
            return None

        return (fig_left, fig_top, fig_right, fig_bottom)

    def _refine_bbox(self, bbox_pdf, page_w, page_h, col_bounds_pdf):
        """Apply boundary refinements."""
        x0, y0, x1, y1 = bbox_pdf

        # Clamp to page
        x0 = max(5.0, x0)
        y0 = max(5.0, y0)
        x1 = min(page_w - 5.0, x1)
        y1 = min(page_h - 5.0, y1)

        # Column constraint
        if col_bounds_pdf:
            col_start, col_end = col_bounds_pdf
            x0 = max(x0, col_start)
            x1 = min(x1, col_end)

        return (x0, y0, x1, y1)

    def _trim_whitespace(
        self, image: np.ndarray, threshold: int = 250, min_content: float = 0.01
    ) -> np.ndarray:
        """Trim pure-white borders from image."""
        if image.size == 0:
            return image

        gray = np.mean(image, axis=2) if image.ndim == 3 else image
        mask = gray < threshold

        # Find content bounds
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            return image

        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]

        # Add small padding (2px)
        h, w = image.shape[:2]
        y_min = max(0, y_min - 2)
        y_max = min(h - 1, y_max + 2)
        x_min = max(0, x_min - 2)
        x_max = min(w - 1, x_max + 2)

        trimmed = image[y_min:y_max+1, x_min:x_max+1]

        # Only trim if we didn't remove too much
        if trimmed.size > image.size * min_content:
            return trimmed
        return image

    def _is_figure_content(self, image: np.ndarray) -> bool:
        """
        Validate that a cropped region contains figure content, not just text.

        Key distinction: text = many small uniform components in regular lines.
        Figures (even grayscale) have axes, curves, or varied structure.
        """
        if image.size == 0 or image.shape[0] < 30 or image.shape[1] < 30:
            return False

        h, w = image.shape[:2]
        area = h * w

        # Check 1: Color presence (strong figure signal)
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        saturation = hsv[:, :, 1]
        color_ratio = float(np.mean(saturation > 40))
        if color_ratio > 0.03:
            return True

        # Check 2: Look for long lines (axes, curves) — figure indicator
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 8
        )

        # Detect long horizontal or vertical lines
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, w // 8), 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(40, h // 8)))
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
        line_pixels = cv2.countNonZero(h_lines) + cv2.countNonZero(v_lines)

        if line_pixels > area * 0.002:
            return True

        # Check 3: Connected component analysis
        n_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )
        if n_labels < 2:
            return False

        areas_arr = stats[1:, cv2.CC_STAT_AREA]
        heights_arr = stats[1:, cv2.CC_STAT_HEIGHT]
        widths_arr = stats[1:, cv2.CC_STAT_WIDTH]

        # Text characters: small, uniform height, moderate aspect ratio
        max_char_h = h * 0.035
        max_char_area = area * 0.0008
        text_like = np.sum(
            (areas_arr < max_char_area) & (heights_arr < max_char_h)
        )
        total = len(areas_arr)

        if total == 0:
            return False

        text_ratio = text_like / total

        # Check 4: Size variance — figures have diverse component sizes
        if total > 5:
            area_std = np.std(areas_arr) / (np.mean(areas_arr) + 1)
            if area_std > 3.0:
                return True

        # Check 5: Any large elongated component (axis line, curve)
        for i in range(len(areas_arr)):
            cw, ch = widths_arr[i], heights_arr[i]
            if cw > w * 0.3 or ch > h * 0.3:
                return True

        # Final decision: if >90% text-like AND no structural indicators
        if text_ratio > 0.90:
            return False

        return True
