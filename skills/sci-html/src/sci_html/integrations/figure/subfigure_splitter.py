#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sub-figure Splitter Module

Strategy (priority order):
1. White-space projection analysis 鈥?find horizontal/vertical gaps to split grid
2. Multi-PSM OCR fusion 鈥?detect (a)/(b)/(c) labels for assignment
3. Caption-based fallback 鈥?use caption sublabels + grid cell ordering

This hybrid approach is far more reliable than pure OCR.
"""

import re
import cv2
import numpy as np
import pytesseract
import platform
from .utils import get_logger, check_tesseract

logger = get_logger()

# Set Tesseract path for Windows
if platform.system() == "Windows":
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

SUBLABEL_RE = re.compile(r"\(?([a-zA-Z])\)?")


class SubfigureSplitter:
    """Split composite figures into sub-figures using white-space analysis + OCR."""

    def __init__(self, pdf_parser=None):
        self.pdf_parser = pdf_parser

    def extract_subfigure(
        self, figure_info: dict, sublabel: str,
        expected_labels: list = None,
    ) -> np.ndarray:
        """
        Extract a specific sub-figure from a composite figure.
        
        Args:
            figure_info: dict with "image", "sublabels" (from caption), etc.
            sublabel: target sub-figure label (e.g., "c")
            expected_labels: override caption sublabels if provided
        
        Returns:
            numpy array of the sub-figure image, or None if not found.
        """
        sublabel = sublabel.lower().strip()
        figure_image = figure_info["image"]
        caption_labels = expected_labels or figure_info.get("sublabels", [])
        n_expected = len(caption_labels) if caption_labels else 0
        
        # Step 1: Split figure into cells via white-space analysis
        cells = self._split_by_whitespace(figure_image, n_expected=n_expected)
        
        if not cells or len(cells) < 2:
            logger.warning(
                "White-space analysis found no splits. Returning entire figure."
            )
            return None
        
        logger.info(f"White-space split: {len(cells)} cells detected")
        
        # Step 2: Assign labels to cells
        labeled_cells = self._assign_labels(figure_image, cells, caption_labels)
        
        if sublabel not in labeled_cells:
            available = sorted(labeled_cells.keys())
            logger.warning(
                f"Sublabel '{sublabel}' not available. "
                f"Available: {available}. Returning entire figure."
            )
            return None
        
        # Step 3: Crop
        x0, y0, x1, y1 = labeled_cells[sublabel]
        img_h, img_w = figure_image.shape[:2]
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(img_w, int(x1)), min(img_h, int(y1))
        
        if x1 <= x0 or y1 <= y0:
            logger.warning("Invalid crop region. Returning entire figure.")
            return None
        
        subfig = figure_image[y0:y1, x0:x1].copy()
        logger.info(
            f"Extracted subfigure '{sublabel}': "
            f"{subfig.shape[1]}x{subfig.shape[0]} px "
            f"from region ({x0},{y0},{x1},{y1})"
        )
        return subfig

    def get_all_subfigures(self, figure_info: dict) -> dict:
        """
        Extract ALL sub-figures from a composite figure.
        
        Returns:
            dict: {"a": np.ndarray, "b": np.ndarray, ...}
            Empty dict if no sub-figures detected.
        """
        figure_image = figure_info["image"]
        caption_labels = figure_info.get("sublabels", [])
        n_expected = len(caption_labels) if caption_labels else 0
        
        cells = self._split_by_whitespace(figure_image, n_expected=n_expected)
        if not cells or len(cells) < 2:
            return {}
        
        labeled_cells = self._assign_labels(figure_image, cells, caption_labels)
        img_h, img_w = figure_image.shape[:2]
        
        result = {}
        for label, (x0, y0, x1, y1) in sorted(labeled_cells.items()):
            x0, y0 = max(0, int(x0)), max(0, int(y0))
            x1, y1 = min(img_w, int(x1)), min(img_h, int(y1))
            if x1 > x0 and y1 > y0:
                result[label] = figure_image[y0:y1, x0:x1].copy()
        
        return result

    # ========================================================================
    # CORE: White-space projection analysis
    # ========================================================================

    def _split_by_whitespace(
        self, image: np.ndarray, n_expected: int = 0
    ) -> list:
        """
        Split image into cells by detecting white-space gaps.
        
        Uses full-span detection for horizontal splits, and
        segmented detection for vertical splits (checking each row
        segment independently, then taking intersection).
        """
        if image is None or image.size == 0:
            return []
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        
        # Dynamic min_gap: horizontal needs wider gaps, vertical can be narrower
        h_min_gap = max(15, int(h * 0.015))
        v_min_gap = max(10, int(w * 0.003))  # vertical gaps are often very narrow
        
        # --- Horizontal splits (full-width white bands) ---
        raw_row_splits = self._find_split_lines(
            gray, axis="horizontal", min_gap=h_min_gap,
            white_threshold=240, white_fraction_thresh=0.92
        )
        row_splits = self._cluster_splits(raw_row_splits, min_distance=int(h * 0.08))
        
        # --- Vertical splits (segmented detection) ---
        # A vertical gap may not span the full image height.
        # Check each horizontal segment independently, then find
        # x-positions that appear in ALL segments.
        col_splits = self._find_vertical_splits_segmented(
            gray, row_splits, min_gap=v_min_gap
        )
        
        logger.info(
            f"White-space: {len(row_splits)} row split(s), "
            f"{len(col_splits)} col split(s)"
        )
        
        # If we know expected cell count, select best split combination
        if n_expected >= 2:
            row_splits, col_splits = self._select_best_splits(
                row_splits, col_splits, n_expected, h, w
            )
            logger.info(
                f"Grid optimization for {n_expected} cells: "
                f"{len(row_splits)} row(s) x {len(col_splits)} col(s)"
            )
        
        # Build boundaries and generate cells
        row_bounds = self._splits_to_bounds(row_splits, h)
        col_bounds = self._splits_to_bounds(col_splits, w)
        
        cells = []
        for r_top, r_bot in row_bounds:
            for c_left, c_right in col_bounds:
                cell_w = c_right - c_left
                cell_h = r_bot - r_top
                if cell_w < w * 0.08 or cell_h < h * 0.08:
                    continue
                cells.append((c_left, r_top, c_right, r_bot))
        
        return cells
    
    def _find_split_lines(
        self, gray: np.ndarray, axis: str,
        min_gap: int = 20, white_threshold: int = 240,
        white_fraction_thresh: float = 0.92,
    ) -> list:
        """
        Find white bands that span the full width/height of the image.
        
        Returns:
            list of (midpoint, band_length) tuples for each detected band
        """
        h, w = gray.shape
        
        if axis == "horizontal":
            white_fraction = np.mean(gray > white_threshold, axis=1)
            length = h
        else:
            white_fraction = np.mean(gray > white_threshold, axis=0)
            length = w
        
        is_white = white_fraction > white_fraction_thresh
        
        bands = []
        margin = int(length * 0.05)  # ignore edges
        in_band = False
        band_start = 0
        
        for i in range(length):
            if is_white[i] and not in_band:
                band_start = i
                in_band = True
            elif not is_white[i] and in_band:
                band_len = i - band_start
                mid = (band_start + i) // 2
                if band_len >= min_gap and margin < mid < length - margin:
                    bands.append((mid, band_len))
                in_band = False
        
        return bands

    def _find_vertical_splits_segmented(
        self, gray: np.ndarray, row_splits: list,
        min_gap: int = 20,
    ) -> list:
        """
        Find vertical split lines by checking each row segment independently.
        
        A vertical gap might only be white within each sub-figure row,
        not across the entire image height. This method:
        1. Divides the image into row segments using row_splits
        2. Finds vertical white bands in each segment
        3. Returns x-positions that appear in a majority of segments
        """
        h, w = gray.shape
        
        # Define row segments
        boundaries = [0] + sorted(row_splits) + [h]
        segments = []
        for i in range(len(boundaries) - 1):
            seg_h = boundaries[i + 1] - boundaries[i]
            if seg_h > h * 0.08:  # skip tiny segments
                segments.append((boundaries[i], boundaries[i + 1]))
        
        if not segments:
            segments = [(0, h)]
        
        # Find vertical white bands in each segment
        all_segment_splits = []
        for seg_top, seg_bot in segments:
            seg_gray = gray[seg_top:seg_bot, :]
            splits = self._find_split_lines(
                seg_gray, axis="vertical", min_gap=min_gap,
                white_threshold=240, white_fraction_thresh=0.85
            )
            clustered = self._cluster_splits(
                splits, min_distance=int(w * 0.08)
            )
            all_segment_splits.append(set(clustered))
        
        if not all_segment_splits:
            return []
        
        # Find x-positions present in a majority of segments
        # Collect all candidate positions
        all_positions = {}
        for seg_splits in all_segment_splits:
            for x_pos in seg_splits:
                # Find the closest existing bucket or create a new one
                matched = False
                for existing in list(all_positions.keys()):
                    if abs(x_pos - existing) < w * 0.08:
                        all_positions[existing] += 1
                        matched = True
                        break
                if not matched:
                    all_positions[x_pos] = 1
        
        # Keep positions present in majority of segments (>= 50%)
        threshold = max(1, len(segments) * 0.5)
        result = sorted(
            pos for pos, count in all_positions.items()
            if count >= threshold
        )
        
        return result
    
    def _cluster_splits(
        self, bands: list, min_distance: int
    ) -> list:
        """
        Cluster nearby split bands into single split lines.
        
        Bands within min_distance of each other are merged.
        The strongest band (longest white gap) in each cluster wins.
        
        Returns:
            list of split positions (midpoints)
        """
        if not bands:
            return []
        
        # Sort by position
        sorted_bands = sorted(bands, key=lambda b: b[0])
        
        clusters = [[sorted_bands[0]]]
        for band in sorted_bands[1:]:
            if band[0] - clusters[-1][-1][0] <= min_distance:
                clusters[-1].append(band)
            else:
                clusters.append([band])
        
        # For each cluster, pick the band with the longest white gap
        result = []
        for cluster in clusters:
            best = max(cluster, key=lambda b: b[1])
            result.append(best[0])
        
        return result
    
    def _select_best_splits(
        self, row_splits: list, col_splits: list,
        n_expected: int, img_h: int, img_w: int,
    ) -> tuple:
        """
        Select the best combination of row/col splits to produce n_expected cells.
        
        Tries all valid (n_rows, n_cols) factorizations of n_expected
        and picks the one closest to the available splits.
        """
        # Generate candidate factorizations: n_expected = n_rows * n_cols
        factorizations = []
        for nr in range(1, n_expected + 1):
            if n_expected % nr == 0:
                nc = n_expected // nr
                # Need (nr-1) row splits and (nc-1) col splits
                factorizations.append((nr, nc))
        
        best_combo = (row_splits, col_splits)
        best_score = -1
        
        for nr, nc in factorizations:
            need_row = nr - 1
            need_col = nc - 1
            
            # Check if we have enough splits
            if need_row > len(row_splits) or need_col > len(col_splits):
                continue
            
            # Score: prefer factorizations that use more of the available splits
            # and produce cells with reasonable aspect ratios
            row_score = need_row  # using more splits = better
            col_score = need_col
            
            # Aspect ratio bonus: cells should be roughly square-ish
            cell_h = img_h / nr
            cell_w = img_w / nc
            aspect = min(cell_h, cell_w) / max(cell_h, cell_w) if max(cell_h, cell_w) > 0 else 0
            
            score = (row_score + col_score) * 10 + aspect * 5
            
            if score > best_score:
                best_score = score
                # Take the top N splits by band length (strongest gaps)
                selected_rows = sorted(
                    sorted(row_splits)[:need_row] if need_row <= len(row_splits) else row_splits
                )
                selected_cols = sorted(
                    sorted(col_splits)[:need_col] if need_col <= len(col_splits) else col_splits
                )
                best_combo = (selected_rows, selected_cols)
        
        return best_combo

    def _splits_to_bounds(self, splits: list, total: int) -> list:
        """
        Convert split positions to boundary ranges.

        E.g., splits=[500] with total=1000 鈫?[(0, 500), (500, 1000)]
             splits=[] with total=1000 鈫?[(0, 1000)]
        """
        if not splits:
            return [(0, total)]

        bounds = []
        prev = 0
        for s in sorted(splits):
            bounds.append((prev, s))
            prev = s
        bounds.append((prev, total))

        return bounds

    # ========================================================================
    # Label assignment: OCR + caption fallback
    # ========================================================================

    def _assign_labels(
        self, image: np.ndarray, cells: list, caption_labels: list
    ) -> dict:
        """
        Assign sub-figure labels to grid cells.
        
        Strategy (simplified):
        1. If caption_labels match cell count 鈫?assign in reading order (most reliable)
        2. If caption_labels exist 鈫?try OCR with caption whitelist, fill gaps
        3. No caption 鈫?try OCR, then fall back to sequential letters
        """
        n_cells = len(cells)
        
        # BEST CASE: caption labels count matches cell count 鈫?direct assignment
        if caption_labels and len(caption_labels) == n_cells:
            logger.info(
                f"Caption labels match cell count: {caption_labels} 鈫?{n_cells} cells"
            )
            return {caption_labels[i]: cells[i] for i in range(n_cells)}
        
        # Try OCR with caption whitelist filtering
        ocr_labels = self._ocr_detect_labels(image, whitelist=caption_labels)
        
        if ocr_labels:
            matched = self._match_ocr_to_cells(ocr_labels, cells)
            if len(matched) == n_cells:
                logger.info(f"OCR fully matched {n_cells} cells")
                return matched
            elif len(matched) > 0:
                logger.info(
                    f"OCR partial: {len(matched)}/{n_cells}. Filling gaps."
                )
                return self._fill_gaps(matched, cells, caption_labels)
        
        # Fallback: caption labels in reading order (truncate or pad)
        if caption_labels:
            labels = caption_labels[:n_cells]
            # Pad if not enough caption labels
            while len(labels) < n_cells:
                labels.append(chr(ord('a') + len(labels)))
            logger.info(f"Using caption fallback: {labels}")
            return {labels[i]: cells[i] for i in range(n_cells)}
        
        # Last resort: sequential letters
        logger.info(f"Using sequential labels for {n_cells} cells")
        return {chr(ord('a') + i): cells[i] for i in range(min(n_cells, 26))}

    def _ocr_detect_labels(
        self, image: np.ndarray, whitelist: list = None
    ) -> list:
        """
        Multi-PSM OCR fusion with optional whitelist filtering.
        
        If whitelist is provided (e.g., ['a','b','c','d'] from caption),
        only keep OCR detections that match the whitelist.
        This eliminates false positives like (e), (o).
        """
        img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        all_candidates = {}

        # Guard: skip OCR entirely if Tesseract is not available
        if not check_tesseract():
            logger.warning("Tesseract OCR not available. Skipping OCR label detection.")
            return []

        for psm in [6, 11, 12]:
            config = (
                f"--psm {psm} "
                f"-c tessedit_char_whitelist="
                f"abcdefghijklmnopqrstuvwxyz()ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            )
            try:
                data = pytesseract.image_to_data(
                    img_bgr, output_type=pytesseract.Output.DICT, config=config
                )
            except Exception as e:
                logger.warning(f"Tesseract PSM {psm} failed: {e}")
                continue
            
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])
                
                if conf < 25 or not text:
                    continue
                
                m = SUBLABEL_RE.fullmatch(text)
                if not m:
                    continue
                
                letter = m.group(1).lower()
                
                # Whitelist filter: reject labels not in caption
                if whitelist and letter not in whitelist:
                    continue
                
                if letter not in "abcdefghijklmnop":
                    continue
                
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                
                if w > 300 or h > 300 or w < 10 or h < 10:
                    continue
                
                if letter not in all_candidates or conf > all_candidates[letter]["confidence"]:
                    all_candidates[letter] = {
                        "label": letter,
                        "position": (x + w // 2, y + h // 2),
                        "bbox": (x, y, x + w, y + h),
                        "confidence": conf,
                    }
        
        result = [v for v in all_candidates.values() if v["confidence"] >= 35]
        result.sort(key=lambda s: (s["position"][1], s["position"][0]))
        
        if result:
            labels_str = ", ".join(
                f"({s['label']}) conf={s['confidence']}" for s in result
            )
            logger.info(f"OCR (filtered): {labels_str}")
        
        return result

    def _match_ocr_to_cells(self, ocr_labels: list, cells: list) -> dict:
        """
        Match OCR-detected labels to grid cells by position.

        Each OCR label is assigned to the cell that contains its position.
        """
        matched = {}

        for label_info in ocr_labels:
            lx, ly = label_info["position"]
            label = label_info["label"]

            for cell in cells:
                cx0, cy0, cx1, cy1 = cell
                if cx0 <= lx <= cx1 and cy0 <= ly <= cy1:
                    matched[label] = cell
                    break

        return matched

    def _fill_gaps(self, matched: dict, cells: list, caption_labels: list) -> dict:
        """
        Fill unmatched cells using caption labels.

        For cells not matched by OCR, assign the next available
        caption label in reading order.
        """
        result = dict(matched)
        matched_cells = set(tuple(v) for v in matched.values())
        used_labels = set(matched.keys())

        # Find available caption labels (not already used by OCR)
        available_labels = [l for l in caption_labels if l not in used_labels]

        # Find unmatched cells (in order)
        unmatched_cells = [c for c in cells if tuple(c) not in matched_cells]

        # Assign available labels to unmatched cells
        for i, cell in enumerate(unmatched_cells):
            if i < len(available_labels):
                result[available_labels[i]] = cell
            else:
                # No more caption labels 鈥?use sequential
                next_letter = chr(ord("a") + len(result))
                result[next_letter] = cell

        return result

