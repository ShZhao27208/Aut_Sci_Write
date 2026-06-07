"""Download papers from PubMed Central (open access, no key needed).

Usage:
    python pubmed_download.py <PMID_or_PMCID_or_DOI> [--output-dir DIR]
    python pubmed_download.py --search "query" [--limit N]

No API key required. Uses NCBI E-utilities and Europe PMC.
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
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": USER_AGENT})
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def _ncbi_params(config: dict[str, Any], extra: dict | None = None) -> dict[str, str]:
    """Build NCBI API params with api_key if available."""
    params: dict[str, str] = {}
    api_key = config.get("ncbi_api_key", "")
    if api_key:
        params["api_key"] = api_key
    if extra:
        params.update(extra)
    return params


def search_pubmed(
    query: str,
    limit: int = 10,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search PubMed/PMC for papers via Europe PMC API."""
    if config is None:
        config = load_config()

    session = _get_session(config)
    url = f"{EUROPEPMC_BASE}/search"
    params = {
        "query": query,
        "format": "json",
        "pageSize": min(limit, 25),
        "resultType": "core",
    }

    try:
        resp = session.get(url, params=params, timeout=20)
    except requests.RequestException as e:
        return {"success": False, "error": f"Request failed: {e}"}

    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"success": False, "error": "Invalid JSON response"}

    results = []
    for item in data.get("resultList", {}).get("result", [])[:limit]:
        pmcid = item.get("pmcid", "")
        results.append({
            "title": item.get("title", ""),
            "authors": item.get("authorString", ""),
            "journal": item.get("journalTitle", ""),
            "year": str(item.get("pubYear", "")),
            "doi": item.get("doi", ""),
            "pmid": item.get("pmid", ""),
            "pmcid": pmcid,
            "is_oa": item.get("isOpenAccess", "N") == "Y",
            "has_pdf": bool(pmcid),
        })

    return {"success": True, "query": query, "count": len(results), "results": results}


def download_pubmed(
    identifier: str,
    output_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Download an Open Access paper from PubMed Central.

    Args:
        identifier: PMCID (PMC1234567), PMID (12345678), or DOI
        output_dir: Override output directory
        config: Config dict

    Returns:
        {success: bool, file?: str, identifier: str, source: str, error?: str}
    """
    if config is None:
        config = load_config()

    session = _get_session(config)
    pmcid = _resolve_pmcid(identifier, session)

    if not pmcid:
        return {"success": False, "identifier": identifier, "source": "PubMedCentral", "error": "Could not resolve to a PMC ID — article may not be in PMC"}

    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"{pmcid}.pdf"

    if output_path.exists() and output_path.stat().st_size >= MIN_PDF_SIZE:
        return {"success": True, "pmcid": pmcid, "file": str(output_path), "source": "local_cache"}

    # Strategy 1: Europe PMC render endpoint
    europepmc_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
    pdf_content = _try_download_pdf(session, europepmc_url)
    if pdf_content:
        output_path.write_bytes(pdf_content)
        return {"success": True, "pmcid": pmcid, "file": str(output_path), "source": "PubMedCentral_EuropePMC", "size_bytes": len(pdf_content)}

    # Strategy 2: NCBI direct (old-style URL, may work with some proxies)
    ncbi_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
    pdf_content = _try_download_pdf(session, ncbi_url)
    if pdf_content:
        output_path.write_bytes(pdf_content)
        return {"success": True, "pmcid": pmcid, "file": str(output_path), "source": "PubMedCentral_NCBI", "size_bytes": len(pdf_content)}

    # Strategy 3: Resolve DOI and use Semantic Scholar as fallback
    doi = _pmcid_to_doi(pmcid, session)
    if doi:
        try:
            from semantic_scholar_download import download_s2
            s2_result = download_s2(doi, output_dir=str(target_dir), config=config)
            if s2_result.get("success"):
                return {"success": True, "pmcid": pmcid, "file": s2_result["file"], "source": "PubMedCentral_via_S2", "size_bytes": s2_result.get("size_bytes")}
        except Exception:
            pass

    return {"success": False, "pmcid": pmcid, "source": "PubMedCentral", "error": "All download strategies failed (EuropePMC, NCBI, SemanticScholar). Try configuring a proxy."}


def _try_download_pdf(session: requests.Session, url: str) -> bytes | None:
    """Attempt to download a PDF from url. Returns content if valid PDF, else None."""
    try:
        resp = session.get(url, timeout=25, allow_redirects=True)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    if resp.content[:5] != b"%PDF-":
        return None
    if len(resp.content) < MIN_PDF_SIZE:
        return None
    return resp.content


def _pmcid_to_doi(pmcid: str, session: requests.Session) -> str | None:
    """Get DOI for a PMCID via Europe PMC."""
    url = f"{EUROPEPMC_BASE}/search"
    params = {"query": f"PMCID:{pmcid}", "format": "json", "pageSize": 1}
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("resultList", {}).get("result", [])
            if results and results[0].get("doi"):
                return results[0]["doi"]
    except Exception:
        pass
    return None


def _resolve_pmcid(identifier: str, session: requests.Session) -> str | None:
    """Convert PMID, DOI, or PMCID string to a PMCID."""
    identifier = identifier.strip()

    if identifier.upper().startswith("PMC"):
        return identifier.upper()

    if re.match(r"^\d+$", identifier):
        return _pmid_to_pmcid(identifier, session)

    if re.match(r"10\.\d{4,}", identifier):
        return _doi_to_pmcid(identifier, session)

    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if identifier.lower().startswith(prefix.lower()):
            doi = identifier[len(prefix):]
            return _doi_to_pmcid(doi, session)

    return None


def _pmid_to_pmcid(pmid: str, session: requests.Session) -> str | None:
    """Convert PMID to PMCID via NCBI ID converter."""
    url = f"{NCBI_BASE}/elink.fcgi"
    params = {"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json"}
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            linksets = data.get("linksets", [])
            if linksets:
                links = linksets[0].get("linksetdbs", [])
                for ls in links:
                    if ls.get("dbto") == "pmc":
                        ids = ls.get("links", [])
                        if ids:
                            return f"PMC{ids[0]}"
    except Exception:
        pass
    return None


def _doi_to_pmcid(doi: str, session: requests.Session) -> str | None:
    """Convert DOI to PMCID via Europe PMC search."""
    url = f"{EUROPEPMC_BASE}/search"
    params = {"query": f"DOI:{doi}", "format": "json", "pageSize": 1}
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("resultList", {}).get("result", [])
            if results and results[0].get("pmcid"):
                return results[0]["pmcid"]
    except Exception:
        pass
    return None


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Download paper from PubMed Central")
    parser.add_argument("identifier", nargs="?", help="PMCID, PMID, or DOI")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--search", "-s", help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max search results")
    args = parser.parse_args()

    if args.search:
        result = search_pubmed(args.search, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("success") else 1)

    if not args.identifier:
        parser.error("PMCID/PMID/DOI required (or use --search)")

    result = download_pubmed(args.identifier, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
