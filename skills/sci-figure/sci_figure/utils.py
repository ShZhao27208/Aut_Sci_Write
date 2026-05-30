"""Shared utilities: logging, validation, dependency checks."""

from __future__ import annotations

import logging
import os
import shutil

_LOGGER_NAME = "sci_figure"
_logger_initialized = False


def setup_logger(level=logging.INFO) -> logging.Logger:
    global _logger_initialized
    logger = logging.getLogger(_LOGGER_NAME)
    if not _logger_initialized:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(console)
        _logger_initialized = True
    logger.setLevel(level)
    return logger


def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        return setup_logger()
    return logger


def validate_pdf_path(path: str) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")
    if not path.lower().endswith(".pdf"):
        raise ValueError(f"Not a PDF file: {path}")
    return os.path.abspath(path)


def check_tesseract() -> bool:
    # Honour an explicit override first (documented as TESSERACT_CMD in README).
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd and os.path.isfile(cmd):
        return True
    return shutil.which("tesseract") is not None


def check_easyocr() -> bool:
    try:
        import easyocr  # noqa: F401
        return True
    except ImportError:
        return False
