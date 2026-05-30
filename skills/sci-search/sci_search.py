#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Sci Search - Academic Paper Search & Metrics Tool
Combined logic from paper_fetch.py and smart_paper_output.py
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

def configure_windows_console() -> None:
    """Avoid import-time stdio mutation; only reconfigure in CLI mode."""
    if sys.platform != 'win32':
        return

    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue

        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            reconfigure(encoding='utf-8', errors='replace')

# Configuration
_SCRIPT_DIR = Path(__file__).parent
JOURNAL_DB_PATH = _SCRIPT_DIR.parent.parent / "scripts" / "journal_db.json"


def default_data_dir() -> Path:
    """Return a user-writable data directory for sci-search cache files."""
    override = os.environ.get("AUT_SCI_WRITE_DATA_DIR")
    if override:
        return Path(override) / "sci-search"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Aut_Sci_Write" / "sci-search"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "aut_sci_write" / "sci-search"


LIBRARY_PATH = default_data_dir() / "library.json"

# API rate-limit delay (seconds)
RATE_LIMIT_DELAY = 1.0

# Journal metrics database fallback (overridden by journal_db.json when present)
DEFAULT_JOURNAL_DB = {
    'Advanced Materials': {'jcr_partition': 'Q1', 'impact_factor': '29.4', '5_year_if': '28.9', 'chinese_partition': 'CAS Q1 Top', 'category': 'Materials Science, Multidisciplinary', 'publisher': 'Wiley', 'is_top_journal': True, 'is_nature_science_advmat': True, 'notes': 'Flagship materials science journal.'},
    'Nature': {'jcr_partition': 'Q1', 'impact_factor': '64.8', '5_year_if': '59.2', 'chinese_partition': 'CAS Q1 Top', 'category': 'Multidisciplinary Sciences', 'publisher': 'Springer Nature', 'is_top_journal': True, 'is_nature_science_advmat': True, 'notes': 'Flagship multidisciplinary science journal.'},
    'Science': {'jcr_partition': 'Q1', 'impact_factor': '56.9', '5_year_if': '54.3', 'chinese_partition': 'CAS Q1 Top', 'category': 'Multidisciplinary Sciences', 'publisher': 'AAAS', 'is_top_journal': True, 'is_nature_science_advmat': True, 'notes': 'Flagship multidisciplinary science journal.'},
    'Nature Photonics': {'jcr_partition': 'Q1', 'impact_factor': '35.0', '5_year_if': '32.5', 'chinese_partition': 'CAS partition unavailable', 'category': 'Physics, Applied', 'publisher': 'Springer Nature', 'is_top_journal': True, 'is_nature_science_advmat': True, 'notes': 'Nature portfolio journal in photonics.'},
    'Nature Physics': {'jcr_partition': 'Q1', 'impact_factor': '19.6', '5_year_if': '18.9', 'chinese_partition': 'CAS partition unavailable', 'category': 'Physics, Multidisciplinary', 'publisher': 'Springer Nature', 'is_top_journal': True, 'is_nature_science_advmat': True, 'notes': 'Nature portfolio journal in physics.'},
    'Nano Energy': {'jcr_partition': 'Q1', 'impact_factor': '16.8', '5_year_if': '16.3', 'chinese_partition': 'CAS partition unavailable', 'category': 'Nanoscience & Nanotechnology', 'publisher': 'Elsevier', 'is_top_journal': True, 'is_nature_science_advmat': False, 'notes': 'High-impact energy materials journal.'},
    'ACS Omega': {'jcr_partition': 'Q2', 'impact_factor': '4.1', '5_year_if': '4.3', 'chinese_partition': 'CAS partition unavailable', 'category': 'Chemistry, Multidisciplinary', 'publisher': 'American Chemical Society', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Journal note unavailable'},
    'Ceramics International': {'jcr_partition': 'Q1', 'impact_factor': '5.2', '5_year_if': '5.1', 'chinese_partition': 'CAS partition unavailable', 'category': 'Materials Science, Ceramics', 'publisher': 'Elsevier', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Ceramics and materials processing journal.'},
    'Journal of Luminescence': {'jcr_partition': 'Q2', 'impact_factor': '3.6', '5_year_if': '3.5', 'chinese_partition': 'CAS partition unavailable', 'category': 'Optics', 'publisher': 'Elsevier', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Luminescence and optical materials journal.'},
    'CrystEngComm': {'jcr_partition': 'Q2', 'impact_factor': '3.1', '5_year_if': '3.2', 'chinese_partition': 'CAS partition unavailable', 'category': 'Chemistry, Multidisciplinary', 'publisher': 'Royal Society of Chemistry', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Crystal engineering journal.'},
    'Colloids and Surfaces A: Physicochemical and Engineering Aspects': {'jcr_partition': 'Q2', 'impact_factor': '5.2', '5_year_if': '5.0', 'chinese_partition': 'CAS partition unavailable', 'category': 'Chemistry, Physical', 'publisher': 'Elsevier', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Journal note unavailable'},
    'The Journal of Physical Chemistry Letters': {'jcr_partition': 'Q1', 'impact_factor': '6.4', '5_year_if': '6.2', 'chinese_partition': 'CAS partition unavailable', 'category': 'Chemistry, Physical', 'publisher': 'American Chemical Society', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Physical chemistry letters journal.'},
    'Journal of the American Ceramic Society': {'jcr_partition': 'Q2', 'impact_factor': '3.9', '5_year_if': '3.8', 'chinese_partition': 'CAS partition unavailable', 'category': 'Materials Science, Ceramics', 'publisher': 'Wiley', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Ceramic science journal.'},
    'Optical Materials': {'jcr_partition': 'Q2', 'impact_factor': '3.9', '5_year_if': '3.8', 'chinese_partition': 'CAS partition unavailable', 'category': 'Materials Science, Coatings & Films', 'publisher': 'Elsevier', 'is_top_journal': False, 'is_nature_science_advmat': False, 'notes': 'Optical materials journal.'},
    'Laser & Photonics Reviews': {'jcr_partition': 'Q1', 'impact_factor': '11.0', '5_year_if': '10.5', 'chinese_partition': 'CAS partition unavailable', 'category': 'Optics', 'publisher': 'Wiley', 'is_top_journal': True, 'is_nature_science_advmat': False, 'notes': 'Journal note unavailable'},
    'Advanced Optical Materials': {'jcr_partition': 'Q1', 'impact_factor': '9.0', '5_year_if': '8.7', 'chinese_partition': 'CAS partition unavailable', 'category': 'Materials Science, Multidisciplinary', 'publisher': 'Wiley', 'is_top_journal': True, 'is_nature_science_advmat': True, 'notes': 'Advanced Materials family journal in optical materials.'}
}


def _normalize_journal_metrics(journal_name: str, metrics: Dict) -> Dict:
    """Support both legacy JSON schema and richer in-code metrics schema."""
    normalized = {
        'jcr_partition': metrics.get('jcr_partition', metrics.get('JCR', 'N/A')),
        'impact_factor': str(metrics.get('impact_factor', metrics.get('IF', 'N/A'))),
        '5_year_if': str(metrics.get('5_year_if', metrics.get('IF', 'N/A'))),
        'chinese_partition': metrics.get('chinese_partition', metrics.get('Partition', 'N/A')),
        'category': metrics.get('category', ''),
        'publisher': metrics.get('publisher', metrics.get('Publisher', '')),
        'is_top_journal': bool(metrics.get('is_top_journal', False)),
        'is_nature_science_advmat': bool(metrics.get('is_nature_science_advmat', False)),
        'notes': metrics.get('notes', ''),
    }

    journal_lower = journal_name.lower()
    if journal_lower in {'nature', 'science'} or 'advanced materials' in journal_lower:
        normalized['is_top_journal'] = True
        normalized['is_nature_science_advmat'] = True

    return normalized


def load_journal_db(db_path: Path = JOURNAL_DB_PATH) -> Dict[str, Dict]:
    """Load journal metrics from disk, falling back to bundled defaults."""
    database = {
        name: _normalize_journal_metrics(name, metrics)
        for name, metrics in DEFAULT_JOURNAL_DB.items()
    }

    if not db_path.exists():
        return database

    try:
        with db_path.open('r', encoding='utf-8') as f:
            file_metrics = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: failed to load journal DB from {db_path}: {exc}")
        return database

    for name, metrics in file_metrics.items():
        if isinstance(metrics, dict):
            database[name] = _normalize_journal_metrics(name, metrics)

    return database


JOURNAL_DB = load_journal_db()

def load_local_env() -> Dict[str, str]:
    """Load simple KEY=VALUE pairs from a skill-local .env file."""
    env_path = _SCRIPT_DIR / ".env"
    if not env_path.exists():
        return {}

    values = {}
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError as exc:
        print(f"Warning: failed to load local env from {env_path}: {exc}")

    return values


LOCAL_ENV = load_local_env()


def get_config_value(name: str, default: str = "") -> str:
    return LOCAL_ENV.get(name) or os.environ.get(name, default)


def _normalize_journal_name(name: str) -> str:
    """Normalize a journal name for safe matching.

    Lowercase, strip punctuation to spaces, and collapse whitespace so that
    only genuinely equivalent names compare equal. This avoids the substring
    trap where 'Nature Communications' would otherwise match 'Nature'.
    """
    lowered = name.lower()
    no_punct = re.sub(r'[^a-z0-9]+', ' ', lowered)
    return re.sub(r'\s+', ' ', no_punct).strip()


def get_journal_metrics(journal_name: str) -> Optional[Dict]:
    if not journal_name:
        return None

    # Exact match (raw)
    if journal_name in JOURNAL_DB:
        return JOURNAL_DB[journal_name]

    query_norm = _normalize_journal_name(journal_name)
    if not query_norm:
        return None

    # Exact normalized match against DB entries.
    for db_journal, metrics in JOURNAL_DB.items():
        if _normalize_journal_name(db_journal) == query_norm:
            return metrics

    # Known abbreviations: only accept when the normalized query EQUALS a
    # known abbreviation, never a substring of it (that was the bug).
    abbrev_map = {
        'adv mater': 'Advanced Materials',
        'nat photonics': 'Nature Photonics',
        'nat phys': 'Nature Physics',
        'j phys chem lett': 'The Journal of Physical Chemistry Letters',
        'j am ceram soc': 'Journal of the American Ceramic Society',
        'opt mater': 'Optical Materials',
        'laser photon rev': 'Laser & Photonics Reviews',
        'adv opt mater': 'Advanced Optical Materials',
        'colloid surf a': 'Colloids and Surfaces A: Physicochemical and Engineering Aspects',
        'crystengcomm': 'CrystEngComm',
        'j lumin': 'Journal of Luminescence',
        'acs omega': 'ACS Omega',
        'nano energy': 'Nano Energy',
    }
    for abbrev, full_name in abbrev_map.items():
        if _normalize_journal_name(abbrev) == query_norm:
            return JOURNAL_DB.get(full_name)

    # No confident match: return None rather than fabricate metrics.
    return None

class PaperLibrary:
    def __init__(self, library_path: str = str(LIBRARY_PATH)):
        self.library_path = library_path
        self.papers = self._load_library()

    def _load_library(self) -> List[Dict]:
        if os.path.exists(self.library_path):
            try:
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('papers', [])
            except Exception: return []
        return []

    def _save_library(self):
        data = {'papers': self.papers, 'last_updated': datetime.now().isoformat()}
        Path(self.library_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.library_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _paper_key(self, paper: Dict) -> tuple:
        return (
            paper.get('source', ''),
            paper.get('url', ''),
            paper.get('doi', ''),
            paper.get('title', '').strip().lower(),
        )

    def add_paper(self, paper: Dict):
        # Decorate with metrics if available
        paper = dict(paper)
        if paper.get('journal'):
            metrics = get_journal_metrics(paper['journal'])
            if metrics:
                paper['journal_metrics'] = metrics

        paper_key = self._paper_key(paper)
        for index, existing in enumerate(self.papers):
            if self._paper_key(existing) == paper_key:
                self.papers[index] = paper
                self._save_library()
                return

        self.papers.append(paper)
        self._save_library()

    def extend_papers(self, papers: List[Dict]):
        for paper in papers:
            self.add_paper(paper)

class ArxivFetcher:
    API_URL = "https://export.arxiv.org/api/query"
    NS = {'atom': 'http://www.w3.org/2005/Atom'}

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        params = {'search_query': f'all:{query}', 'max_results': max_results}
        url = f"{self.API_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                content = resp.read().decode('utf-8')
            root = ET.fromstring(content)
            papers = []
            for entry in root.findall('atom:entry', self.NS):
                paper = {
                    'source': 'arxiv',
                    'title': ' '.join((entry.find('atom:title', self.NS).text or '').split()),
                    'authors': [n.text.strip() for au in entry.findall('atom:author', self.NS) for n in [au.find('atom:name', self.NS)] if n is not None],
                    'year': (entry.find('atom:published', self.NS).text or '')[:4],
                    'url': entry.find('atom:id', self.NS).text.strip(),
                    'abstract': ' '.join((entry.find('atom:summary', self.NS).text or '').split())
                }
                papers.append(paper)
            return papers
        except Exception as e:
            print(f"arXiv error: {e}")
            return []

class WoSFetcher:
    """Web of Science Starter API fetcher.

    Requires WOS_API_KEY in the skill-local .env file.
    Apply for a free API key at: https://developer.clarivate.com/apis/wos-starter
    Authentication: X-ApiKey header (no subscription required for Starter tier).
    """
    API_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"

    def __init__(self):
        self.api_key = get_config_value("WOS_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        if not self.api_key:
            return []

        params = {
            "q": query,
            "db": "WOS",
            "limit": min(max_results, 10),
            "page": 1,
        }
        url = f"{self.API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={
            "X-ApiKey": self.api_key,
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            papers = []
            for hit in data.get("hits", []):
                # Extract authors
                authors_raw = hit.get("authors", {})
                if isinstance(authors_raw, dict):
                    authors = [a.get("displayName", "") for a in authors_raw.get("authors", [])]
                else:
                    authors = []

                # Extract source/journal
                source = hit.get("source", {})
                journal = source.get("sourceTitle", "") if isinstance(source, dict) else ""
                year = ""
                if isinstance(source, dict):
                    pub_year = source.get("publishYear") or source.get("publishDate", "")
                    year = str(pub_year)[:4] if pub_year else ""

                # Extract DOI
                identifiers = hit.get("identifiers", {})
                doi = ""
                if isinstance(identifiers, dict):
                    doi = identifiers.get("doi", "")

                uid = hit.get("uid", "")
                url_link = f"https://www.webofscience.com/wos/woscc/full-record/{uid}" if uid else ""

                paper = {
                    "source": "wos",
                    "title": hit.get("title", "Unknown"),
                    "authors": authors,
                    "year": year,
                    "journal": journal,
                    "url": url_link,
                    "doi": doi,
                    "times_cited": hit.get("timesCited", ""),
                }
                papers.append(paper)
            return papers
        except Exception as e:
            print(f"Web of Science error: {e}")
            return []


class PubmedFetcher:
    """NCBI PubMed E-utilities fetcher.

    Optional skill-local .env values:
    - NCBI_API_KEY: increases E-utilities rate limits.
    - NCBI_EMAIL: identifies the caller per NCBI guidance.
    - NCBI_TOOL: custom tool name shown to NCBI; defaults to sci-search.
    """
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self):
        self.api_key = get_config_value("NCBI_API_KEY")
        self.email = get_config_value("NCBI_EMAIL")
        self.tool = get_config_value("NCBI_TOOL", "sci-search")

    def _request(self, url: str, params: Dict, timeout: int = 20) -> bytes:
        payload = dict(params)
        payload["tool"] = self.tool
        if self.email:
            payload["email"] = self.email
        if self.api_key:
            payload["api_key"] = self.api_key

        req = urllib.request.Request(
            f"{url}?{urllib.parse.urlencode(payload)}",
            headers={"User-Agent": f"{self.tool}/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    @staticmethod
    def _text(node: Optional[ET.Element]) -> str:
        if node is None or node.text is None:
            return ""
        return " ".join(node.text.split())

    @classmethod
    def _collect_text(cls, node: Optional[ET.Element]) -> str:
        if node is None:
            return ""
        return " ".join(" ".join(node.itertext()).split())

    @classmethod
    def _parse_article(cls, article: ET.Element, pmid: str) -> Dict:
        medline = article.find("MedlineCitation")
        pubmed_data = article.find("PubmedData")
        article_node = medline.find("Article") if medline is not None else None
        journal_node = article_node.find("Journal") if article_node is not None else None
        journal_issue = journal_node.find("JournalIssue") if journal_node is not None else None
        pub_date = journal_issue.find("PubDate") if journal_issue is not None else None

        title = cls._collect_text(article_node.find("ArticleTitle") if article_node is not None else None)
        journal = cls._text(journal_node.find("Title") if journal_node is not None else None)
        if not journal:
            journal = cls._text(journal_node.find("ISOAbbreviation") if journal_node is not None else None)

        year = cls._text(pub_date.find("Year") if pub_date is not None else None)
        if not year:
            medline_date = cls._text(pub_date.find("MedlineDate") if pub_date is not None else None)
            match = re.search(r"\d{4}", medline_date)
            year = match.group(0) if match else ""

        authors = []
        author_list = article_node.find("AuthorList") if article_node is not None else None
        if author_list is not None:
            for author in author_list.findall("Author"):
                collective = cls._text(author.find("CollectiveName"))
                if collective:
                    authors.append(collective)
                    continue
                last_name = cls._text(author.find("LastName"))
                initials = cls._text(author.find("Initials"))
                fore_name = cls._text(author.find("ForeName"))
                if last_name and initials:
                    authors.append(f"{last_name} {initials}")
                elif fore_name or last_name:
                    authors.append(" ".join(part for part in (fore_name, last_name) if part))

        abstracts = []
        abstract_node = article_node.find("Abstract") if article_node is not None else None
        if abstract_node is not None:
            for abstract_text in abstract_node.findall("AbstractText"):
                label = abstract_text.attrib.get("Label", "")
                text = cls._collect_text(abstract_text)
                if text:
                    abstracts.append(f"{label}: {text}" if label else text)

        doi = ""
        if pubmed_data is not None:
            article_ids = pubmed_data.find("ArticleIdList")
            if article_ids is not None:
                for article_id in article_ids.findall("ArticleId"):
                    if article_id.attrib.get("IdType", "").lower() == "doi":
                        doi = cls._text(article_id)
                        break

        mesh_terms = []
        mesh_heading_list = medline.find("MeshHeadingList") if medline is not None else None
        if mesh_heading_list is not None:
            for heading in mesh_heading_list.findall("MeshHeading"):
                descriptor = cls._text(heading.find("DescriptorName"))
                if descriptor:
                    mesh_terms.append(descriptor)

        return {
            "source": "pubmed",
            "title": title or "Unknown",
            "authors": authors,
            "year": year,
            "journal": journal,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi": doi,
            "pmid": pmid,
            "abstract": " ".join(abstracts),
            "mesh_terms": mesh_terms,
        }

    @staticmethod
    def _scrub_api_key(message: str) -> str:
        """Redact api_key query params so keys never leak via printed errors."""
        return re.sub(r'(api_key=)[^&\s]+', r'\1[REDACTED]', message)

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "sort": "relevance",
        }
        try:
            search_data = json.loads(self._request(self.ESEARCH_URL, params).decode("utf-8"))
            ids = search_data.get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            fetch_xml = self._request(
                self.EFETCH_URL,
                {
                    "db": "pubmed",
                    "id": ",".join(ids),
                    "retmode": "xml",
                },
            ).decode("utf-8")
            root = ET.fromstring(fetch_xml)

            papers = []
            for article in root.findall("PubmedArticle"):
                medline = article.find("MedlineCitation")
                pmid = self._text(medline.find("PMID") if medline is not None else None)
                if pmid:
                    papers.append(self._parse_article(article, pmid))

            return papers
        except Exception as e:
            print(f"PubMed error: {self._scrub_api_key(str(e))}")
            return []

def format_markdown(paper: Dict, index: int) -> str:
    metrics = paper.get('journal_metrics', get_journal_metrics(paper.get('journal', '')))

    status_icon = ""
    if metrics:
        if metrics.get('is_nature_science_advmat'): status_icon = " **Priority journal**"
        elif metrics.get('is_top_journal'): status_icon = " **High-impact journal**"

    source_label = paper['source'].upper()
    if paper['source'] == 'wos':
        source_label = "Web of Science"

    lines = [
        f"### {index}. {paper['title']}{status_icon}",
        f"- **Authors:** {', '.join(paper['authors'][:3])}" + (" et al." if len(paper['authors']) > 3 else ""),
        f"- **Year:** {paper['year']} | **Source:** {source_label}",
    ]

    if paper.get('journal'):
        lines.append(f"- **Journal:** {paper['journal']}")

    if metrics:
        lines.append(f"- **Metrics:** JCR {metrics.get('jcr_partition', 'N/A')} | IF {metrics.get('impact_factor', 'N/A')} | {metrics.get('chinese_partition', 'N/A')}")

    if paper.get('times_cited') != "" and paper.get('times_cited') is not None:
        lines.append(f"- **Times Cited:** {paper['times_cited']}")

    lines.append(f"- **Link:** {paper['url']}")
    if paper.get('abstract'):
        lines.append(f"- **Abstract:** {paper['abstract'][:300]}...")

    return "\n".join(lines)


def dedupe_results(results: List[Dict]) -> List[Dict]:
    """Deduplicate cross-source results while keeping first-seen order."""
    seen = set()
    deduped = []

    for paper in results:
        key = (
            paper.get('source', ''),
            paper.get('url', ''),
            paper.get('doi', ''),
            paper.get('title', '').strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(paper)

    return deduped

def main():
    import argparse
    configure_windows_console()
    parser = argparse.ArgumentParser(description='Sci Search Tool')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--output', help='Output to markdown file')
    parser.add_argument('--source', choices=['all', 'arxiv', 'pubmed', 'wos'], default='all',
                        help='Search source (default: all available)')
    parser.add_argument('--library', default=str(LIBRARY_PATH), help='Path to library cache JSON')
    parser.add_argument('--no-cache', action='store_true', help='Skip writing search results to library cache')
    args = parser.parse_args()

    results = []
    wos = WoSFetcher()

    print(f"Searching for: {args.query}...")

    if args.source in ('all', 'arxiv'):
        print("  - arXiv...")
        results.extend(ArxivFetcher().search(args.query, args.limit))
        time.sleep(RATE_LIMIT_DELAY)

    if args.source in ('all', 'pubmed'):
        print("  - PubMed...")
        results.extend(PubmedFetcher().search(args.query, args.limit))
        time.sleep(RATE_LIMIT_DELAY)

    if args.source in ('all', 'wos'):
        if wos.is_available():
            print("  - Web of Science...")
            results.extend(wos.search(args.query, args.limit))
        elif args.source == 'wos':
            print("  WOS_API_KEY is not configured in skills/sci-search/.env. Get a free key at: https://developer.clarivate.com/apis/wos-starter")
            return
        else:
            print("  Web of Science skipped (WOS_API_KEY is not configured in skills/sci-search/.env)")

    results = dedupe_results(results)

    if not results:
        print("No results found.")
        return

    if not args.no_cache:
        PaperLibrary(args.library).extend_papers(results)
        print(f"Cached {len(results)} result(s) to {args.library}")

    md_output = [f"# Search Results: {args.query}\n"]
    for i, p in enumerate(results, 1):
        md_output.append(format_markdown(p, i))
        md_output.append("-" * 40)
        print(f"Found: {p['title'][:60]}...")

    final_md = "\n\n".join(md_output)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(final_md)
        print(f"\nDone! Results saved to {args.output}")
    else:
        print("\n" + final_md)

if __name__ == "__main__":
    main()

