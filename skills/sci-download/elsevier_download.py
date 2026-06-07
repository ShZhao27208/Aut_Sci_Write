"""Download papers from Elsevier/ScienceDirect via the Article Retrieval API.

Usage:
    python elsevier_download.py <DOI> [--output-dir DIR]
    python elsevier_download.py --test-key

Requires: elsevier_api_key configured via config.py
Endpoint: https://api.elsevier.com/content/article/doi/{doi}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import requests

from config import load_config

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

MIN_PDF_SIZE = 10_000


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": USER_AGENT})
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def download_elsevier(doi: str, output_dir: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Download a paper from Elsevier API.

    Args:
        doi: DOI string (e.g. 10.1016/j.cell.2023.01.001)
        output_dir: Override output directory
        config: Config dict (loaded from file if None)

    Returns:
        {success: bool, file?: str, doi: str, source: str, error?: str}
    """
    if config is None:
        config = load_config()

    api_key = config.get("elsevier_api_key", "")
    if not api_key:
        return {
            "success": False,
            "doi": doi,
            "source": "ElsevierAPI",
            "error": "No API key configured. Run: python config.py set elsevier_api_key YOUR_KEY",
        }

    doi = _normalize_doi(doi)

    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{_safe_filename(doi)}.pdf"

    if output_path.exists() and output_path.stat().st_size >= MIN_PDF_SIZE:
        return {"success": True, "doi": doi, "file": str(output_path), "source": "local_cache"}

    url = f"https://api.elsevier.com/content/article/doi/{doi}"
    headers = {
        "Accept": "application/pdf",
        "X-ELS-APIKey": api_key,
    }
    insttoken = config.get("elsevier_insttoken", "")
    if insttoken:
        headers["X-ELS-InstToken"] = insttoken

    session = _get_session(config)
    try:
        resp = session.get(url, headers=headers, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": f"Request failed: {e}"}

    if resp.status_code == 401:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": "Invalid API key (401)"}
    if resp.status_code == 403:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": "Access forbidden (403) — API quota exhausted or no institutional access"}
    if resp.status_code == 404:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": "Article not found (404)"}
    if resp.status_code == 429:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": "Rate limited (429) — try again later"}
    if resp.status_code != 200:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": f"HTTP {resp.status_code}"}

    content_type = resp.headers.get("Content-Type", "")
    is_pdf = "pdf" in content_type or resp.content[:5] == b"%PDF-"

    if not is_pdf:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": f"Non-PDF response ({content_type[:40]}) — API key may lack PDF access"}

    if len(resp.content) < MIN_PDF_SIZE:
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": f"Response too small ({len(resp.content)} bytes)"}

    output_path.write_bytes(resp.content)

    if output_path.read_bytes()[:5] != b"%PDF-":
        output_path.unlink(missing_ok=True)
        return {"success": False, "doi": doi, "source": "ElsevierAPI", "error": "Downloaded file is not a valid PDF"}

    return {"success": True, "doi": doi, "file": str(output_path), "source": "ElsevierAPI", "size_bytes": len(resp.content)}


def test_api_key(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the configured Elsevier API key."""
    if config is None:
        config = load_config()
    api_key = config.get("elsevier_api_key", "")
    if not api_key:
        return {"valid": False, "error": "No API key configured"}

    session = _get_session(config)
    try:
        resp = session.get(
            "https://api.elsevier.com/content/serial/title",
            headers={"Accept": "application/json", "X-ELS-APIKey": api_key},
            params={"count": 1},
            timeout=15,
        )
        if resp.status_code == 200:
            return {"valid": True, "message": "API key is valid"}
        return {"valid": False, "error": f"HTTP {resp.status_code}"}
    except requests.RequestException as e:
        return {"valid": False, "error": str(e)}


def _normalize_doi(identifier: str) -> str:
    identifier = identifier.strip()
    identifier = identifier.replace("–", "-").replace("—", "-")
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if identifier.lower().startswith(prefix.lower()):
            identifier = identifier[len(prefix):]
            break
    return identifier.strip()


def _safe_filename(doi: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", doi)


# --- CLI ---

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Download Elsevier paper by DOI")
    parser.add_argument("doi", nargs="?", help="DOI to download (e.g. 10.1016/j.cell.2023.01.001)")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--test-key", action="store_true", help="Test API key validity")
    args = parser.parse_args()

    if args.test_key:
        result = test_api_key()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("valid") else 1)

    if not args.doi:
        parser.error("DOI is required (or use --test-key)")

    result = download_elsevier(args.doi, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
