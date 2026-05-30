"""Shared path bootstrap for tests.

Importing this module ensures ``src/`` (where the ``sci_html`` package lives)
is on ``sys.path`` so tests run from the repo root WITHOUT an editable install.

Works for both runners:
  - ``python -m unittest discover`` imports each ``test_*.py`` directly, so each
    test module imports this helper at its top.
  - ``pytest`` prepends the tests directory to ``sys.path``, so the same import
    resolves (and ``conftest.py`` provides a redundant safety net).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
