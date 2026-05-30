"""Pytest/unittest bootstrap so ``sci_html`` is importable without installation.

Placed at the sci-html skill root so ``python -m pytest tests/`` (run from this
directory) auto-discovers it. The ``src`` layout means the package is not on
``sys.path`` by default; this inserts it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
