"""
Caption Detector — locate figure captions in PDF pages.

Focused solely on finding "Figure N" / "Fig. N" caption text and their
positions. Does NOT compute figure boundaries (that's the engines' job).

Key improvements over v1:
- No PyMuPDF fulltext fallback (was the main source of false positives)
- Multi-line caption merging
- Column-aware positioning
"""

from __future__ import annotations

import re
import pdfplumber
from sci_figure.utils import get_logger

logger = get_logger()

# Caption patterns (line-start anchored to avoid matching in-text references)
CAPTION_PATTERNS = [
    re.compile(r"^(Fig\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(Figure\s+(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(FIGURE\s+(\d+))\s*[\.:\s]"),
    re.compile(r"^(图\s*(\d+))\s*[\.:\s。]"),
    re.compile(r"^(Scheme\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(方案\s*(\d+))\s*[\.:\s。]"),
    re.compile(r"^(示意图\s*(\d+))\s*[\.:\s。]"),
    re.compile(r"^(Chart\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(Supplementary\s+Fig(?:ure)?\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(Extended\s+Data\s+Fig(?:ure)?\.?\s*(\d+))\s*[\.:\s]", re.IGNORECASE),
    re.compile(r"^(附图\s*(\d+))\s*[\.:\s。]"),
    re.compile(r"^(补充图\s*(\d+))\s*[\.:\s。]"),
]

FIGURE_TYPE_MAP = {
    0: "figure", 1: "figure", 2: "figure", 3: "figure",
    4: "scheme", 5: "scheme", 6: "scheme",
    7: "chart",
    8: "supplementary", 9: "extended_data",
    10: "supplementary", 11: "supplementary",
}

# Sub-label patterns for detecting (a), (b), etc. in caption text
SUBLABEL_PATTERNS = [
    re.compile(r"\(([a-z])\)"),
    re.compile(r"\(([A-Z])\)"),
    re.compile(r"(?:^|[,;]\s*)([a-z])\)"),
]


class CaptionDetector:
    """Detect and locate figure captions in PDF pages."""

    def __init__(self, plumber_doc: pdfplumber.PDF):
        self.doc = plumber_doc

    def detect_all(self) -> list[dict]:
        """
        Scan all pages for figure captions.

        Returns:
            Sorted list of caption dicts:
            [{
                "number": int,
                "page": int,
                "caption_text": str,
                "bbox_pdf": (x0, y0, x1, y1),
                "figure_type": str,
                "sublabels": list[str],
                "column_hint": float,  # x-center of caption
            }, ...]
        """
        all_captions = []

        for page_num in range(len(self.doc.pages)):
            page_captions = self._detect_page(page_num)
            all_captions.extend(page_captions)

        # Deduplicate: same (figure_type, number) → keep the longest caption.
        # Keying on number alone would collide distinct figures that share a
        # number (e.g. "Figure 1" vs "Scheme 1", or "Supplementary Figure 1"
        # vs "Figure 1") and silently drop one.
        unique = {}
        for cap in all_captions:
            key = (cap["figure_type"], cap["number"])
            if key not in unique or len(cap["caption_text"]) > len(unique[key]["caption_text"]):
                unique[key] = cap

        result = sorted(unique.values(), key=lambda c: (c["number"], c["figure_type"]))
        logger.info(f"Detected {len(result)} figure caption(s) total")
        return result

    def _detect_page(self, page_num: int) -> list[dict]:
        """Detect captions on a single page."""
        page = self.doc.pages[page_num]

        try:
            words = page.extract_words(
                x_tolerance=3, y_tolerance=3,
                keep_blank_chars=False, use_text_flow=False,
            )
        except Exception as e:
            logger.warning(f"Text extraction failed on page {page_num}: {e}")
            return []

        if not words:
            return []

        lines = self._group_words_to_lines(words)
        captions = []

        for i, line in enumerate(lines):
            text = line["text"].strip()
            if len(text) < 6:
                continue

            fig_num, pattern_idx = self._match_caption(text)
            if fig_num is None:
                continue

            # Merge continuation lines (caption may span multiple lines)
            full_text = text
            merged_bbox = (line["x0"], line["y0"], line["x1"], line["y1"])

            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j]
                # Stop if next line is another caption or too far away
                if self._match_caption(next_line["text"].strip())[0] is not None:
                    break
                if next_line["y0"] - merged_bbox[3] > 15:
                    break
                # Stop if next line looks like body text (much wider)
                if next_line["x1"] - next_line["x0"] > (merged_bbox[2] - merged_bbox[0]) * 1.5:
                    break

                full_text += " " + next_line["text"].strip()
                merged_bbox = (
                    min(merged_bbox[0], next_line["x0"]),
                    merged_bbox[1],
                    max(merged_bbox[2], next_line["x1"]),
                    next_line["y1"],
                )

            figure_type = FIGURE_TYPE_MAP.get(pattern_idx, "figure")
            sublabels = self._extract_sublabels(full_text)
            x_center = (merged_bbox[0] + merged_bbox[2]) / 2

            captions.append({
                "number": fig_num,
                "page": page_num,
                "caption_text": full_text,
                "bbox_pdf": merged_bbox,
                "figure_type": figure_type,
                "sublabels": sublabels,
                "column_hint": x_center,
            })

        return captions

    def _match_caption(self, text: str) -> tuple[int | None, int | None]:
        """Check if text starts with a figure caption pattern."""
        for idx, pattern in enumerate(CAPTION_PATTERNS):
            m = pattern.match(text.strip())
            if m:
                return int(m.group(2)), idx
        return None, None

    def _group_words_to_lines(self, words: list[dict]) -> list[dict]:
        """Group words into lines by y-coordinate proximity."""
        if not words:
            return []

        sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
        lines = []
        current_line = [sorted_words[0]]
        line_y = sorted_words[0]["top"]
        y_tolerance = 3.0

        for w in sorted_words[1:]:
            if abs(w["top"] - line_y) <= y_tolerance:
                current_line.append(w)
            else:
                lines.append(self._merge_line(current_line))
                current_line = [w]
                line_y = w["top"]

        if current_line:
            lines.append(self._merge_line(current_line))

        return lines

    def _merge_line(self, words: list[dict]) -> dict:
        """Merge words into a single line dict."""
        words_sorted = sorted(words, key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in words_sorted)
        return {
            "text": text,
            "x0": min(w["x0"] for w in words_sorted),
            "y0": min(w["top"] for w in words_sorted),
            "x1": max(w["x1"] for w in words_sorted),
            "y1": max(w["bottom"] for w in words_sorted),
        }

    def _extract_sublabels(self, caption_text: str) -> list[str]:
        """Extract sub-figure labels from caption text.

        Only returns labels that form a plausible consecutive sequence
        starting from 'a' (e.g., a,b,c,d — not random scattered letters).
        """
        all_matches = set()
        for pattern in SUBLABEL_PATTERNS:
            matches = pattern.findall(caption_text)
            all_matches.update(m.lower() for m in matches)

        if not all_matches:
            return []

        # Filter: only keep letters that form a consecutive run from 'a'
        sorted_labels = sorted(all_matches)
        if not sorted_labels or sorted_labels[0] != 'a':
            return []

        consecutive = []
        for i, label in enumerate(sorted_labels):
            if label == chr(ord('a') + i):
                consecutive.append(label)
            else:
                break

        return consecutive if len(consecutive) >= 2 else []
