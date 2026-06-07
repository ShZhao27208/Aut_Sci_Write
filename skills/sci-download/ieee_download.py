"""Download papers from IEEE Xplore via the API.

Usage:
    python ieee_download.py <DOI> [--output-dir DIR]
    python ieee_download.py --search "query" [--limit N]
    python ieee_download.py --test-key

Requires: ieee_api_key in .env
Endpoint: https://ieeexploreapi.ieee.org/api/v1/search/articles
Note: Free tier provides metadata + abstract. PDF access requires institutional subscription.
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
API_BASE = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": USER_AGENT})
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def search_ieee(
    query: str,
    limit: int = 10,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search IEEE Xplore for articles.

    Returns:
        {success: bool, results: [{title, authors, doi, year, pdf_url?, abstract}]}
    """
    if config is None:
        config = load_config()

    api_key = config.get("ieee_api_key", "")
    if not api_key:
        return {"success": False, "error": "No API key. Set IEEE_API_KEY in ~/.aut-sci-download/.env"}

    session = _get_session(config)
    params = {
        "apikey": api_key,
        "querytext": query,
        "max_records": min(limit, 25),
        "format": "json",
    }

    try:
        resp = session.get(API_BASE, params=params, timeout=20)
    except requests.RequestException as e:
        return {"success": False, "error": f"Request failed: {e}"}

    if resp.status_code == 403:
        return {"success": False, "error": "Invalid API key (403)"}
    if resp.status_code == 429:
        return {"success": False, "error": "Rate limited (429)"}
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"success": False, "error": "Invalid JSON response"}

    articles = data.get("articles", [])
    results = []
    for art in articles[:limit]:
        authors = "; ".join(
            a.get("full_name", "") for a in art.get("authors", {}).get("authors", [])
        )
        results.append({
            "title": art.get("title", ""),
            "authors": authors,
            "doi": art.get("doi", ""),
            "year": str(art.get("publication_year", "")),
            "publisher": art.get("publisher", ""),
            "pdf_url": art.get("pdf_url", ""),
            "abstract": art.get("abstract", "")[:200],
        })

    return {"success": True, "query": query, "count": len(results), "results": results}


def download_ieee(
    doi: str,
    output_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Download an IEEE paper PDF by DOI.

    The IEEE API provides pdf_url but actual download requires
    institutional access (via IP or proxy). This function attempts
    the download and reports clearly if access is denied.
    """
    if config is None:
        config = load_config()

    api_key = config.get("ieee_api_key", "")
    if not api_key:
        return {
            "success": False,
            "doi": doi,
            "source": "IEEE_Xplore",
            "error": "No API key. Set IEEE_API_KEY in ~/.aut-sci-download/.env",
        }

    doi = _normalize_doi(doi)

    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{_safe_filename(doi)}.pdf"

    if output_path.exists() and output_path.stat().st_size >= MIN_PDF_SIZE:
        return {"success": True, "doi": doi, "file": str(output_path), "source": "local_cache"}

    session = _get_session(config)
    params = {"apikey": api_key, "querytext": f"doi:{doi}", "max_records": 1, "format": "json"}

    try:
        resp = session.get(API_BASE, params=params, timeout=20)
    except requests.RequestException as e:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": f"Search failed: {e}"}

    if resp.status_code != 200:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": f"API HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": "Invalid JSON"}

    articles = data.get("articles", [])
    if not articles:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": "Article not found"}

    pdf_url = articles[0].get("pdf_url", "")
    if not pdf_url:
        return {
            "success": False,
            "doi": doi,
            "source": "IEEE_Xplore",
            "error": "No PDF URL — article metadata found but PDF not available via API",
            "title": articles[0].get("title", ""),
        }

    try:
        pdf_resp = session.get(pdf_url, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": f"PDF download failed: {e}"}

    if pdf_resp.status_code == 403:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": "Access denied (403) — institutional subscription required"}
    if pdf_resp.status_code != 200:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": f"PDF HTTP {pdf_resp.status_code}"}

    if pdf_resp.content[:5] != b"%PDF-" or len(pdf_resp.content) < MIN_PDF_SIZE:
        return {"success": False, "doi": doi, "source": "IEEE_Xplore", "error": "Response is not a valid PDF"}

    output_path.write_bytes(pdf_resp.content)
    return {"success": True, "doi": doi, "file": str(output_path), "source": "IEEE_Xplore", "size_bytes": len(pdf_resp.content)}


def test_api_key(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the configured IEEE API key."""
    if config is None:
        config = load_config()
    api_key = config.get("ieee_api_key", "")
    if not api_key:
        return {"valid": False, "error": "No API key configured"}

    session = _get_session(config)
    try:
        resp = session.get(
            API_BASE,
            params={"apikey": api_key, "querytext": "machine learning", "max_records": 1},
            timeout=15,
        )
        if resp.status_code == 200:
            return {"valid": True, "message": "IEEE Xplore API key is valid"}
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
    parser = argparse.ArgumentParser(description="Download IEEE Xplore paper by DOI")
    parser.add_argument("doi", nargs="?", help="DOI (e.g. 10.1109/ACCESS.2023.1234567)")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--search", "-s", help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max search results")
    parser.add_argument("--test-key", action="store_true", help="Test API key validity")
    args = parser.parse_args()

    if args.test_key:
        result = test_api_key()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("valid") else 1)

    if args.search:
        result = search_ieee(args.search, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("success") else 1)

    if not args.doi:
        parser.error("DOI is required (or use --search / --test-key)")

    result = download_ieee(args.doi, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
