"""
PDF Parser — render pages and extract text with coordinates.

Foundation module shared by all engines. Wraps PyMuPDF (rendering) and
pdfplumber (text extraction) with coordinate conversion utilities.
"""

from __future__ import annotations

import os
import numpy as np
import fitz
import pdfplumber
from sci_figure.utils import get_logger
from sci_figure.exceptions import PDFNotFoundError, PDFCorruptError, PDFEncryptedError

logger = get_logger()


class PDFParser:
    """Parse PDF: render pages, extract text, coordinate conversion."""

    def __init__(self, pdf_path: str, dpi: int = 600):
        self.pdf_path = os.path.abspath(pdf_path)
        self.dpi = dpi
        self._scale = dpi / 72.0
        self._closed = False
        self._page_cache: dict[int, np.ndarray] = {}

        if not os.path.isfile(self.pdf_path):
            raise PDFNotFoundError(self.pdf_path)

        try:
            self.fitz_doc = fitz.open(self.pdf_path)
        except Exception as e:
            raise PDFCorruptError(self.pdf_path, str(e)) from e

        if self.fitz_doc.is_encrypted:
            self.fitz_doc.close()
            raise PDFEncryptedError(self.pdf_path)

        if len(self.fitz_doc) == 0:
            self.fitz_doc.close()
            raise PDFCorruptError(self.pdf_path, "0 pages")

        try:
            self.plumber_doc = pdfplumber.open(self.pdf_path)
        except Exception as e:
            self.fitz_doc.close()
            raise PDFCorruptError(self.pdf_path, f"pdfplumber: {e}") from e

        logger.info(f"PDF: {self.page_count} pages, {dpi} DPI")

    @property
    def page_count(self) -> int:
        return len(self.fitz_doc)

    def render_page(self, page_num: int) -> np.ndarray:
        """Render page to RGB numpy array at configured DPI (cached)."""
        self._check(page_num)
        if page_num in self._page_cache:
            return self._page_cache[page_num]

        page = self.fitz_doc[page_num]
        mat = fitz.Matrix(self._scale, self._scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3
        )
        self._page_cache[page_num] = img
        return img

    def get_page_size(self, page_num: int) -> tuple[float, float]:
        """Page size in PDF points (72 DPI)."""
        self._check(page_num)
        rect = self.fitz_doc[page_num].rect
        return (rect.width, rect.height)

    def pdf_to_pixel(self, pdf_coords: tuple) -> tuple[int, int, int, int]:
        """Convert PDF points → pixel coordinates."""
        x0, y0, x1, y1 = pdf_coords
        return (
            int(x0 * self._scale),
            int(y0 * self._scale),
            int(x1 * self._scale),
            int(y1 * self._scale),
        )

    def pixel_to_pdf(self, pixel_coords: tuple) -> tuple[float, float, float, float]:
        """Convert pixel coordinates → PDF points."""
        x0, y0, x1, y1 = pixel_coords
        return (
            x0 / self._scale,
            y0 / self._scale,
            x1 / self._scale,
            y1 / self._scale,
        )

    def crop_region(self, page_num: int, bbox_pdf: tuple) -> np.ndarray:
        """Crop a region from a rendered page given PDF-space coordinates."""
        page_img = self.render_page(page_num)
        h, w = page_img.shape[:2]
        x0, y0, x1, y1 = self.pdf_to_pixel(bbox_pdf)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0:
            return np.array([], dtype=np.uint8)
        return page_img[y0:y1, x0:x1].copy()

    def _check(self, page_num: int):
        if self._closed:
            raise RuntimeError("PDFParser is closed")
        if page_num < 0 or page_num >= self.page_count:
            raise ValueError(f"Page {page_num} out of range [0, {self.page_count - 1}]")

    def close(self):
        if self._closed:
            return
        self._page_cache.clear()
        try:
            self.fitz_doc.close()
        except Exception:
            pass
        try:
            self.plumber_doc.close()
        except Exception:
            pass
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False
