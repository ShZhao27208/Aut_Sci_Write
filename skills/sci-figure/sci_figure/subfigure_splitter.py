"""
Subfigure Splitter v2 — OCR-first splitting with CV fallback.

Strategy (priority order):
1. OCR label detection → infer cell boundaries from label positions (when OCR available)
2. CV connected-component splitting (fallback when OCR unavailable or insufficient)
3. Grid detection (if CV components don't match expected count)
4. Caption count inference (last resort: equal-divide by label count)
"""

from __future__ import annotations

import os
import re
import numpy as np
import cv2
from sci_figure.utils import get_logger, check_tesseract, check_easyocr

logger = get_logger()


class SubfigureSplitter:
    """Split composite figures into labeled sub-figures."""

    _easyocr_reader = None

    def __init__(self, ocr_engine: str = "tesseract", easyocr_model_dir: str = None):
        """
        Args:
            ocr_engine: "tesseract", "easyocr", or "none"
            easyocr_model_dir: path to local EasyOCR model storage. Falls back to
                the EASYOCR_MODEL_DIR env var, then to EasyOCR's own default
                (None lets easyocr manage its own cache).
        """
        self.ocr_engine = ocr_engine
        self.easyocr_model_dir = easyocr_model_dir or os.environ.get("EASYOCR_MODEL_DIR")

    def split(
        self,
        figure_image: np.ndarray,
        sublabels: list[str],
        target_label: str = None,
    ) -> dict[str, np.ndarray]:
        """
        Split a figure into sub-figures.

        Args:
            figure_image: RGB numpy array of the full figure
            sublabels: expected labels from caption (e.g., ["a","b","c","d"])
            target_label: if set, only extract this one sub-figure

        Returns:
            {"a": np.ndarray, "b": np.ndarray, ...}
            or {"a": np.ndarray} if target_label="a"
        """
        if figure_image is None or figure_image.size == 0:
            return {}

        n_expected = len(sublabels) if sublabels else 0
        h, w = figure_image.shape[:2]

        labeled = None

        # Strategy 1: OCR-first (when OCR engine available)
        if self.ocr_engine != "none" and n_expected >= 2:
            labeled = self._split_by_ocr(figure_image, sublabels)

        # Strategy 2: CV fallback
        if not labeled or len(labeled) < 2:
            cells = self._split_by_components(figure_image, n_expected)

            if n_expected >= 2 and len(cells) != n_expected:
                grid_cells = self._split_by_grid(figure_image, n_expected)
                if grid_cells and len(grid_cells) == n_expected:
                    cells = grid_cells

            if not cells or len(cells) < 2:
                logger.warning("Could not split figure into sub-figures")
                return {}

            labeled = self._assign_labels(figure_image, cells, sublabels)

        # Crop and return
        result = {}
        for label, bbox in labeled.items():
            if target_label and label != target_label.lower():
                continue
            x0, y0, x1, y1 = [int(v) for v in bbox]
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(w, x1), min(h, y1)
            if x1 > x0 and y1 > y0:
                result[label] = figure_image[y0:y1, x0:x1].copy()

        return result

    def get_cell_boundaries(
        self, figure_image: np.ndarray, sublabels: list[str]
    ) -> dict[str, tuple]:
        """Return labeled bounding boxes without cropping (for annotation)."""
        n_expected = len(sublabels) if sublabels else 0

        # OCR-first when available
        if self.ocr_engine != "none" and n_expected >= 2:
            labeled = self._split_by_ocr(figure_image, sublabels)
            if labeled and len(labeled) >= 2:
                return labeled

        # CV fallback
        cells = self._split_by_components(figure_image, n_expected)

        if n_expected >= 2 and len(cells) != n_expected:
            grid_cells = self._split_by_grid(figure_image, n_expected)
            if grid_cells and len(grid_cells) == n_expected:
                cells = grid_cells

        if not cells or len(cells) < 2:
            return {}

        return self._assign_labels(figure_image, cells, sublabels)

    # ========================================================================
    # Strategy 1: Connected-component splitting
    # ========================================================================

    def _split_by_components(
        self, image: np.ndarray, n_expected: int = 0
    ) -> list[tuple]:
        """
        Find sub-figure regions using connected-component analysis.

        Unlike v1's white-space projection, this finds actual content blobs,
        which works even with colored backgrounds or thin separators.
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Adaptive threshold
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )

        # Morphological closing to merge content within each sub-figure
        kw = max(15, int(w * 0.04))
        kh = max(15, int(h * 0.04))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(
            closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter by minimum size
        min_area = h * w * 0.05
        cells = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            if cw * ch >= min_area and cw > w * 0.1 and ch > h * 0.1:
                cells.append((x, y, x + cw, y + ch))

        # Sort in reading order (top-to-bottom, left-to-right).
        # Guard against tiny images where h // 3 == 0 would raise ZeroDivisionError.
        row_band = max(1, h // 3)
        cells.sort(key=lambda c: (c[1] // row_band, c[0]))

        return cells

    # ========================================================================
    # Strategy 2: Grid detection
    # ========================================================================

    def _split_by_grid(
        self, image: np.ndarray, n_expected: int
    ) -> list[tuple] | None:
        """
        Try to split image into a regular grid matching n_expected cells.

        Tests all valid (rows, cols) factorizations and picks the one
        with the best white-gap alignment.
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Find factorizations
        factorizations = []
        for nr in range(1, n_expected + 1):
            if n_expected % nr == 0:
                nc = n_expected // nr
                factorizations.append((nr, nc))

        best_cells = None
        best_score = -1

        for nr, nc in factorizations:
            # Check if horizontal splits exist at expected positions
            h_score = self._check_grid_gaps(gray, axis="horizontal", n_splits=nr - 1)
            v_score = self._check_grid_gaps(gray, axis="vertical", n_splits=nc - 1)
            score = h_score + v_score

            if score > best_score:
                best_score = score
                # Generate cells for this grid.
                # Guard against tiny images where h // nr or w // nc == 0.
                cells = []
                cell_h = max(1, h // nr)
                cell_w = max(1, w // nc)
                for r in range(nr):
                    for c in range(nc):
                        cells.append((
                            c * cell_w,
                            r * cell_h,
                            (c + 1) * cell_w,
                            (r + 1) * cell_h,
                        ))
                best_cells = cells

        # Only return if we found reasonable gaps
        if best_score > 0.3:
            return best_cells
        return None

    def _check_grid_gaps(
        self, gray: np.ndarray, axis: str, n_splits: int
    ) -> float:
        """Score how well the image has white gaps at grid positions."""
        if n_splits == 0:
            return 0.5  # neutral score for no-split dimension

        h, w = gray.shape
        length = h if axis == "horizontal" else w

        # Expected split positions
        positions = [(i + 1) * length // (n_splits + 1) for i in range(n_splits)]

        # Check whiteness around each expected position
        scores = []
        for pos in positions:
            band_start = max(0, pos - 5)
            band_end = min(length, pos + 5)

            if axis == "horizontal":
                band = gray[band_start:band_end, :]
            else:
                band = gray[:, band_start:band_end]

            white_ratio = np.mean(band > 240)
            scores.append(white_ratio)

        return float(np.mean(scores)) if scores else 0.0

    # ========================================================================
    # Strategy 0: OCR-first splitting (when OCR available)
    # ========================================================================

    def _split_by_ocr(
        self, image: np.ndarray, sublabels: list[str]
    ) -> dict[str, tuple] | None:
        """
        Detect sub-figure labels via OCR and infer cell boundaries from
        their positions using midpoint cutting.

        Returns labeled bboxes directly, or None if OCR doesn't find enough.
        """
        n_expected = len(sublabels)
        if n_expected < 2:
            return None

        ocr_labels = self._ocr_detect(image, sublabels)
        if not ocr_labels or len(ocr_labels) < max(2, n_expected // 2):
            return None

        h, w = image.shape[:2]

        # Sort by reading order: cluster into rows by y, then sort by x
        sorted_labels = self._sort_labels_reading_order(ocr_labels, h)

        # Infer grid layout from label positions
        rows = self._cluster_rows(sorted_labels, h)
        n_rows = len(rows)
        n_cols = max(len(row) for row in rows) if rows else 1

        # Compute row boundaries (y splits)
        y_splits = [0]
        for i in range(len(rows) - 1):
            row_bottom = max(lbl["position"][1] for lbl in rows[i])
            next_row_top = min(lbl["position"][1] for lbl in rows[i + 1])
            y_splits.append((row_bottom + next_row_top) // 2)
        y_splits.append(h)

        # For each row, compute column boundaries (x splits)
        labeled = {}
        for row_idx, row in enumerate(rows):
            row_sorted = sorted(row, key=lambda lbl: lbl["position"][0])
            x_splits = [0]
            for i in range(len(row_sorted) - 1):
                curr_x = row_sorted[i]["position"][0]
                next_x = row_sorted[i + 1]["position"][0]
                x_splits.append((curr_x + next_x) // 2)
            x_splits.append(w)

            for col_idx, lbl in enumerate(row_sorted):
                x0 = x_splits[col_idx]
                x1 = x_splits[col_idx + 1]
                y0 = y_splits[row_idx]
                y1 = y_splits[row_idx + 1]
                labeled[lbl["label"]] = (x0, y0, x1, y1)

        if len(labeled) < 2:
            return None

        logger.info(
            f"OCR-first split: found {len(labeled)} cells "
            f"({n_rows}x{n_cols} layout)"
        )
        return labeled

    def _sort_labels_reading_order(
        self, labels: list[dict], img_height: int
    ) -> list[dict]:
        """Sort OCR labels in reading order (top-to-bottom rows, left-to-right)."""
        row_threshold = img_height * 0.15
        sorted_by_y = sorted(labels, key=lambda lbl: lbl["position"][1])

        rows: list[list[dict]] = []
        current_row: list[dict] = [sorted_by_y[0]]

        for lbl in sorted_by_y[1:]:
            if lbl["position"][1] - current_row[0]["position"][1] > row_threshold:
                rows.append(current_row)
                current_row = [lbl]
            else:
                current_row.append(lbl)
        rows.append(current_row)

        result = []
        for row in rows:
            result.extend(sorted(row, key=lambda lbl: lbl["position"][0]))
        return result

    def _cluster_rows(
        self, sorted_labels: list[dict], img_height: int
    ) -> list[list[dict]]:
        """Cluster labels into rows based on y-coordinate proximity."""
        if not sorted_labels:
            return []

        row_threshold = img_height * 0.15
        rows: list[list[dict]] = [[sorted_labels[0]]]

        for lbl in sorted_labels[1:]:
            last_row_y = np.mean([l["position"][1] for l in rows[-1]])
            if abs(lbl["position"][1] - last_row_y) > row_threshold:
                rows.append([lbl])
            else:
                rows[-1].append(lbl)

        return rows

    # ========================================================================
    # Label assignment
    # ========================================================================

    def _assign_labels(
        self,
        image: np.ndarray,
        cells: list[tuple],
        caption_labels: list[str],
    ) -> dict[str, tuple]:
        """
        Assign labels to cells.

        Priority:
        1. If caption labels match cell count → direct reading-order assignment
        2. Try OCR to detect labels in image
        3. Fallback to sequential letters
        """
        n_cells = len(cells)

        # Best case: caption labels match
        if caption_labels and len(caption_labels) == n_cells:
            return {caption_labels[i]: cells[i] for i in range(n_cells)}

        # Try OCR if available
        if self.ocr_engine != "none":
            ocr_labels = self._ocr_detect(image, caption_labels)
            if ocr_labels:
                matched = self._match_ocr_to_cells(ocr_labels, cells)
                if len(matched) == n_cells:
                    return matched

        # Fallback: use caption labels in reading order (pad if needed)
        if caption_labels:
            labels = caption_labels[:n_cells]
            while len(labels) < n_cells:
                labels.append(chr(ord('a') + len(labels)))
            return {labels[i]: cells[i] for i in range(n_cells)}

        # Last resort: sequential letters
        return {chr(ord('a') + i): cells[i] for i in range(min(n_cells, 26))}

    def _ocr_detect(
        self, image: np.ndarray, whitelist: list[str] = None
    ) -> list[dict]:
        """Detect sub-figure labels via OCR (Tesseract or EasyOCR)."""
        if self.ocr_engine == "tesseract" and check_tesseract():
            return self._ocr_tesseract(image, whitelist)
        elif self.ocr_engine == "easyocr" and check_easyocr():
            return self._ocr_easyocr(image, whitelist)
        return []

    def _ocr_tesseract(self, image: np.ndarray, whitelist: list[str] = None) -> list[dict]:
        """Tesseract-based label detection."""
        import pytesseract

        # Honour an explicit binary override (documented as TESSERACT_CMD in
        # README). When unset, let pytesseract use its own PATH lookup.
        tess_cmd = os.environ.get("TESSERACT_CMD")
        if tess_cmd:
            pytesseract.pytesseract.tesseract_cmd = tess_cmd

        img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        label_re = re.compile(r"\(?([a-zA-Z])\)?")
        candidates = {}

        for psm in [6, 11]:
            config = f"--psm {psm} -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz()"
            try:
                data = pytesseract.image_to_data(
                    img_bgr, output_type=pytesseract.Output.DICT, config=config
                )
            except Exception:
                continue

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])
                if conf < 30 or not text:
                    continue

                m = label_re.fullmatch(text)
                if not m:
                    continue

                letter = m.group(1).lower()
                if whitelist and letter not in whitelist:
                    continue

                x, y = data["left"][i], data["top"][i]
                w, h = data["width"][i], data["height"][i]
                if w > 200 or h > 200 or w < 8 or h < 8:
                    continue

                if letter not in candidates or conf > candidates[letter]["conf"]:
                    candidates[letter] = {
                        "label": letter,
                        "position": (x + w // 2, y + h // 2),
                        "conf": conf,
                    }

        return [v for v in candidates.values() if v["conf"] >= 35]

    def _ocr_easyocr(self, image: np.ndarray, whitelist: list[str] = None) -> list[dict]:
        """EasyOCR-based label detection with cached reader."""
        if SubfigureSplitter._easyocr_reader is None:
            import easyocr
            logger.info(f"Loading EasyOCR (models: {self.easyocr_model_dir})")
            SubfigureSplitter._easyocr_reader = easyocr.Reader(
                ["en"],
                model_storage_directory=self.easyocr_model_dir,
                gpu=False,
                verbose=False,
            )

        results = SubfigureSplitter._easyocr_reader.readtext(image)

        label_re = re.compile(r"\(?([a-zA-Z])\)?")
        candidates = {}

        for bbox, text, conf in results:
            m = label_re.fullmatch(text.strip())
            if not m:
                continue

            letter = m.group(1).lower()
            if whitelist and letter not in whitelist:
                continue

            cx = int((bbox[0][0] + bbox[2][0]) / 2)
            cy = int((bbox[0][1] + bbox[2][1]) / 2)

            if letter not in candidates or conf > candidates[letter]["conf"]:
                candidates[letter] = {
                    "label": letter,
                    "position": (cx, cy),
                    "conf": conf,
                }

        return [v for v in candidates.values() if v["conf"] >= 0.3]

    def _match_ocr_to_cells(
        self, ocr_labels: list[dict], cells: list[tuple]
    ) -> dict[str, tuple]:
        """Match OCR-detected labels to cells by spatial containment."""
        matched = {}
        for label_info in ocr_labels:
            lx, ly = label_info["position"]
            for cell in cells:
                x0, y0, x1, y1 = cell
                if x0 <= lx <= x1 and y0 <= ly <= y1:
                    matched[label_info["label"]] = cell
                    break
        return matched
