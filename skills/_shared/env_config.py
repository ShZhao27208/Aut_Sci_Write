"""Unified .env configuration for the Aut_Sci_Write skill suite.

All API keys are stored in a single file: ~/.aut_sci_write/.env
This module auto-creates the directory and a template .env on first access.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict

ENV_DIR = Path(os.environ.get("AUT_SCI_WRITE_ENV_DIR", str(Path.home() / ".aut_sci_write")))
ENV_FILE = ENV_DIR / ".env"

ENV_TEMPLATE = """\
# ═══════════════════════════════════════════════════════════════
# Aut_Sci_Write — Unified API Key Configuration
# ═══════════════════════════════════════════════════════════════
# All skills in the Aut_Sci_Write suite read from this single file.
# Fill in the keys you need; leave others blank.

# ─── sci-search ───────────────────────────────────────────────
# Web of Science Starter API (free): https://developer.clarivate.com/apis/wos-starter
WOS_API_KEY=
# Elsevier Scopus API (free): https://dev.elsevier.com/
SCOPUS_API_KEY=
# Springer Nature Metadata API (free): https://dev.springernature.com/
SPRINGER_API_KEY=
# Springer Nature Open Access API (falls back to SPRINGER_API_KEY)
SPRINGER_OA_API_KEY=
# Semantic Scholar (optional, for higher rate limits): https://www.semanticscholar.org/product/api#api-key
SEMANTIC_SCHOLAR_API_KEY=
# OpenAlex polite pool (optional, just your email)
OPENALEX_EMAIL=

# ─── sci-download ─────────────────────────────────────────────
# Elsevier Article Retrieval API (free): https://dev.elsevier.com/
ELSEVIER_API_KEY=
ELSEVIER_INSTTOKEN=
# IEEE Xplore API (free tier): https://developer.ieee.org/
IEEE_API_KEY=
# Unpaywall (just your email): https://unpaywall.org/products/api
UNPAYWALL_EMAIL=

# ─── sci-search & sci-download (shared) ──────────────────────
# NCBI/PubMed E-utilities (free): https://www.ncbi.nlm.nih.gov/account/settings/
NCBI_API_KEY=
NCBI_EMAIL=

# ─── sci-zotero ──────────────────────────────────────────────
# Zotero API key: https://www.zotero.org/settings/keys/new
ZOTERO_API_KEY=
# Numeric user ID (for personal library)
ZOTERO_USER_ID=
# Numeric group ID (for group library, use instead of USER_ID)
ZOTERO_GROUP_ID=

# ─── sci-ppt (optional translation) ──────────────────────────
# Moonshot API (only needed for --translate): https://platform.moonshot.cn/
MOONSHOT_API_KEY=
"""


def _parse_env(path: Path) -> Dict[str, str]:
    """Parse a .env file into a dict. Ignores comments and empty lines."""
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)$", line)
            if m:
                env[m.group(1)] = m.group(2).strip().strip("\"'")
    except OSError:
        pass
    return env


def ensure_env_dir() -> Path:
    """Create ~/.aut_sci_write/ and a template .env if they don't exist."""
    ENV_DIR.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    return ENV_DIR


def load_env() -> Dict[str, str]:
    """Load all key-value pairs from the unified .env file."""
    ensure_env_dir()
    return _parse_env(ENV_FILE)


def get_env_value(name: str, default: str = "") -> str:
    """Get a config value: unified .env > environment variable > default."""
    env = load_env()
    return env.get(name) or os.environ.get(name, default)


def write_env_key(key: str, value: str) -> None:
    """Set a key in the unified .env file, preserving other entries."""
    ensure_env_dir()
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^{re.escape(key)}\s*=")
    found = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
