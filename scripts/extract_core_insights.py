#!/usr/bin/env python3
"""Compatibility wrapper for the sci-extract CLI."""

from pathlib import Path
import runpy


TARGET = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sci-extract"
    / "extract_core_insights.py"
)


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
