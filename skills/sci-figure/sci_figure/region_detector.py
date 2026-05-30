"""
Region Detector — CV-based figure region detection on rendered pages.

Core algorithm:
1. Adaptive thresholding (separate foreground/background)
2. Morphological operations (dilate + close to merge figure fragments)
3. Connected component analysis (find large non-text regions)
4. Filtering (area threshold, aspect ratio, color detection)
5. Output candidate regions with confidence scores
"""

from __future__ import annotations

import numpy as np
import cv2
from sci_figure.utils import get_logger

logger = get_logger()


class RegionDetector:
    """Detect figure candidate regions in rendered page images using CV."""

    def __init__(
        self,
        min_area_ratio: float = 0.03,
        max_area_ratio: float = 0.85,
        margin_ratio: float = 0.03,
    ):
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.margin_ratio = margin_ratio

    def detect_regions(self, page_image: np.ndarray) -> list[dict]:
        """
        Detect all figure candidate regions in a rendered page image.

        Args:
            page_image: RGB numpy array of the rendered page

        Returns:
            List of region dicts sorted by area (descending):
            [{"bbox": (x0,y0,x1,y1), "area": int, "has_color": bool,
              "confidence": float, "density": float}, ...]
        """
        if page_image is None or page_image.size == 0:
            return []

        h, w = page_image.shape[:2]
        page_area = h * w

        # Step 1: Convert to grayscale and create figure mask
        gray = cv2.cvtColor(page_image, cv2.COLOR_RGB2GRAY)
        figure_mask = self._create_figure_mask(gray, h, w)

        # Step 2: Find contours (candidate regions)
        contours, _ = cv2.findContours(
            figure_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Step 3: Filter and score candidates
        margin_x = int(w * self.margin_ratio)
        margin_y = int(h * self.margin_ratio)
        regions = []

        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            area = cw * ch

            # Area filter
            if area < page_area * self.min_area_ratio:
                continue
            if area > page_area * self.max_area_ratio:
                continue

            # Margin filter (skip things at very edge)
            if x < margin_x and cw < w * 0.3:
                continue
            if y < margin_y and ch < h * 0.1:
                continue

            # Aspect ratio filter (reject extreme strips)
            aspect = cw / ch if ch > 0 else 0
            if aspect > 6 or aspect < 0.1:
                continue

            # Compute fill density
            contour_area = cv2.contourArea(contour)
            density = contour_area / area if area > 0 else 0

            # Color detection
            roi = page_image[y:y+ch, x:x+cw]
            has_color = self._has_color(roi)

            # Confidence scoring
            confidence = self._score_region(
                area, page_area, density, has_color, aspect, y, h
            )

            regions.append({
                "bbox": (x, y, x + cw, y + ch),
                "area": area,
                "has_color": has_color,
                "confidence": confidence,
                "density": density,
            })

        regions.sort(key=lambda r: r["confidence"], reverse=True)

        logger.info(f"CV detector: {len(regions)} candidate region(s) found")
        return regions

    def match_to_caption(
        self,
        regions: list[dict],
        caption_bbox_px: tuple,
        page_height: int,
        page_width: int,
        column_bounds: tuple = None,
    ) -> dict | None:
        """
        Find the region best matching a caption position.

        Strategy: figure is typically ABOVE its caption, with horizontal overlap.
        If column_bounds provided, restrict matching to that column.
        """
        if not regions:
            return None

        cap_x0, cap_y0, cap_x1, cap_y1 = caption_bbox_px
        cap_width = cap_x1 - cap_x0
        cap_center_x = (cap_x0 + cap_x1) / 2

        best = None
        best_score = -1.0

        for region in regions:
            rx0, ry0, rx1, ry1 = region["bbox"]

            # Column constraint
            if column_bounds:
                col_start, col_end = column_bounds
                region_center_x = (rx0 + rx1) / 2
                if not (col_start <= region_center_x <= col_end):
                    continue

            # Region should be above caption (allow small overlap)
            if ry0 > cap_y0:
                continue

            # Horizontal overlap
            overlap_x = max(0, min(rx1, cap_x1) - max(rx0, cap_x0))
            overlap_ratio = overlap_x / cap_width if cap_width > 0 else 0

            # Vertical proximity (closer = better)
            vertical_dist = cap_y0 - ry1
            if vertical_dist < 0:
                vertical_dist = 0
            proximity_score = max(0, 1.0 - vertical_dist / (page_height * 0.3))

            # Center alignment bonus (horizontal offset normalized by page WIDTH)
            region_center = (rx0 + rx1) / 2
            center_offset = abs(region_center - cap_center_x) / (page_width * 0.5)
            alignment_score = max(0, 1.0 - center_offset)

            score = (
                overlap_ratio * 0.4
                + proximity_score * 0.4
                + alignment_score * 0.1
                + region["confidence"] * 0.1
            )

            if score > best_score:
                best_score = score
                best = region

        if best and best_score > 0.3:
            logger.info(
                f"Matched region {best['bbox']} to caption "
                f"(score={best_score:.2f})"
            )
            return best

        return None

    def _create_figure_mask(self, gray: np.ndarray, h: int, w: int) -> np.ndarray:
        """
        Create a binary mask highlighting figure regions while excluding text.

        Strategy:
        1. Adaptive threshold → binary foreground
        2. Remove text-sized connected components (small CCs = characters)
        3. Morphological close on remaining (figure) elements
        4. Filter out regions with text-like density patterns
        """
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 25, 8
        )

        # Remove text: filter out small connected components (characters)
        # At 300 DPI, a typical character is ~15-40px tall, area < 600px²
        cleaned = self._remove_text_components(binary, h, w)

        # Small dilation: connect nearby figure elements
        k_small = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        dilated = cv2.dilate(cleaned, k_small, iterations=2)

        # Moderate closing: merge figure fragments without bridging columns
        kw = max(20, int(w * 0.02))
        kh = max(15, int(h * 0.015))
        k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, k_close)

        # Opening to remove noise
        k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, k_open)

        return opened

    def _remove_text_components(
        self, binary: np.ndarray, h: int, w: int
    ) -> np.ndarray:
        """
        Remove connected components that are text-sized characters.

        Text characters at 300 DPI are typically:
        - Height: 10-50px
        - Area: 30-800px²
        - Aspect ratio: 0.2-5.0

        Figure elements (axes, lines, data points, fills) are typically larger
        or have very different aspect ratios.
        """
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )

        # Thresholds scaled to DPI (assuming ~300 DPI for a rendered page)
        max_text_height = int(h * 0.02)  # ~60px at 3000px page height
        max_text_area = int(h * w * 0.0003)  # ~900px² at 3000x2100

        cleaned = binary.copy()

        for i in range(1, n_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            comp_h = stats[i, cv2.CC_STAT_HEIGHT]
            comp_w = stats[i, cv2.CC_STAT_WIDTH]

            # Skip very tiny noise
            if area < 5:
                cleaned[labels == i] = 0
                continue

            # Text character heuristic: small area AND moderate height
            if area < max_text_area and comp_h < max_text_height:
                cleaned[labels == i] = 0
                continue

            # Thin horizontal lines (underlines, rules) — keep for figures
            # but remove if very thin and wide (likely text decoration)
            if comp_h < 4 and comp_w > w * 0.2:
                cleaned[labels == i] = 0
                continue

        return cleaned

    def _has_color(self, roi: np.ndarray, threshold: float = 0.03) -> bool:
        """Check if region contains significant color (non-grayscale)."""
        if roi.size == 0 or roi.shape[0] < 5 or roi.shape[1] < 5:
            return False
        hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
        saturation = hsv[:, :, 1]
        return float(np.mean(saturation > 30)) > threshold

    def _score_region(
        self,
        area: int,
        page_area: int,
        density: float,
        has_color: bool,
        aspect: float,
        y: int,
        page_height: int,
    ) -> float:
        """
        Score a candidate region's likelihood of being a figure.

        Factors:
        - Area ratio (moderate size preferred)
        - Fill density (figures tend to be dense)
        - Color presence (strong signal)
        - Aspect ratio (moderate preferred)
        - Vertical position (not at very top/bottom = header/footer)
        """
        # Area score: prefer 5%-60% of page
        area_ratio = area / page_area
        if area_ratio < 0.05:
            area_score = area_ratio / 0.05
        elif area_ratio > 0.6:
            area_score = max(0, 1.0 - (area_ratio - 0.6) / 0.3)
        else:
            area_score = 1.0

        # Density score
        density_score = min(1.0, density / 0.5)

        # Color bonus
        color_score = 1.0 if has_color else 0.5

        # Aspect score: prefer 0.3 - 3.0
        if 0.3 <= aspect <= 3.0:
            aspect_score = 1.0
        else:
            aspect_score = 0.5

        # Position score: penalize very top/bottom (headers/footers)
        y_ratio = y / page_height
        if 0.05 < y_ratio < 0.9:
            position_score = 1.0
        else:
            position_score = 0.5

        return (
            area_score * 0.3
            + density_score * 0.2
            + color_score * 0.25
            + aspect_score * 0.15
            + position_score * 0.1
        )
