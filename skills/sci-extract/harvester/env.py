"""Bridge to the suite-wide `_shared/env_config.py` credential store.

sci-extract keeps its own fetchers but shares the single `~/.aut_sci_write/.env`
file with every other skill in the suite, so users configure keys once.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

_SKILLS_ROOT = Path(__file__).resolve().parents[2]

if str(_SKILLS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILLS_ROOT))

try:
    from _shared.env_config import ENV_FILE, get_env_value, load_env
except ImportError:  # pragma: no cover - standalone fallback
    ENV_FILE = Path.home() / ".aut_sci_write" / ".env"

    def load_env() -> dict[str, str]:
        env: dict[str, str] = {}
        if not ENV_FILE.exists():
            return env
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip("\"'")
        return env

    def get_env_value(name: str, default: str = "") -> str:
        return load_env().get(name) or os.environ.get(name, default)


# Every credential sci-extract can make use of, grouped by the source it unlocks.
SOURCE_CREDENTIALS: dict[str, tuple[str, ...]] = {
    "crossref": (),
    "openalex": ("OPENALEX_EMAIL",),
    "semantic_scholar": ("SEMANTIC_SCHOLAR_API_KEY",),
    "pubmed": ("NCBI_API_KEY", "NCBI_EMAIL"),
    "europepmc": (),
    "unpaywall": ("UNPAYWALL_EMAIL",),
    "arxiv": (),
    "wos": ("WOS_API_KEY",),
    "scopus": ("SCOPUS_API_KEY",),
    "springer": ("SPRINGER_API_KEY", "SPRINGER_OA_API_KEY"),
    "elsevier": ("ELSEVIER_API_KEY", "ELSEVIER_INSTTOKEN"),
    "ieee": ("IEEE_API_KEY",),
}

# Sources usable with no credential at all.
KEYLESS_SOURCES = frozenset(
    {"crossref", "openalex", "semantic_scholar", "pubmed", "europepmc", "arxiv"}
)


@lru_cache(maxsize=1)
def _env_snapshot() -> dict[str, str]:
    return load_env()


def key(name: str, default: str = "") -> str:
    """Read one credential: unified .env first, then process environment."""
    return (_env_snapshot().get(name) or os.environ.get(name, default) or "").strip()


def has(name: str) -> bool:
    return bool(key(name))


def available_sources() -> dict[str, bool]:
    """Map every known source to whether it is usable right now."""
    status: dict[str, bool] = {}
    for source, required in SOURCE_CREDENTIALS.items():
        if source in KEYLESS_SOURCES:
            status[source] = True
        else:
            status[source] = any(has(name) for name in required)
    return status


def springer_key() -> str:
    """Open Access key, falling back to the general metadata key."""
    return key("SPRINGER_OA_API_KEY") or key("SPRINGER_API_KEY")


def contact_email() -> str:
    """Best-effort contact address for polite-pool / Unpaywall requests."""
    return key("UNPAYWALL_EMAIL") or key("NCBI_EMAIL") or key("OPENALEX_EMAIL")


def env_file_path() -> Path:
    return Path(ENV_FILE)
