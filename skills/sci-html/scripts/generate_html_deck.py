#!/usr/bin/env python3
"""Compatibility wrapper for the sci-html CLI."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sci_html.cli import main  # noqa: E402  (import follows sys.path bootstrap above)

if __name__ == "__main__":
    raise SystemExit(main())
