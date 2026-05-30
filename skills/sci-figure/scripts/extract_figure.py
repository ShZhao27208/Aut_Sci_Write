#!/usr/bin/env python
"""Entry point wrapper."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cli import main  # noqa: E402  (import follows sys.path bootstrap above)

if __name__ == "__main__":
    raise SystemExit(main())
