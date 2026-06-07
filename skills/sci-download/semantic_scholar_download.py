"""Find and download papers via Semantic Scholar API.

Usage:
    python semantic_scholar_download.py <DOI_or_query> [--output-dir DIR]
    python semantic_scholar_download.py --search "query" [--limit N]

No API key required (rate-limited to 100 req/5min without key).
Endpoint: https://api.semanticscholar.org/graph/v1/paper/
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
API_BASE = "https://api.semanticscholar.org/graph/v1"


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": USER_AGENT})
    api_key = config.get("semantic_scholar_api_key", "")
    if api_key:
        s.headers["x-api-key"] = api_key
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def search_s2(
    query: str,
    limit: int = 10,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search Semantic Scholar for papers."""
    if config is None:
        config = load_config()

    session = _get_session(config)
    url = f"{API_BASE}/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 50),
        "fields": "title,authors,year,externalIds,openAccessPdf,abstract",
    }

    try:
        resp = session.get(url, params=params, timeout=20)
    except requests.RequestException as e:
        return {"success": False, "error": f"Request failed: {e}"}

    if resp.status_code == 429:
        return {"success": False, "error": "Rate limited (429) — wait a moment and retry"}
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"success": False, "error": "Invalid JSON response"}

    results = []
    for paper in data.get("data", [])[:limit]:
        authors = "; ".join(a.get("name", "") for a in paper.get("authors", [])[:5])
        oa_pdf = paper.get("openAccessPdf")
        pdf_url = oa_pdf.get("url", "") if oa_pdf else ""
        ext_ids = paper.get("externalIds") or {}
        results.append({
            "title": paper.get("title", ""),
            "authors": authors,
            "year": str(paper.get("year", "")),
            "doi": ext_ids.get("DOI", ""),
            "pdf_url": pdf_url,
            "abstract": (paper.get("abstract") or "")[:200],
        })

    return {"success": True, "query": query, "count": len(results), "results": results}


def download_s2(
    identifier: str,
    output_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Download a paper's OA PDF via Semantic Scholar.

    Args:
        identifier: DOI, S2 paper ID, or arXiv ID
        output_dir: Override output directory
        config: Config dict

    Returns:
        {success: bool, file?: str, identifier: str, source: str, error?: str}
    """
    if config is None:
        config = load_config()

    session = _get_session(config)
    paper_id = _resolve_paper_id(identifier)

    url = f"{API_BASE}/paper/{paper_id}"
    params = {"fields": "title,openAccessPdf,externalIds"}

    try:
        resp = session.get(url, params=params, timeout=15)
    except requests.RequestException as e:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": f"Request failed: {e}"}

    if resp.status_code == 404:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": "Paper not found"}
    if resp.status_code == 429:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": "Rate limited — retry later"}
    if resp.status_code != 200:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": f"HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": "Invalid JSON"}

    oa_pdf = data.get("openAccessPdf")
    if not oa_pdf or not oa_pdf.get("url"):
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": "No open access PDF available", "title": data.get("title", "")}

    pdf_url = oa_pdf["url"]
    ext_ids = data.get("externalIds", {})
    doi = ext_ids.get("DOI", "") if ext_ids else ""

    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{_safe_filename(doi or identifier)}.pdf"

    if output_path.exists() and output_path.stat().st_size >= MIN_PDF_SIZE:
        return {"success": True, "identifier": identifier, "file": str(output_path), "source": "local_cache"}

    try:
        pdf_resp = session.get(pdf_url, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": f"PDF download failed: {e}"}

    if pdf_resp.status_code != 200:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": f"PDF HTTP {pdf_resp.status_code}"}

    if pdf_resp.content[:5] != b"%PDF-" or len(pdf_resp.content) < MIN_PDF_SIZE:
        return {"success": False, "identifier": identifier, "source": "SemanticScholar", "error": "Response is not a valid PDF"}

    output_path.write_bytes(pdf_resp.content)
    return {"success": True, "identifier": identifier, "file": str(output_path), "source": "SemanticScholar", "size_bytes": len(pdf_resp.content)}


def _resolve_paper_id(identifier: str) -> str:
    """Convert user input to S2 paper ID format."""
    identifier = identifier.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if identifier.lower().startswith(prefix.lower()):
            identifier = identifier[len(prefix):]
            break
    if re.match(r"10\.\d{4,}", identifier):
        return f"DOI:{identifier}"
    if re.match(r"\d{4}\.\d{4,5}", identifier):
        return f"ARXIV:{identifier}"
    return identifier


def _safe_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Download paper via Semantic Scholar")
    parser.add_argument("identifier", nargs="?", help="DOI, arXiv ID, or S2 paper ID")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--search", "-s", help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max search results")
    args = parser.parse_args()

    if args.search:
        result = search_s2(args.search, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("success") else 1)

    if not args.identifier:
        parser.error("Identifier is required (or use --search)")

    result = download_s2(args.identifier, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
