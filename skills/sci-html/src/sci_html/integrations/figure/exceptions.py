#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom Exception Classes for Sh_Sci_Fig

Hierarchy:
    ShSciFigError (base)
    鈹溾攢鈹€ PDFError
    鈹?  鈹溾攢鈹€ PDFNotFoundError
    鈹?  鈹溾攢鈹€ PDFCorruptError
    鈹?  鈹斺攢鈹€ PDFEncryptedError
    鈹溾攢鈹€ FigureNotFoundError
    鈹溾攢鈹€ SubfigureNotFoundError
    鈹溾攢鈹€ OCRError
    鈹斺攢鈹€ OutputError
"""


class ShSciFigError(Exception):
    """Base exception for all Sh_Sci_Fig errors."""

    pass


class PDFError(ShSciFigError):
    """Errors related to PDF file operations."""

    pass


class PDFNotFoundError(PDFError):
    """PDF file does not exist at the given path."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"PDF file not found: {path}")


class PDFCorruptError(PDFError):
    """PDF file is corrupt or cannot be parsed."""

    def __init__(self, path: str, reason: str = ""):
        self.path = path
        detail = f" ({reason})" if reason else ""
        super().__init__(f"Cannot open PDF{detail}: {path}")


class PDFEncryptedError(PDFError):
    """PDF file is password-protected."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(
            f"PDF is encrypted/password-protected: {path}. "
            f"Please provide a decrypted version."
        )


class FigureNotFoundError(ShSciFigError):
    """Requested figure number does not exist in the PDF."""

    def __init__(self, figure_num: int, available: list = None):
        self.figure_num = figure_num
        self.available = available or []
        avail_str = (
            f" Available: {', '.join(str(n) for n in self.available)}"
            if self.available
            else " No figures detected in this PDF."
        )
        super().__init__(f"Figure {figure_num} not found.{avail_str}")


class SubfigureNotFoundError(ShSciFigError):
    """Requested sub-figure label does not exist in the figure."""

    def __init__(self, figure_num: int, sublabel: str, available: list = None):
        self.figure_num = figure_num
        self.sublabel = sublabel
        self.available = available or []
        avail_str = f" Available: {', '.join(self.available)}" if self.available else ""
        super().__init__(
            f"Sub-figure '{sublabel}' not found in Figure {figure_num}.{avail_str}"
        )


class OCRError(ShSciFigError):
    """Errors related to OCR processing (Tesseract)."""

    def __init__(self, message: str = "OCR processing failed"):
        super().__init__(message)


class OutputError(ShSciFigError):
    """Errors related to saving output files."""

    def __init__(self, path: str, reason: str = ""):
        self.path = path
        detail = f": {reason}" if reason else ""
        super().__init__(f"Cannot save output to '{path}'{detail}")

