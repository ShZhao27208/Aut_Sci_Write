#!/usr/bin/env python3
"""Compatibility wrapper for the sci-zotero CLI."""

from pathlib import Path
import runpy


TARGET = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sci-zotero"
    / "zotero.py"
)


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
