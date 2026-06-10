"""Find open access PDFs via Unpaywall API.

Usage:
    python unpaywall_download.py <DOI> [--output-dir DIR]

Requires: UNPAYWALL_EMAIL in .env (just your email, no registration needed).
Endpoint: https://api.unpaywall.org/v2/{doi}?email=xxx
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
API_BASE = "https://api.unpaywall.org/v2"


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": USER_AGENT})
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def download_unpaywall(
    doi: str,
    output_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Find and download the Open Access version of a paper via Unpaywall.

    Args:
        doi: DOI string
        output_dir: Override output directory
        config: Config dict

    Returns:
        {success: bool, file?: str, doi: str, source: str, oa_url?: str, error?: str}
    """
    if config is None:
        config = load_config()

    email = config.get("unpaywall_email", "")
    if not email:
        return {
            "success": False,
            "doi": doi,
            "source": "Unpaywall",
            "error": "No email configured. Set UNPAYWALL_EMAIL in ~/.aut_sci_write/.env",
        }

    doi = _normalize_doi(doi)

    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{_safe_filename(doi)}.pdf"

    if output_path.exists() and output_path.stat().st_size >= MIN_PDF_SIZE:
        return {"success": True, "doi": doi, "file": str(output_path), "source": "local_cache"}

    session = _get_session(config)
    api_url = f"{API_BASE}/{doi}"

    try:
        resp = session.get(api_url, params={"email": email}, timeout=15)
    except requests.RequestException as e:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": f"Request failed: {e}"}

    if resp.status_code == 404:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": "DOI not found in Unpaywall"}
    if resp.status_code == 422:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": "Invalid DOI format"}
    if resp.status_code != 200:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": f"HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": "Invalid JSON response"}

    if not data.get("is_oa"):
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": "Article is not Open Access"}

    pdf_url = _find_best_pdf_url(data)
    if not pdf_url:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": "OA article found but no PDF URL available"}

    try:
        pdf_resp = session.get(pdf_url, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": f"PDF download failed: {e}", "oa_url": pdf_url}

    if pdf_resp.status_code != 200:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": f"PDF HTTP {pdf_resp.status_code}", "oa_url": pdf_url}

    if pdf_resp.content[:5] != b"%PDF-":
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": "Response is not a valid PDF", "oa_url": pdf_url}

    if len(pdf_resp.content) < MIN_PDF_SIZE:
        return {"success": False, "doi": doi, "source": "Unpaywall", "error": f"PDF too small ({len(pdf_resp.content)} bytes)"}

    output_path.write_bytes(pdf_resp.content)
    return {"success": True, "doi": doi, "file": str(output_path), "source": "Unpaywall", "oa_url": pdf_url, "size_bytes": len(pdf_resp.content)}


def _find_best_pdf_url(data: dict) -> str | None:
    """Extract the best PDF URL from Unpaywall response."""
    best = data.get("best_oa_location", {})
    if best:
        url = best.get("url_for_pdf") or best.get("url")
        if url:
            return url

    for loc in data.get("oa_locations", []):
        url = loc.get("url_for_pdf") or loc.get("url")
        if url:
            return url

    return None


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
    parser = argparse.ArgumentParser(description="Find OA PDF via Unpaywall")
    parser.add_argument("doi", help="DOI to look up (e.g. 10.1038/s41586-023-06600-9)")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    args = parser.parse_args()

    result = download_unpaywall(args.doi, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
