#!/usr/bin/env python3
"""Compatibility wrapper for the sci-zotero CLI."""

import runpy
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sci-zotero"
    / "zotero.py"
)


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
