#!/usr/bin/env python
"""Entry point wrapper."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
