#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility Functions

Shared helpers: logging, path validation, dependency checks.
"""

import os
import sys
import shutil
import logging
import platform
from datetime import datetime


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOGGER_NAME = "Sh_Sci_Fig"
_logger_initialized = False


def setup_logger(
    level=logging.INFO,
    log_file: str = None,
    verbose: bool = False,
) -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        level: base log level (overridden to DEBUG when verbose=True)
        log_file: optional path to a log file (appends)
        verbose: if True, use DEBUG level and add timestamps
    """
    global _logger_initialized
    logger = logging.getLogger(_LOGGER_NAME)

    if verbose:
        level = logging.DEBUG

    # Only add handlers once
    if not _logger_initialized:
        # Console handler
        console = logging.StreamHandler()
        if verbose:
            fmt = "%(asctime)s [%(levelname)s] %(message)s"
            datefmt = "%H:%M:%S"
        else:
            fmt = "[%(levelname)s] %(message)s"
            datefmt = None
        console.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        logger.addHandler(console)

        # File handler (optional)
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
                fh = logging.FileHandler(log_file, encoding="utf-8")
                fh.setFormatter(
                    logging.Formatter(
                        "%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
                logger.addHandler(fh)
            except OSError:
                # Silently skip file logging if path is invalid
                pass

        _logger_initialized = True

    logger.setLevel(level)
    return logger


def get_logger() -> logging.Logger:
    """Return the existing logger (or create a default one)."""
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        return setup_logger()
    return logger


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


def validate_pdf_path(path: str) -> str:
    """
    Validate a PDF file path.

    Returns:
        The absolute path if valid.

    Raises:
        FileNotFoundError: if file does not exist
        ValueError: if file is not a PDF
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")
    if not path.lower().endswith(".pdf"):
        raise ValueError(f"Not a PDF file (expected .pdf extension): {path}")
    return os.path.abspath(path)


def validate_pdf_path_bool(path: str) -> bool:
    """Legacy bool-returning validation (backward compatible)."""
    try:
        validate_pdf_path(path)
        return True
    except (FileNotFoundError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------


def check_tesseract() -> bool:
    """
    Check if Tesseract OCR is available.

    Returns:
        True if tesseract is found, False otherwise.
    """
    if platform.system() == "Windows":
        default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.isfile(default_path):
            return True

    # Check PATH
    if shutil.which("tesseract") is not None:
        return True

    return False


def get_tesseract_version() -> str:
    """Return Tesseract version string, or 'unavailable'."""
    import subprocess

    tesseract_cmd = "tesseract"
    if platform.system() == "Windows":
        default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.isfile(default_path):
            tesseract_cmd = default_path

    try:
        result = subprocess.run(
            [tesseract_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        first_line = result.stdout.strip().split("\n")[0] if result.stdout else ""
        return first_line or "unavailable"
    except Exception:
        return "unavailable"


def check_dependencies() -> list:
    """
    Check all required dependencies are available.

    Returns:
        list of error messages (empty if all OK)
    """
    errors = []

    # Python packages
    required = {
        "fitz": "PyMuPDF",
        "pdfplumber": "pdfplumber",
        "cv2": "opencv-python",
        "PIL": "Pillow",
        "pytesseract": "pytesseract",
        "numpy": "numpy",
    }

    for module, pip_name in required.items():
        try:
            __import__(module)
        except ImportError:
            errors.append(f"Missing package: {pip_name} (pip install {pip_name})")

    # Tesseract binary (optional - graceful degradation if not found)
    if not check_tesseract():
        logger.warning(
            "Tesseract OCR not found (optional). Sub-figure label detection via OCR disabled. "
            "Install: winget install UB-Mannheim.TesseractOCR (Windows) "
            "or apt install tesseract-ocr (Linux)"
        )
        # Note: NOT added to errors - subfigure splitting degrades gracefully

    return errors


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def safe_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Replace characters that are invalid in filenames
    for ch in r'<>:"/\|?*':
        name = name.replace(ch, "_")
    return name.strip()


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

