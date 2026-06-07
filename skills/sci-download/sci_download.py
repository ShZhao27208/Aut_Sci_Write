"""Unified academic paper download CLI.

Routes DOIs/identifiers to the appropriate source automatically,
or allows explicit source selection via --source flag.

Usage:
    python sci_download.py "10.1038/s41586-023-06600-9"
    python sci_download.py "2301.07041"
    python sci_download.py "10.1016/j.cell.2023.01.001" --source unpaywall
    python sci_download.py --search "perovskite solar cells" --source semantic_scholar
    python sci_download.py --status
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from config import load_config

DOI_ROUTES: dict[str, str] = {
    "10.1016": "elsevier",
    "10.1038": "springer",
    "10.1007": "springer",
    "10.1109": "ieee",
}

ARXIV_PATTERN = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")
PMC_PATTERN = re.compile(r"^PMC\d+$", re.IGNORECASE)
PMID_PATTERN = re.compile(r"^\d{7,8}$")
DOI_PATTERN = re.compile(r"^10\.\d{4,}/")
CHINESE_PATTERN = re.compile(r"[一-鿿]")

SOURCES = ["elsevier", "springer", "ieee", "arxiv", "unpaywall", "semantic_scholar", "pubmed", "cnki"]


def route_identifier(identifier: str) -> str | None:
    identifier = identifier.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if identifier.lower().startswith(prefix.lower()):
            identifier = identifier[len(prefix):]
            break

    if ARXIV_PATTERN.match(identifier) or identifier.startswith("arXiv:"):
        return "arxiv"
    if identifier.startswith("https://arxiv.org/"):
        return "arxiv"
    if PMC_PATTERN.match(identifier):
        return "pubmed"
    if PMID_PATTERN.match(identifier):
        return "pubmed"
    if CHINESE_PATTERN.search(identifier):
        return "cnki"

    for prefix, source in DOI_ROUTES.items():
        if identifier.startswith(prefix):
            return source

    if DOI_PATTERN.match(identifier):
        return None  # unknown DOI → waterfall

    return None


def download(identifier: str, source: str | None = None, output_dir: str | None = None) -> dict[str, Any]:
    """Download a paper by identifier, routing to the appropriate source."""
    config = load_config()

    if not source:
        source = route_identifier(identifier)

    if source == "elsevier":
        from elsevier_download import download_elsevier
        return download_elsevier(identifier, output_dir=output_dir, config=config)

    if source == "springer":
        from springer_download import download_springer
        return download_springer(identifier, output_dir=output_dir, config=config)

    if source == "ieee":
        from ieee_download import download_ieee
        return download_ieee(identifier, output_dir=output_dir, config=config)

    if source == "arxiv":
        from arxiv_download import download_arxiv
        return download_arxiv(identifier, output_dir=output_dir, config=config)

    if source == "pubmed":
        from pubmed_download import download_pubmed
        return download_pubmed(identifier, output_dir=output_dir, config=config)

    if source == "unpaywall":
        from unpaywall_download import download_unpaywall
        return download_unpaywall(identifier, output_dir=output_dir, config=config)

    if source == "semantic_scholar":
        from semantic_scholar_download import download_s2
        return download_s2(identifier, output_dir=output_dir, config=config)

    if source == "cnki":
        from cnki_download import download_cnki
        return download_cnki(identifier, output_dir=output_dir, config=config)

    # Unknown DOI: waterfall Unpaywall → Semantic Scholar
    return _waterfall_download(identifier, output_dir, config)


def _waterfall_download(identifier: str, output_dir: str | None, config: dict[str, Any]) -> dict[str, Any]:
    """Try Unpaywall first, then Semantic Scholar as fallback."""
    tried: list[dict[str, Any]] = []

    from unpaywall_download import download_unpaywall
    result = download_unpaywall(identifier, output_dir=output_dir, config=config)
    if result.get("success"):
        result["tried"] = [{"source": "Unpaywall", "success": True}]
        return result
    tried.append({"source": "Unpaywall", "error": result.get("error", "")})

    from semantic_scholar_download import download_s2
    result = download_s2(identifier, output_dir=output_dir, config=config)
    if result.get("success"):
        result["tried"] = tried + [{"source": "SemanticScholar", "success": True}]
        return result
    tried.append({"source": "SemanticScholar", "error": result.get("error", "")})

    return {
        "success": False,
        "identifier": identifier,
        "source": "waterfall",
        "error": "All fallback sources failed",
        "tried": tried,
    }


def search(query: str, source: str, limit: int = 10) -> dict[str, Any]:
    """Search for papers via the specified source."""
    config = load_config()

    if source == "arxiv":
        from arxiv_download import search_arxiv
        return search_arxiv(query, limit=limit, config=config)

    if source == "ieee":
        from ieee_download import search_ieee
        return search_ieee(query, limit=limit, config=config)

    if source == "semantic_scholar":
        from semantic_scholar_download import search_s2
        return search_s2(query, limit=limit, config=config)

    if source == "pubmed":
        from pubmed_download import search_pubmed
        return search_pubmed(query, limit=limit, config=config)

    if source == "cnki":
        from cnki_download import search_cnki
        return search_cnki(query, limit=limit, config=config)

    return {"success": False, "error": f"Source '{source}' does not support search. Try: arxiv, ieee, semantic_scholar, pubmed, cnki"}


def show_status() -> dict[str, Any]:
    """Show configuration status and key availability."""
    config = load_config()
    keys = {
        "elsevier_api_key": bool(config.get("elsevier_api_key", "")),
        "springer_api_key": bool(config.get("springer_api_key", "")),
        "ieee_api_key": bool(config.get("ieee_api_key", "")),
        "unpaywall_email": bool(config.get("unpaywall_email", "")),
        "ncbi_api_key": bool(config.get("ncbi_api_key", "")),
        "semantic_scholar_api_key": bool(config.get("semantic_scholar_api_key", "")),
    }
    return {
        "output_dir": config.get("output_dir", ""),
        "proxy": config.get("proxy", ""),
        "cnki_mode": config.get("cnki_mode", "fsso"),
        "webvpn_school": config.get("webvpn_school", ""),
        "api_keys_configured": keys,
        "free_sources": ["arxiv", "semantic_scholar", "pubmed", "unpaywall (email only)"],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Unified academic paper download — 8 sources, one CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s "10.1038/s41586-023-06600-9"          Auto-route Springer
  %(prog)s "2301.07041"                           Auto-route arXiv
  %(prog)s "10.1021/acs.nanolett.3c00123" --source unpaywall
  %(prog)s --search "perovskite" --source semantic_scholar
  %(prog)s --status                               Show config
""",
    )
    parser.add_argument("identifier", nargs="?", help="DOI, arXiv ID, PMCID, PMID, or CNKI filename")
    parser.add_argument("--source", "-s", choices=SOURCES, help="Force a specific download source")
    parser.add_argument("--search", metavar="QUERY", help="Search for papers (requires --source)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max search results (default: 10)")
    parser.add_argument("--output-dir", "-o", help="Output directory for downloaded PDFs")
    parser.add_argument("--status", action="store_true", help="Show config and API key status")
    args = parser.parse_args()

    if args.status:
        result = show_status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.search:
        if not args.source:
            parser.error("--search requires --source (e.g. --source semantic_scholar)")
        result = search(args.search, source=args.source, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("success") else 1)

    if not args.identifier:
        parser.error("Identifier is required (or use --search / --status)")

    result = download(args.identifier, source=args.source, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("success"):
        print(f"\n✓ Downloaded: {result.get('file', '')}", file=sys.stderr)
        print(f"  Source: {result.get('source', '')}", file=sys.stderr)
    else:
        print(f"\n✗ Failed: {result.get('error', '')}", file=sys.stderr)
        if result.get("tried"):
            for attempt in result["tried"]:
                status = "✓" if attempt.get("success") else "✗"
                msg = attempt.get("error", "ok")
                print(f"  {status} {attempt['source']}: {msg}", file=sys.stderr)

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
