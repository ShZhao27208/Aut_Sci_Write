"""Download papers from arXiv (open access, no key needed).

Usage:
    python arxiv_download.py <arxiv_id_or_url> [--output-dir DIR]
    python arxiv_download.py --search "query" [--limit N]

No API key required. arXiv provides free access to all preprints.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
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
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_PDF_BASE = "https://arxiv.org/pdf"

ARXIV_ID_PATTERNS = [
    re.compile(r"(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"([a-z-]+/\d{7})(v\d+)?"),
]


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": USER_AGENT})
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def _extract_arxiv_id(identifier: str) -> str | None:
    identifier = identifier.strip()
    for prefix in ("https://arxiv.org/abs/", "https://arxiv.org/pdf/", "http://arxiv.org/abs/", "arXiv:"):
        if identifier.startswith(prefix):
            identifier = identifier[len(prefix):]
            break
    identifier = identifier.rstrip("/").replace(".pdf", "")
    for pat in ARXIV_ID_PATTERNS:
        m = pat.search(identifier)
        if m:
            return m.group(0)
    return None


def search_arxiv(
    query: str,
    limit: int = 10,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search arXiv papers by keyword."""
    if config is None:
        config = load_config()

    session = _get_session(config)
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(limit, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        resp = session.get(ARXIV_API, params=params, timeout=20)
    except requests.RequestException as e:
        return {"success": False, "error": f"Request failed: {e}"}

    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}

    results = _parse_atom_feed(resp.text)
    return {"success": True, "query": query, "count": len(results), "results": results}


def _parse_atom_feed(xml_text: str) -> list[dict[str, str]]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

        authors = []
        for author in entry.findall("atom:author", ns):
            name_el = author.find("atom:name", ns)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        arxiv_id = ""
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
            href = link.get("href", "")
            if "abs" in href:
                m = re.search(r"abs/(.+)", href)
                if m:
                    arxiv_id = m.group(1)

        summary_el = entry.find("atom:summary", ns)
        abstract = summary_el.text.strip()[:200] if summary_el is not None and summary_el.text else ""

        published_el = entry.find("atom:published", ns)
        year = published_el.text[:4] if published_el is not None and published_el.text else ""

        results.append({
            "title": title,
            "authors": "; ".join(authors[:5]),
            "arxiv_id": arxiv_id,
            "year": year,
            "pdf_url": pdf_url or f"{ARXIV_PDF_BASE}/{arxiv_id}.pdf",
            "abstract": abstract,
        })

    return results


def download_arxiv(
    identifier: str,
    output_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Download a paper from arXiv by ID or URL."""
    if config is None:
        config = load_config()

    arxiv_id = _extract_arxiv_id(identifier)
    if not arxiv_id:
        return {"success": False, "identifier": identifier, "source": "arXiv", "error": f"Cannot parse arXiv ID from: {identifier}"}

    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_id = arxiv_id.replace("/", "_")
    output_path = target_dir / f"arxiv_{safe_id}.pdf"

    if output_path.exists() and output_path.stat().st_size >= MIN_PDF_SIZE:
        return {"success": True, "arxiv_id": arxiv_id, "file": str(output_path), "source": "local_cache"}

    pdf_url = f"{ARXIV_PDF_BASE}/{arxiv_id}.pdf"
    session = _get_session(config)

    try:
        resp = session.get(pdf_url, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return {"success": False, "arxiv_id": arxiv_id, "source": "arXiv", "error": f"Download failed: {e}"}

    if resp.status_code != 200:
        return {"success": False, "arxiv_id": arxiv_id, "source": "arXiv", "error": f"HTTP {resp.status_code}"}

    if resp.content[:5] != b"%PDF-":
        return {"success": False, "arxiv_id": arxiv_id, "source": "arXiv", "error": "Response is not a valid PDF"}

    if len(resp.content) < MIN_PDF_SIZE:
        return {"success": False, "arxiv_id": arxiv_id, "source": "arXiv", "error": f"PDF too small ({len(resp.content)} bytes)"}

    output_path.write_bytes(resp.content)
    return {"success": True, "arxiv_id": arxiv_id, "file": str(output_path), "source": "arXiv", "size_bytes": len(resp.content)}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Download arXiv paper")
    parser.add_argument("identifier", nargs="?", help="arXiv ID or URL (e.g. 2301.07041)")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--search", "-s", help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max search results")
    args = parser.parse_args()

    if args.search:
        result = search_arxiv(args.search, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("success") else 1)

    if not args.identifier:
        parser.error("arXiv ID/URL is required (or use --search)")

    result = download_arxiv(args.identifier, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
