"""Offline unit tests for sci-figure.

Covers two confirmed bugs without needing a real PDF:
  - BUG 1: caption dedup must key on (figure_type, number) so distinct
    figures that share a number (e.g. "Figure 1" + "Scheme 1") both survive.
  - BUG 5: the sub-figure splitter must not crash on images smaller than its
    internal grid divisors (ZeroDivisionError guards).
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from sci_figure.caption_detector import CaptionDetector
from sci_figure.subfigure_splitter import SubfigureSplitter


def _caption(number: int, figure_type: str, caption_text: str) -> dict:
    return {
        "number": number,
        "page": 0,
        "caption_text": caption_text,
        "bbox_pdf": (0.0, 0.0, 1.0, 1.0),
        "figure_type": figure_type,
        "sublabels": [],
        "column_hint": 0.5,
    }


def _detector_with_captions(captions: list[dict]) -> CaptionDetector:
    """Build a CaptionDetector over a single fake page that yields `captions`."""
    detector = CaptionDetector(SimpleNamespace(pages=[object()]))
    detector._detect_page = lambda page_num: captions  # type: ignore[method-assign]
    return detector


class CaptionDedupTests(unittest.TestCase):
    def test_figure_and_scheme_same_number_both_survive(self):
        # Arrange
        captions = [
            _caption(1, "figure", "Figure 1. A detailed figure caption."),
            _caption(1, "scheme", "Scheme 1. A reaction scheme caption."),
        ]
        detector = _detector_with_captions(captions)

        # Act
        result = detector.detect_all()

        # Assert: keying on number alone would have dropped one of these.
        self.assertEqual(len(result), 2)
        keys = {(c["figure_type"], c["number"]) for c in result}
        self.assertEqual(keys, {("figure", 1), ("scheme", 1)})

    def test_supplementary_and_figure_same_number_both_survive(self):
        captions = [
            _caption(1, "figure", "Figure 1. Main figure."),
            _caption(1, "supplementary", "Supplementary Figure 1. Extra panel."),
        ]
        detector = _detector_with_captions(captions)

        result = detector.detect_all()

        self.assertEqual(len(result), 2)
        types = sorted(c["figure_type"] for c in result)
        self.assertEqual(types, ["figure", "supplementary"])

    def test_same_key_keeps_longest_caption(self):
        short = _caption(1, "figure", "Figure 1.")
        long = _caption(1, "figure", "Figure 1. A much longer and richer caption.")
        detector = _detector_with_captions([short, long])

        result = detector.detect_all()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["caption_text"], long["caption_text"])


class TinyImageSplitGuardTests(unittest.TestCase):
    def test_split_does_not_crash_on_tiny_image(self):
        splitter = SubfigureSplitter(ocr_engine="none")
        for shape in [(2, 2, 3), (1, 5, 3), (5, 1, 3), (2, 8, 3)]:
            tiny = np.zeros(shape, dtype=np.uint8)
            with self.subTest(shape=shape):
                # Must not raise ZeroDivisionError on h // 3 etc.
                result = splitter.split(tiny, ["a", "b", "c"])
                self.assertIsInstance(result, dict)

    def test_grid_split_does_not_crash_on_tiny_image(self):
        splitter = SubfigureSplitter(ocr_engine="none")
        tiny = np.zeros((2, 2, 3), dtype=np.uint8)
        # Direct call into the grid splitter exercises h // nr and w // nc.
        cells = splitter._split_by_grid(tiny, 4)
        # Either None (no gaps found) or a non-empty cell list — never a crash.
        self.assertTrue(cells is None or len(cells) >= 1)

    def test_get_cell_boundaries_does_not_crash_on_tiny_image(self):
        splitter = SubfigureSplitter(ocr_engine="none")
        tiny = np.zeros((2, 2, 3), dtype=np.uint8)
        result = splitter.get_cell_boundaries(tiny, ["a", "b", "c", "d"])
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
