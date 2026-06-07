"""Download papers from Springer Nature via the Open Access API.

Usage:
    python springer_download.py <DOI> [--output-dir DIR]
    python springer_download.py --test-key

Requires: springer_api_key in .env
Endpoint: https://api.springernature.com/openaccess/json
Note: Only works for Open Access articles published by Springer/Nature.
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
API_BASE = "https://api.springernature.com"


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": USER_AGENT})
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def download_springer(doi: str, output_dir: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Download an Open Access paper from Springer Nature API.

    Args:
        doi: DOI string (e.g. 10.1038/s41586-023-06600-9)
        output_dir: Override output directory
        config: Config dict

    Returns:
        {success: bool, file?: str, doi: str, source: str, error?: str}
    """
    if config is None:
        config = load_config()

    api_key = config.get("springer_api_key", "")
    if not api_key:
        return {
            "success": False,
            "doi": doi,
            "source": "SpringerNatureAPI",
            "error": "No API key configured. Set SPRINGER_API_KEY in ~/.aut-sci-download/.env",
        }

    doi = _normalize_doi(doi)

    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{_safe_filename(doi)}.pdf"

    if output_path.exists() and output_path.stat().st_size >= MIN_PDF_SIZE:
        return {"success": True, "doi": doi, "file": str(output_path), "source": "local_cache"}

    session = _get_session(config)

    meta_url = f"{API_BASE}/openaccess/json"
    params = {"q": f"doi:{doi}", "api_key": api_key}

    try:
        resp = session.get(meta_url, params=params, timeout=20)
    except requests.RequestException as e:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": f"Request failed: {e}"}

    if resp.status_code == 403:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": "Invalid API key (403)"}
    if resp.status_code == 429:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": "Rate limited (429)"}
    if resp.status_code != 200:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": f"HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": "Invalid JSON response"}

    records = data.get("records", [])
    if not records:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": "Article not found or not Open Access"}

    pdf_url = _extract_pdf_url(records[0])
    if not pdf_url:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": "No PDF URL in metadata — article may not be OA"}

    try:
        pdf_resp = session.get(pdf_url, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": f"PDF download failed: {e}"}

    if pdf_resp.status_code != 200:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": f"PDF HTTP {pdf_resp.status_code}"}

    if pdf_resp.content[:5] != b"%PDF-":
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": "Response is not a valid PDF"}

    if len(pdf_resp.content) < MIN_PDF_SIZE:
        return {"success": False, "doi": doi, "source": "SpringerNatureAPI", "error": f"PDF too small ({len(pdf_resp.content)} bytes)"}

    output_path.write_bytes(pdf_resp.content)
    return {"success": True, "doi": doi, "file": str(output_path), "source": "SpringerNatureAPI", "size_bytes": len(pdf_resp.content)}


def _extract_pdf_url(record: dict) -> str | None:
    """Extract PDF download URL from Springer API record."""
    for url_entry in record.get("url", []):
        if url_entry.get("format") == "pdf":
            return url_entry["value"]

    for url_entry in record.get("url", []):
        val = url_entry.get("value", "")
        if "pdf" in val.lower():
            return val

    doi = record.get("doi", "")
    if doi:
        return f"https://link.springer.com/content/pdf/{doi}.pdf"

    return None


def test_api_key(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the configured Springer Nature API key."""
    if config is None:
        config = load_config()
    api_key = config.get("springer_api_key", "")
    if not api_key:
        return {"valid": False, "error": "No API key configured"}

    session = _get_session(config)
    try:
        resp = session.get(
            f"{API_BASE}/openaccess/json",
            params={"q": "doi:10.1038/s41586-023-06600-9", "api_key": api_key, "p": 1},
            timeout=15,
        )
        if resp.status_code == 200:
            return {"valid": True, "message": "Springer Nature API key is valid"}
        return {"valid": False, "error": f"HTTP {resp.status_code}"}
    except requests.RequestException as e:
        return {"valid": False, "error": str(e)}


def _normalize_doi(identifier: str) -> str:
    identifier = identifier.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if identifier.lower().startswith(prefix.lower()):
            identifier = identifier[len(prefix):]
            break
    return identifier.strip()


def _safe_filename(doi: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", doi)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Download Springer Nature OA paper by DOI")
    parser.add_argument("doi", nargs="?", help="DOI (e.g. 10.1038/s41586-023-06600-9)")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--test-key", action="store_true", help="Test API key validity")
    args = parser.parse_args()

    if args.test_key:
        result = test_api_key()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("valid") else 1)

    if not args.doi:
        parser.error("DOI is required (or use --test-key)")

    result = download_springer(args.doi, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
