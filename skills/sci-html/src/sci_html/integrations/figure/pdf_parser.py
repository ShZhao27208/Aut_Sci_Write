#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF Parser Module

Responsibilities:
- Render PDF pages to high-quality images via PyMuPDF (fitz)
- Extract text with coordinates via pdfplumber
- Coordinate system conversion between PDF and pixel space
- Graceful handling of corrupt, encrypted, or malformed PDFs
"""

import os
import fitz  # PyMuPDF
import pdfplumber
import numpy as np
from .utils import get_logger
from .exceptions import PDFNotFoundError, PDFCorruptError, PDFEncryptedError

logger = get_logger()


class PDFParser:
    """Parse PDF files: render pages to images and extract text with positions."""

    def __init__(self, pdf_path: str, dpi: int = 600):
        self.pdf_path = os.path.abspath(pdf_path)
        self.dpi = dpi
        self._scale = dpi / 72.0  # PDF default is 72 DPI
        self._closed = False

        # --- Validate file exists ---
        if not os.path.isfile(self.pdf_path):
            raise PDFNotFoundError(self.pdf_path)

        # --- Open with PyMuPDF (fitz) ---
        try:
            self._fitz_doc = fitz.open(self.pdf_path)
        except Exception as e:
            raise PDFCorruptError(self.pdf_path, str(e)) from e

        # Check for encryption
        if self._fitz_doc.is_encrypted:
            self._fitz_doc.close()
            raise PDFEncryptedError(self.pdf_path)

        # Check for zero pages
        if len(self._fitz_doc) == 0:
            self._fitz_doc.close()
            raise PDFCorruptError(self.pdf_path, "PDF contains 0 pages")

        # --- Open with pdfplumber ---
        try:
            self._plumber_doc = pdfplumber.open(self.pdf_path)
        except Exception as e:
            self._fitz_doc.close()
            raise PDFCorruptError(self.pdf_path, f"pdfplumber: {e}") from e

        logger.info(
            f"PDF loaded: {self.get_page_count()} pages, "
            f"rendering at {dpi} DPI (scale={self._scale:.2f}x)"
        )

    def get_page_count(self) -> int:
        """Return total number of pages in the PDF."""
        return len(self._fitz_doc)

    def render_page(self, page_num: int) -> np.ndarray:
        """
        Render a PDF page to a numpy array (RGB) at configured DPI.

        Automatically handles rotated pages by applying the page's
        built-in rotation to the rendering matrix.

        Args:
            page_num: 0-indexed page number

        Returns:
            numpy array of shape (height, width, 3), dtype uint8

        Raises:
            ValueError: if page_num is out of range
        """
        self._check_open()
        self._validate_page_num(page_num)

        page = self._fitz_doc[page_num]
        mat = fitz.Matrix(self._scale, self._scale)

        # Handle rotated pages: fitz auto-applies rotation via get_pixmap
        # but log it for debugging
        rotation = page.rotation
        if rotation != 0:
            logger.debug(f"Page {page_num} has {rotation}掳 rotation (auto-handled)")

        try:
            pix = page.get_pixmap(matrix=mat, alpha=False)
        except Exception as e:
            raise PDFCorruptError(
                self.pdf_path, f"Failed to render page {page_num}: {e}"
            ) from e

        # Convert fitz Pixmap to numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3
        )

        logger.info(
            f"Rendered page {page_num}: {pix.width}x{pix.height} px ({self.dpi} DPI)"
        )
        return img

    def get_page_size(self, page_num: int) -> tuple:
        """
        Get the PDF page size in points (72 DPI).

        Args:
            page_num: 0-indexed page number

        Returns:
            (width_pt, height_pt) in PDF points
        """
        self._check_open()
        self._validate_page_num(page_num)
        page = self._fitz_doc[page_num]
        rect = page.rect
        return (rect.width, rect.height)

    def extract_text_with_positions(self, page_num: int) -> list:
        """
        Extract text words with bounding box coordinates from a page.

        Uses pdfplumber for accurate text positioning. Coordinates are in
        PDF point space (72 DPI, origin at top-left).

        Args:
            page_num: 0-indexed page number

        Returns:
            list of dicts, each with:
                {
                    "text": str,
                    "x0": float,   # left edge (PDF points)
                    "y0": float,   # top edge (PDF points)
                    "x1": float,   # right edge (PDF points)
                    "y1": float,   # bottom edge (PDF points)
                }
        """
        self._check_open()
        self._validate_page_num(page_num)

        page = self._plumber_doc.pages[page_num]

        try:
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=False,
            )
        except Exception as e:
            logger.warning(
                f"Text extraction failed on page {page_num}: {e}. "
                f"Returning empty word list."
            )
            return []

        result = []
        for w in words:
            result.append(
                {
                    "text": w["text"],
                    "x0": float(w["x0"]),
                    "y0": float(w["top"]),
                    "x1": float(w["x1"]),
                    "y1": float(w["bottom"]),
                }
            )

        logger.info(f"Extracted {len(result)} text words from page {page_num}")
        return result

    def extract_lines(self, page_num: int) -> list:
        """
        Extract text grouped by lines from a page via pdfplumber.

        Returns:
            list of dicts, each with:
                {
                    "text": str,         # full line text
                    "x0": float,
                    "y0": float,
                    "x1": float,
                    "y1": float,
                    "words": list,       # individual words in this line
                }
        """
        words = self.extract_text_with_positions(page_num)
        if not words:
            return []

        # Group words into lines by y-coordinate proximity
        sorted_words = sorted(words, key=lambda w: (w["y0"], w["x0"]))
        lines = []
        current_line = [sorted_words[0]]
        line_y = sorted_words[0]["y0"]

        y_tolerance = 3.0  # points

        for w in sorted_words[1:]:
            if abs(w["y0"] - line_y) <= y_tolerance:
                current_line.append(w)
            else:
                lines.append(self._merge_words_to_line(current_line))
                current_line = [w]
                line_y = w["y0"]

        if current_line:
            lines.append(self._merge_words_to_line(current_line))

        return lines

    def _merge_words_to_line(self, words: list) -> dict:
        """Merge a list of words into a single line dict."""
        words_sorted = sorted(words, key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in words_sorted)
        return {
            "text": text,
            "x0": min(w["x0"] for w in words_sorted),
            "y0": min(w["y0"] for w in words_sorted),
            "x1": max(w["x1"] for w in words_sorted),
            "y1": max(w["y1"] for w in words_sorted),
            "words": words_sorted,
        }

    def pdf_to_pixel_coords(self, pdf_coords: tuple, page_num: int = None) -> tuple:
        """
        Convert PDF coordinate space (72 DPI) to pixel coordinates at current DPI.

        Args:
            pdf_coords: (x0, y0, x1, y1) in PDF points
            page_num: not used, kept for interface consistency

        Returns:
            (x0, y0, x1, y1) in pixel coordinates
        """
        x0, y0, x1, y1 = pdf_coords
        return (
            int(x0 * self._scale),
            int(y0 * self._scale),
            int(x1 * self._scale),
            int(y1 * self._scale),
        )

    def pixel_to_pdf_coords(self, pixel_coords: tuple) -> tuple:
        """
        Convert pixel coordinates back to PDF coordinate space.

        Args:
            pixel_coords: (x0, y0, x1, y1) in pixels

        Returns:
            (x0, y0, x1, y1) in PDF points
        """
        x0, y0, x1, y1 = pixel_coords
        return (
            x0 / self._scale,
            y0 / self._scale,
            x1 / self._scale,
            y1 / self._scale,
        )

    # --- Internal helpers ---

    def _validate_page_num(self, page_num: int):
        """Raise ValueError if page_num is out of range."""
        if page_num < 0 or page_num >= self.get_page_count():
            raise ValueError(
                f"Page {page_num} out of range [0, {self.get_page_count() - 1}]"
            )

    def _check_open(self):
        """Raise RuntimeError if the parser has been closed."""
        if self._closed:
            raise RuntimeError(
                "PDFParser is closed. Cannot perform operations on a closed parser."
            )

    def close(self):
        """Release PDF file handles (safe to call multiple times)."""
        if self._closed:
            return
        try:
            if self._fitz_doc:
                self._fitz_doc.close()
        except Exception:
            pass
        try:
            if self._plumber_doc:
                self._plumber_doc.close()
        except Exception:
            pass
        self._closed = True
        logger.debug("PDF parser closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

