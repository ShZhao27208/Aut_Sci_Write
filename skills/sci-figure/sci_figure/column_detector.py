"""
Column Detector — detect single/double column layout in PDF pages.

Uses vertical white-band analysis on rendered page images to determine
whether a page is single-column or multi-column, and where the column
boundaries are.
"""

from __future__ import annotations

import numpy as np
import cv2
from sci_figure.utils import get_logger

logger = get_logger()


class ColumnDetector:
    """Detect page column layout from rendered page images."""

    def __init__(self, min_gap_ratio: float = 0.01, white_threshold: int = 245):
        self.min_gap_ratio = min_gap_ratio
        self.white_threshold = white_threshold

    def detect(self, page_image: np.ndarray) -> dict:
        """
        Detect column layout of a rendered page.

        Returns:
            {
                "n_columns": int,          # 1 or 2 (or more)
                "column_boundaries": list,  # [(x_start, x_end), ...]
                "gap_positions": list,      # [x_mid, ...] of inter-column gaps
            }
        """
        h, w = page_image.shape[:2]
        gray = cv2.cvtColor(page_image, cv2.COLOR_RGB2GRAY)

        # Analyze vertical projection in the middle 70% of the page height
        # (skip headers/footers which may span full width)
        y_start = int(h * 0.15)
        y_end = int(h * 0.85)
        roi = gray[y_start:y_end, :]

        white_fraction = np.mean(roi > self.white_threshold, axis=0)

        # Find vertical white bands (potential column gaps)
        min_gap_px = max(8, int(w * self.min_gap_ratio))
        gaps = self._find_white_bands(white_fraction, min_gap_px, w)

        if not gaps:
            return {
                "n_columns": 1,
                "column_boundaries": [(0, w)],
                "gap_positions": [],
            }

        # Filter: column gap should be near the center (20%-80% of page width)
        center_gaps = [
            g for g in gaps
            if w * 0.2 < g["center"] < w * 0.8
        ]

        if not center_gaps:
            return {
                "n_columns": 1,
                "column_boundaries": [(0, w)],
                "gap_positions": [],
            }

        # Use the strongest (widest) center gap as the column divider
        best_gap = max(center_gaps, key=lambda g: g["width"])
        gap_center = best_gap["center"]

        logger.info(
            f"Double-column detected: gap at x={gap_center} "
            f"(width={best_gap['width']}px)"
        )

        return {
            "n_columns": 2,
            "column_boundaries": [
                (0, best_gap["start"]),
                (best_gap["end"], w),
            ],
            "gap_positions": [gap_center],
        }

    def get_column_for_position(self, x: float, layout: dict) -> int:
        """Return which column (0-indexed) a given x-coordinate belongs to."""
        for i, (col_start, col_end) in enumerate(layout["column_boundaries"]):
            if col_start <= x <= col_end:
                return i
        return 0

    def _find_white_bands(
        self, white_fraction: np.ndarray, min_gap: int, page_width: int
    ) -> list[dict]:
        """Find continuous white vertical bands."""
        is_white = white_fraction > 0.90
        bands = []
        in_band = False
        band_start = 0

        margin = int(page_width * 0.05)

        for i in range(len(is_white)):
            if is_white[i] and not in_band:
                band_start = i
                in_band = True
            elif not is_white[i] and in_band:
                band_width = i - band_start
                center = (band_start + i) // 2
                if band_width >= min_gap and margin < center < page_width - margin:
                    bands.append({
                        "start": band_start,
                        "end": i,
                        "center": center,
                        "width": band_width,
                    })
                in_band = False

        return bands
