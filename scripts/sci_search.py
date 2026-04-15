#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Sci Search - Academic Paper Search & Metrics Tool
Combined logic from paper_fetch.py and smart_paper_output.py
"""

import os
import sys
import codecs
import json
import time
import urllib.request
import urllib.parse
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

# Configuration
_SCRIPT_DIR = Path(__file__).parent
LIBRARY_PATH = _SCRIPT_DIR.parent / "library.json"
JOURNAL_DB_PATH = _SCRIPT_DIR / "journal_db.json"

# API rate-limit delay (seconds)
RATE_LIMIT_DELAY = 1.0

# Journal metrics database fallback (overridden by journal_db.json when present)
DEFAULT_JOURNAL_DB = {
    'Advanced Materials': {
        'jcr_partition': 'Q1',
        'impact_factor': '29.4',
        '5_year_if': '28.9',
        'chinese_partition': '材料科学1区 Top',
        'category': 'Materials Science, Multidisciplinary',
        'publisher': 'Wiley',
        'is_top_journal': True,
        'is_nature_science_advmat': True,
        'notes': '顶刊，Advanced Materials系列，需重点标注'
    },
    'Nature': {
        'jcr_partition': 'Q1',
        'impact_factor': '64.8',
        '5_year_if': '59.2',
        'chinese_partition': '综合性期刊1区 Top',
        'category': 'Multidisciplinary Sciences',
        'publisher': 'Springer Nature',
        'is_top_journal': True,
        'is_nature_science_advmat': True,
        'notes': '顶刊，Nature系列，需重点标注'
    },
    'Science': {
        'jcr_partition': 'Q1',
        'impact_factor': '56.9',
        '5_year_if': '54.3',
        'chinese_partition': '综合性期刊1区 Top',
        'category': 'Multidisciplinary Sciences',
        'publisher': 'AAAS',
        'is_top_journal': True,
        'is_nature_science_advmat': True,
        'notes': '顶刊，Science系列，需重点标注'
    },
    'Nature Photonics': {
        'jcr_partition': 'Q1',
        'impact_factor': '35.0',
        '5_year_if': '32.5',
        'chinese_partition': '物理与天体物理1区',
        'category': 'Physics, Applied',
        'publisher': 'Springer Nature',
        'is_top_journal': True,
        'is_nature_science_advmat': True,
        'notes': 'Nature子刊，需重点标注'
    },
    'Nature Physics': {
        'jcr_partition': 'Q1',
        'impact_factor': '19.6',
        '5_year_if': '18.9',
        'chinese_partition': '物理与天体物理1区',
        'category': 'Physics, Multidisciplinary',
        'publisher': 'Springer Nature',
        'is_top_journal': True,
        'is_nature_science_advmat': True,
        'notes': 'Nature子刊，需重点标注'
    },
    'Nano Energy': {
        'jcr_partition': 'Q1',
        'impact_factor': '16.8',
        '5_year_if': '16.3',
        'chinese_partition': '材料科学1区',
        'category': 'Nanoscience & Nanotechnology',
        'publisher': 'Elsevier',
        'is_top_journal': True,
        'is_nature_science_advmat': False,
        'notes': '高影响力期刊'
    },
    'ACS Omega': {
        'jcr_partition': 'Q2',
        'impact_factor': '4.1',
        '5_year_if': '4.3',
        'chinese_partition': '化学3区',
        'category': 'Chemistry, Multidisciplinary',
        'publisher': 'American Chemical Society',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': 'ACS开源期刊'
    },
    'Ceramics International': {
        'jcr_partition': 'Q1',
        'impact_factor': '5.2',
        '5_year_if': '5.1',
        'chinese_partition': '材料科学2区',
        'category': 'Materials Science, Ceramics',
        'publisher': 'Elsevier',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': '陶瓷材料专业期刊'
    },
    'Journal of Luminescence': {
        'jcr_partition': 'Q2',
        'impact_factor': '3.6',
        '5_year_if': '3.5',
        'chinese_partition': '物理3区',
        'category': 'Optics',
        'publisher': 'Elsevier',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': '发光专业期刊'
    },
    'CrystEngComm': {
        'jcr_partition': 'Q2',
        'impact_factor': '3.1',
        '5_year_if': '3.2',
        'chinese_partition': '化学3区',
        'category': 'Chemistry, Multidisciplinary',
        'publisher': 'Royal Society of Chemistry',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': '晶体工程期刊'
    },
    'Colloids and Surfaces A: Physicochemical and Engineering Aspects': {
        'jcr_partition': 'Q2',
        'impact_factor': '5.2',
        '5_year_if': '5.0',
        'chinese_partition': '化学2区',
        'category': 'Chemistry, Physical',
        'publisher': 'Elsevier',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': '胶体与表面科学期刊'
    },
    'The Journal of Physical Chemistry Letters': {
        'jcr_partition': 'Q1',
        'impact_factor': '6.4',
        '5_year_if': '6.2',
        'chinese_partition': '化学2区',
        'category': 'Chemistry, Physical',
        'publisher': 'American Chemical Society',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': '物理化学快报'
    },
    'Journal of the American Ceramic Society': {
        'jcr_partition': 'Q2',
        'impact_factor': '3.9',
        '5_year_if': '3.8',
        'chinese_partition': '材料科学3区',
        'category': 'Materials Science, Ceramics',
        'publisher': 'Wiley',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': '美国陶瓷学会会刊'
    },
    'Optical Materials': {
        'jcr_partition': 'Q2',
        'impact_factor': '3.9',
        '5_year_if': '3.8',
        'chinese_partition': '材料科学3区',
        'category': 'Materials Science, Coatings & Films',
        'publisher': 'Elsevier',
        'is_top_journal': False,
        'is_nature_science_advmat': False,
        'notes': '光学材料期刊'
    },
    'Laser & Photonics Reviews': {
        'jcr_partition': 'Q1',
        'impact_factor': '11.0',
        '5_year_if': '10.5',
        'chinese_partition': '物理与天体物理1区',
        'category': 'Optics',
        'publisher': 'Wiley',
        'is_top_journal': True,
        'is_nature_science_advmat': False,
        'notes': '激光与光子学评论'
    },
    'Advanced Optical Materials': {
        'jcr_partition': 'Q1',
        'impact_factor': '9.0',
        '5_year_if': '8.7',
        'chinese_partition': '材料科学2区',
        'category': 'Materials Science, Multidisciplinary',
        'publisher': 'Wiley',
        'is_top_journal': True,
        'is_nature_science_advmat': True,
        'notes': 'Advanced Materials子刊，需重点标注'
    }
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

def get_journal_metrics(journal_name: str) -> Optional[Dict]:
    if not journal_name:
        return None

    # Exact match
    if journal_name in JOURNAL_DB:
        return JOURNAL_DB[journal_name]

    # Partial match
    journal_lower = journal_name.lower()
    for db_journal, metrics in JOURNAL_DB.items():
        if db_journal.lower() in journal_lower or journal_lower in db_journal.lower():
            return metrics

    # Abbreviations
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
        if abbrev in journal_lower:
            return JOURNAL_DB.get(full_name)
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
            except: return []
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
            with urllib.request.urlopen(url) as resp:
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

class PubmedFetcher:
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        params = {'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': max_results}
        try:
            with urllib.request.urlopen(f"{self.ESEARCH_URL}?{urllib.parse.urlencode(params)}") as resp:
                ids = json.loads(resp.read().decode('utf-8'))['esearchresult'].get('idlist', [])
            if not ids: return []

            with urllib.request.urlopen(f"{self.ESUMMARY_URL}?db=pubmed&id={','.join(ids)}&retmode=json") as resp:
                results = json.loads(resp.read().decode('utf-8'))['result']

            papers = []
            for pmid in ids:
                if pmid not in results: continue
                doc = results[pmid]
                paper = {
                    'source': 'pubmed',
                    'title': doc.get('title', 'Unknown'),
                    'authors': [a.get('name', '') for a in doc.get('authors', [])],
                    'year': (doc.get('pubdate') or '')[:4],
                    'journal': doc.get('source', ''),
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    'doi': doc.get('elocationid', '').replace('doi: ', '')
                }
                papers.append(paper)
            return papers
        except Exception as e:
            print(f"PubMed error: {e}")
            return []

def format_markdown(paper: Dict, index: int) -> str:
    metrics = paper.get('journal_metrics', get_journal_metrics(paper.get('journal', '')))

    status_icon = ""
    if metrics:
        if metrics.get('is_nature_science_advmat'): status_icon = " **🚨重点标注🚨**"
        elif metrics.get('is_top_journal'): status_icon = " **⭐高影响力⭐**"

    lines = [
        f"### {index}. {paper['title']}{status_icon}",
        f"- **Authors:** {', '.join(paper['authors'][:3])}" + (" et al." if len(paper['authors']) > 3 else ""),
        f"- **Year:** {paper['year']} | **Source:** {paper['source'].upper()}",
    ]

    if paper.get('journal'):
        lines.append(f"- **Journal:** {paper['journal']}")

    if metrics:
        lines.append(f"- **Metrics:** JCR {metrics.get('jcr_partition', 'N/A')} | IF {metrics.get('impact_factor', 'N/A')} | {metrics.get('chinese_partition', 'N/A')}")

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
    parser = argparse.ArgumentParser(description='Sci Search Tool')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--output', help='Output to markdown file')
    parser.add_argument('--library', default=str(LIBRARY_PATH), help='Path to library cache JSON')
    parser.add_argument('--no-cache', action='store_true', help='Skip writing search results to library cache')
    args = parser.parse_args()

    results = []
    print(f"Searching for: {args.query}...")
    results.extend(ArxivFetcher().search(args.query, args.limit))
    time.sleep(RATE_LIMIT_DELAY)
    results.extend(PubmedFetcher().search(args.query, args.limit))
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
