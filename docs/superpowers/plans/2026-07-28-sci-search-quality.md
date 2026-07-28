# Sci-Search Quality Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the default literature search query WoS, Springer Metadata,
Springer Open Access, and Scopus in that order, with reliable year bounds,
recent sorting, citation parsing, and cross-source deduplication.

**Architecture:** Keep the existing fetcher classes and sequential CLI flow in
`sci_search.py`. Add small shared functions for argument validation,
post-processing, and paper identity, while each fetcher remains responsible for
its provider's query syntax. Unit tests mock network calls and fetchers; one
bounded live query verifies the configured APIs after deterministic tests pass.

**Tech Stack:** Python 3.11, standard-library `argparse`, `urllib`, `json`,
`unittest`, `unittest.mock`, Conda environment `aut-sci-write`.

## Global Constraints

- `--source all` runs only WoS, Springer Metadata, Springer Open Access, and
  Scopus, in that exact order.
- arXiv, PubMed, Semantic Scholar, and OpenAlex remain available through an
  explicit `--source` value.
- `--limit` remains a per-source limit.
- `--year-from` and `--year-to` are optional inclusive four-digit years.
- `--sort` accepts `relevance` or `recent` and defaults to `recent`.
- Missing years are excluded when a year bound is active.
- Do not add IEEE, expand journal metrics, migrate existing cache data, add
  concurrency, or introduce a new search adapter framework.
- Never print, document, commit, or assert a real API credential.
- Preserve the existing source file style and keep changes scoped to
  `sci-search` behavior and its documentation.

---

### Task 1: Cross-Source Paper Identity

**Files:**

- Modify: `tests/test_sci_search.py`
- Modify: `skills/sci-search/sci_search.py:222-270`
- Modify: `skills/sci-search/sci_search.py:950-967`

**Interfaces:**

- Produces: `normalize_doi(value: str) -> str`
- Produces: `normalize_title(value: str) -> str`
- Produces: `papers_match(left: Dict, right: Dict) -> bool`
- Updates: `PaperLibrary.add_paper(paper: Dict) -> None`
- Updates: `dedupe_results(results: List[Dict]) -> List[Dict]`

- [ ] **Step 1: Add failing DOI, title-fallback, and cache identity tests**

Add `unittest.mock` only when needed by later tasks. Extend
`SciSearchTests` with these concrete cases:

```python
def test_dedupe_results_uses_normalized_doi_across_sources(self):
    wos = {
        "source": "wos",
        "title": "GNSS NLOS Mitigation",
        "url": "https://example.test/wos",
        "doi": "10.1000/GNSS.1",
    }
    scopus = {
        "source": "scopus",
        "title": "A different provider title",
        "url": "https://example.test/scopus",
        "doi": "https://doi.org/10.1000/gnss.1",
    }

    self.assertEqual(self.module.dedupe_results([wos, scopus]), [wos])

def test_dedupe_results_falls_back_to_title_when_either_doi_is_missing(self):
    without_doi = {
        "source": "springer_meta",
        "title": "GNSS-NLOS: Mitigation!",
        "url": "https://example.test/meta",
        "doi": "",
    }
    with_doi = {
        "source": "scopus",
        "title": "gnss nlos mitigation",
        "url": "https://example.test/scopus",
        "doi": "10.1000/gnss.2",
    }

    self.assertEqual(
        self.module.dedupe_results([without_doi, with_doi]),
        [without_doi],
    )

def test_dedupe_results_keeps_same_title_with_two_different_dois(self):
    first = {"source": "wos", "title": "Shared", "url": "a", "doi": "10.1/a"}
    second = {"source": "scopus", "title": "Shared", "url": "b", "doi": "10.1/b"}

    self.assertEqual(self.module.dedupe_results([first, second]), [first, second])

def test_normalize_title_preserves_unicode_words(self):
    self.assertEqual(self.module.normalize_title("卫星-导航！"), "卫星 导航")

def test_paper_library_updates_cross_source_duplicate_by_doi(self):
    with tempfile.TemporaryDirectory() as tmp_dir:
        library = self.module.PaperLibrary(str(Path(tmp_dir) / "library.json"))
        library.add_paper({
            "source": "wos", "title": "Paper", "authors": [], "year": "2025",
            "url": "a", "doi": "10.1000/PAPER",
        })
        library.add_paper({
            "source": "scopus", "title": "Paper from Scopus", "authors": [],
            "year": "2025", "url": "b",
            "doi": "https://doi.org/10.1000/paper",
        })

    self.assertEqual(len(library.papers), 1)
    self.assertEqual(library.papers[0]["source"], "scopus")
```

- [ ] **Step 2: Run the focused tests and confirm the current key fails**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
```

Expected: the new cross-source DOI and title tests fail because the current key
contains `source` and URL.

- [ ] **Step 3: Implement one pairwise identity rule for results and cache**

Add these helpers before `PaperLibrary`:

```python
def normalize_doi(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("https://doi.org/"):
        normalized = normalized[len("https://doi.org/"):]
    if normalized.startswith("doi:"):
        normalized = normalized[len("doi:"):].strip()
    return normalized


def normalize_title(value: str) -> str:
    lowered = str(value or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[\W_]+", " ", lowered)).strip()


def papers_match(left: Dict, right: Dict) -> bool:
    left_doi = normalize_doi(left.get("doi", ""))
    right_doi = normalize_doi(right.get("doi", ""))
    if left_doi and right_doi:
        return left_doi == right_doi

    left_title = normalize_title(left.get("title", ""))
    right_title = normalize_title(right.get("title", ""))
    return bool(left_title and right_title and left_title == right_title)
```

Remove `_paper_key`. In `PaperLibrary.add_paper`, replace tuple equality with
`papers_match(existing, paper)`. Replace `dedupe_results`' set key with a small
pairwise check:

```python
def dedupe_results(results: List[Dict]) -> List[Dict]:
    """Deduplicate cross-source results while keeping first-seen order."""
    deduped = []
    for paper in results:
        if any(papers_match(existing, paper) for existing in deduped):
            continue
        deduped.append(paper)
    return deduped
```

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run the Task 1 command again. Expected: all `test_sci_search.py` tests pass.

- [ ] **Step 5: Commit the paper identity change**

```powershell
git add -- tests/test_sci_search.py skills/sci-search/sci_search.py
git commit -m "fix: deduplicate sci-search results across sources"
```

---

### Task 2: Year Validation and Shared Post-Processing

**Files:**

- Modify: `tests/test_sci_search.py`
- Modify: `skills/sci-search/sci_search.py:8-19`
- Modify: `skills/sci-search/sci_search.py:950-980`

**Interfaces:**

- Produces: `parse_year(value: str) -> int`
- Produces: `parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace`
- Produces: `filter_results_by_year(results, year_from, year_to) -> List[Dict]`
- Produces: `sort_results(results, sort_mode) -> List[Dict]`
- Produces: `post_process_results(results, year_from, year_to, sort_mode) -> List[Dict]`
- Consumes: `dedupe_results(results: List[Dict]) -> List[Dict]`

- [ ] **Step 1: Add failing argument and post-processing tests**

Import `unittest.mock` later in Task 4. Add:

```python
def test_parse_args_rejects_invalid_year_bounds(self):
    invalid_commands = [
        ["query", "--year-from", "22"],
        ["query", "--year-to", "year"],
        ["query", "--year-from", "2026", "--year-to", "2022"],
    ]
    for argv in invalid_commands:
        with self.subTest(argv=argv), self.assertRaises(SystemExit):
            self.module.parse_args(argv)

def test_parse_args_defaults_to_recent_sort(self):
    args = self.module.parse_args(["query"])

    self.assertEqual(args.sort, "recent")
    self.assertIsNone(args.year_from)
    self.assertIsNone(args.year_to)

def test_post_process_filters_inclusive_years_and_sorts_recent(self):
    papers = [
        {"source": "wos", "title": "2023 first", "doi": "1", "year": "2023"},
        {"source": "wos", "title": "unknown", "doi": "2", "year": ""},
        {"source": "wos", "title": "2025", "doi": "3", "year": "2025"},
        {"source": "wos", "title": "2023 second", "doi": "4", "year": "2023"},
        {"source": "wos", "title": "2021", "doi": "5", "year": "2021"},
    ]

    results = self.module.post_process_results(papers, 2022, 2025, "recent")

    self.assertEqual(
        [paper["title"] for paper in results],
        ["2025", "2023 first", "2023 second"],
    )

def test_post_process_preserves_provider_order_for_relevance(self):
    papers = [
        {"source": "wos", "title": "Older", "doi": "1", "year": "2022"},
        {"source": "wos", "title": "Newer", "doi": "2", "year": "2026"},
    ]

    results = self.module.post_process_results(papers, None, None, "relevance")

    self.assertEqual(results, papers)
```

- [ ] **Step 2: Run the focused tests and verify missing helpers fail**

Run the Task 1 test command. Expected: errors report that `parse_args` and
`post_process_results` do not exist.

- [ ] **Step 3: Add CLI parsing and shared result processing**

Move `argparse` to the module imports. Add:

```python
SOURCE_CHOICES = [
    "all", "arxiv", "pubmed", "wos", "springer", "springer_meta",
    "springer_oa", "scopus", "semantic_scholar", "openalex",
]


def parse_year(value: str) -> int:
    if not re.fullmatch(r"\d{4}", value):
        raise argparse.ArgumentTypeError("year must contain exactly four digits")
    return int(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sci Search Tool")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", help="Output to markdown file")
    parser.add_argument("--source", choices=SOURCE_CHOICES, default="all",
                        help="Search source (default: enabled API sources)")
    parser.add_argument("--year-from", type=parse_year)
    parser.add_argument("--year-to", type=parse_year)
    parser.add_argument("--sort", choices=["relevance", "recent"], default="recent")
    parser.add_argument("--library", default=str(LIBRARY_PATH),
                        help="Path to library cache JSON")
    parser.add_argument("--no-cache", action="store_true",
                        help="Skip writing search results to library cache")
    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if (
        args.year_from is not None
        and args.year_to is not None
        and args.year_from > args.year_to
    ):
        parser.error("--year-from must not be greater than --year-to")
    return args
```

Add the post-processing functions immediately after `dedupe_results`:

```python
def _paper_year(paper: Dict) -> Optional[int]:
    value = str(paper.get("year", "")).strip()
    return int(value) if re.fullmatch(r"\d{4}", value) else None


def filter_results_by_year(
    results: List[Dict],
    year_from: Optional[int],
    year_to: Optional[int],
) -> List[Dict]:
    if year_from is None and year_to is None:
        return list(results)
    filtered = []
    for paper in results:
        year = _paper_year(paper)
        if year is None:
            continue
        if year_from is not None and year < year_from:
            continue
        if year_to is not None and year > year_to:
            continue
        filtered.append(paper)
    return filtered


def sort_results(results: List[Dict], sort_mode: str) -> List[Dict]:
    if sort_mode == "relevance":
        return list(results)
    return sorted(results, key=lambda paper: _paper_year(paper) or -1, reverse=True)


def post_process_results(
    results: List[Dict],
    year_from: Optional[int],
    year_to: Optional[int],
    sort_mode: str,
) -> List[Dict]:
    filtered = filter_results_by_year(results, year_from, year_to)
    return sort_results(dedupe_results(filtered), sort_mode)
```

Do not wire these helpers into `main` until Task 4, so this task remains
independently testable.

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run the Task 1 test command. Expected: all search unit tests pass.

- [ ] **Step 5: Commit the shared CLI and post-processing behavior**

```powershell
git add -- tests/test_sci_search.py skills/sci-search/sci_search.py
git commit -m "feat: add sci-search year and sort processing"
```

---

### Task 3: Provider Query Construction and WoS Citations

**Files:**

- Modify: `tests/test_sci_search.py`
- Modify: `skills/sci-search/sci_search.py:299-617`

**Interfaces:**

- Updates: `WoSFetcher.search(query, max_results=5, year_from=None,
  year_to=None, sort_mode="recent") -> List[Dict]`
- Updates: `SpringerMetaFetcher.search(query, max_results=5, year_from=None,
  year_to=None, sort_mode="recent") -> List[Dict]`
- Updates: `SpringerOpenAccessFetcher.search(query, max_results=5,
  year_from=None, year_to=None, sort_mode="recent") -> List[Dict]`
- Updates: `ScopusFetcher.search(query, max_results=5, year_from=None,
  year_to=None, sort_mode="recent") -> List[Dict]`
- Produces: `_springer_query(query, year_from, year_to) -> str`

- [ ] **Step 1: Add a reusable fake HTTP response and failing request tests**

Add imports and helper:

```python
from unittest import mock
from urllib.parse import parse_qs, urlsplit


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.payload
```

Add focused tests using only synthetic key `test-key`:

```python
def test_wos_builds_bounded_recent_query_and_parses_citations(self):
    payload = {
        "hits": [{
            "uid": "WOS:1", "title": "GNSS NLOS", "names": {"authors": []},
            "source": {"sourceTitle": "Journal", "publishYear": 2025},
            "identifiers": {"doi": "10.1000/test"},
            "citations": [{"db": "WOS", "count": 12}],
        }]
    }
    with mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
            mock.patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=FakeResponse(payload),
            ) as urlopen:
        papers = self.module.WoSFetcher().search(
            "GNSS NLOS", 5, year_from=2022, year_to=2026, sort_mode="recent"
        )

    query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
    self.assertEqual(query["q"], ["TS=(GNSS NLOS) AND PY=(2022-2026)"])
    self.assertEqual(query["sortField"], ["PY+D"])
    self.assertEqual(papers[0]["times_cited"], 12)

def test_wos_relevance_query_has_no_sort_field(self):
    with mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
            mock.patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=FakeResponse({"hits": []}),
            ) as urlopen:
        self.module.WoSFetcher().search("GNSS", sort_mode="relevance")

    query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
    self.assertNotIn("sortField", query)

def test_springer_fetchers_use_unquoted_keywords_and_date_bounds(self):
    for fetcher_class in (
        self.module.SpringerMetaFetcher,
        self.module.SpringerOpenAccessFetcher,
    ):
        with self.subTest(fetcher=fetcher_class.__name__), \
                mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
                mock.patch.object(
                    self.module.urllib.request,
                    "urlopen",
                    return_value=FakeResponse({"records": []}),
                ) as urlopen:
            fetcher_class().search("GNSS NLOS", year_from=2022, year_to=2026)

        query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
        self.assertEqual(
            query["q"],
            ["keyword:GNSS NLOS datefrom:2022-01-01 dateto:2026-12-31"],
        )

def test_scopus_uses_non_phrase_year_query_and_recent_sort(self):
    payload = {"search-results": {"entry": []}}
    with mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
            mock.patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=FakeResponse(payload),
            ) as urlopen:
        self.module.ScopusFetcher().search(
            "GNSS NLOS", year_from=2022, year_to=2026, sort_mode="recent"
        )

    query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
    self.assertEqual(
        query["query"],
        ["TITLE-ABS-KEY(GNSS NLOS) AND PUBYEAR > 2021 AND PUBYEAR < 2027"],
    )
    self.assertEqual(query["sort"], ["-coverDate"])
```

- [ ] **Step 2: Run the focused tests and verify signature/query failures**

Run the Task 1 test command. Expected: the new tests fail because fetchers do
not accept year or sort arguments and WoS still reads `timesCited`.

- [ ] **Step 3: Implement provider-specific query parameters**

Change each of the four search signatures to accept the typed optional years
and `sort_mode`.

For WoS, build the query and params exactly as follows:

```python
wos_query = f"TS=({query})"
if year_from is not None or year_to is not None:
    start_year = year_from if year_from is not None else 1900
    end_year = year_to if year_to is not None else datetime.now().year
    wos_query += f" AND PY=({start_year}-{end_year})"
params = {"q": wos_query, "db": "WOS", "limit": min(max_results, 10), "page": 1}
if sort_mode == "recent":
    params["sortField"] = "PY+D"
```

Parse citations with:

```python
citations = hit.get("citations", [])
times_cited = next(
    (
        item.get("count", "")
        for item in citations
        if isinstance(item, dict) and "count" in item
    ),
    "",
)
```

Use `times_cited` in the paper dictionary.

Add the shared Springer query helper:

```python
def _springer_query(
    query: str,
    year_from: Optional[int],
    year_to: Optional[int],
) -> str:
    parts = [f"keyword:{query}"]
    if year_from is not None:
        parts.append(f"datefrom:{year_from}-01-01")
    if year_to is not None:
        parts.append(f"dateto:{year_to}-12-31")
    return " ".join(parts)
```

Use it for the `q` parameter in both Springer fetchers. `sort_mode` is accepted
for a consistent call contract but does not add a Springer API parameter.

For Scopus:

```python
scopus_query = f"TITLE-ABS-KEY({query})"
if year_from is not None:
    scopus_query += f" AND PUBYEAR > {year_from - 1}"
if year_to is not None:
    scopus_query += f" AND PUBYEAR < {year_to + 1}"
params = {
    "query": scopus_query,
    "count": min(max_results, 25),
    "start": 0,
    "sort": "-coverDate" if sort_mode == "recent" else "-relevancy",
}
```

- [ ] **Step 4: Run focused tests and static checks**

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
conda run --no-capture-output -n aut-sci-write python -m ruff check --select 'F,E9' skills/sci-search/sci_search.py tests/test_sci_search.py
conda run -n aut-sci-write python -m compileall -q skills/sci-search/sci_search.py tests/test_sci_search.py
```

Expected: all search tests pass, Ruff reports no runtime or syntax-class
violations, and both Python files compile. The repository has 53 pre-existing
full-Ruff findings in these files; clearing unrelated style and modernization
findings is outside this task.

- [ ] **Step 5: Commit provider query fixes**

```powershell
git add -- tests/test_sci_search.py skills/sci-search/sci_search.py
git commit -m "fix: improve sci-search provider queries"
```

---

### Task 4: Default Source Order and CLI Wiring

**Files:**

- Modify: `tests/test_sci_search.py`
- Modify: `skills/sci-search/sci_search.py:969-1078`

**Interfaces:**

- Updates: `main(argv: Optional[List[str]] = None) -> None`
- Consumes: `parse_args(argv)` and `post_process_results(...)`
- Consumes: the four extended fetcher `search(...)` signatures from Task 3

- [ ] **Step 1: Add failing default-order and explicit-source tests**

Add simple fakes within the test method so no API or real credential is used:

```python
def test_main_default_source_order_uses_only_four_enabled_sources(self):
    calls = []

    class KeyedFetcher:
        def __init__(self, name):
            self.name = name

        def is_available(self):
            return True

        def search(self, query, limit, **kwargs):
            calls.append(self.name)
            return []

    with mock.patch.object(self.module, "WoSFetcher", lambda: KeyedFetcher("wos")), \
            mock.patch.object(
                self.module, "SpringerMetaFetcher", lambda: KeyedFetcher("springer_meta")
            ), \
            mock.patch.object(
                self.module, "SpringerOpenAccessFetcher", lambda: KeyedFetcher("springer_oa")
            ), \
            mock.patch.object(self.module, "ScopusFetcher", lambda: KeyedFetcher("scopus")), \
            mock.patch.object(self.module.ArxivFetcher, "search") as arxiv, \
            mock.patch.object(self.module.PubmedFetcher, "search") as pubmed, \
            mock.patch.object(self.module.SemanticScholarFetcher, "search") as semantic, \
            mock.patch.object(self.module.OpenAlexFetcher, "search") as openalex, \
            mock.patch.object(self.module.time, "sleep"):
        self.module.main(["GNSS NLOS", "--no-cache"])

    self.assertEqual(calls, ["wos", "springer_meta", "springer_oa", "scopus"])
    arxiv.assert_not_called()
    pubmed.assert_not_called()
    semantic.assert_not_called()
    openalex.assert_not_called()

def test_main_keeps_non_default_sources_explicitly_accessible(self):
    cases = [
        ("arxiv", "ArxivFetcher"),
        ("pubmed", "PubmedFetcher"),
        ("semantic_scholar", "SemanticScholarFetcher"),
        ("openalex", "OpenAlexFetcher"),
    ]
    for source, class_name in cases:
        fetcher = mock.Mock()
        fetcher.search.return_value = []
        with self.subTest(source=source), \
                mock.patch.object(self.module, class_name, return_value=fetcher), \
                mock.patch.object(self.module.time, "sleep"):
            self.module.main(["query", "--source", source, "--no-cache"])
        fetcher.search.assert_called_once_with("query", 5)

def test_main_springer_source_runs_metadata_then_open_access(self):
    calls = []

    class SpringerFetcher:
        def __init__(self, name):
            self.name = name

        def is_available(self):
            return True

        def search(self, query, limit, **kwargs):
            calls.append(self.name)
            return []

    with mock.patch.object(
            self.module,
            "SpringerMetaFetcher",
            lambda: SpringerFetcher("springer_meta"),
        ), mock.patch.object(
            self.module,
            "SpringerOpenAccessFetcher",
            lambda: SpringerFetcher("springer_oa"),
        ), mock.patch.object(self.module.time, "sleep"):
        self.module.main(["query", "--source", "springer", "--no-cache"])

    self.assertEqual(calls, ["springer_meta", "springer_oa"])
```

- [ ] **Step 2: Run focused tests and verify the old default order fails**

Run the Task 1 test command. Expected: `main` rejects the argv argument or the
recorded order includes arXiv and PubMed before WoS.

- [ ] **Step 3: Wire parsed options into the sequential CLI flow**

Change `main` to accept `argv`, call `parse_args(argv)`, and delete its local
parser construction:

```python
def main(argv: Optional[List[str]] = None):
    configure_windows_console()
    args = parse_args(argv)
```

Order the branches as WoS, Springer Metadata, Springer Open Access, and Scopus.
Use `args.source in ("all", ...)` only for those four. Pass these keyword
arguments to each four-source fetcher:

```python
year_from=args.year_from,
year_to=args.year_to,
sort_mode=args.sort,
```

After Scopus, keep arXiv, PubMed, Semantic Scholar, and OpenAlex branches, but
make each branch explicit-only, for example:

```python
if args.source == "arxiv":
    results.extend(ArxivFetcher().search(args.query, args.limit))
```

Preserve `--source springer` as Metadata followed by Open Access. Preserve the
current missing-key behavior and redacted error messages. Before caching,
replace the direct dedupe call with:

```python
results = post_process_results(
    results,
    year_from=args.year_from,
    year_to=args.year_to,
    sort_mode=args.sort,
)
```

- [ ] **Step 4: Run search tests, complete test suite, and Ruff**

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
conda run -n aut-sci-write python -m unittest discover -s tests -p "test_*.py" -v
conda run --no-capture-output -n aut-sci-write python -m ruff check --select 'F,E9' skills/sci-search/sci_search.py tests/test_sci_search.py
conda run -n aut-sci-write python -m compileall -q skills/sci-search/sci_search.py tests/test_sci_search.py
```

Expected: search tests and the full repository suite pass; the targeted Ruff
rules pass; and both modified Python files compile.

- [ ] **Step 5: Commit default source orchestration**

```powershell
git add -- tests/test_sci_search.py skills/sci-search/sci_search.py
git commit -m "feat: prioritize configured sci-search sources"
```

---

### Task 5: Documentation, Live Verification, and Progress Record

**Files:**

- Modify: `skills/sci-search/SKILL.md`
- Modify: `README.md`
- Modify: `docs/index.html`
- Modify: `progress.md`

**Interfaces:**

- Documents the final CLI and default source contract from Tasks 2-4.
- Records deterministic and live verification without exposing credentials.

- [ ] **Step 1: Update user-facing search documentation**

Make these exact content changes:

- Replace every claim that default search simultaneously queries seven sources
  with the four-source default order: WoS, Springer Metadata, Springer Open
  Access, Scopus.
- State that arXiv, PubMed, Semantic Scholar, and OpenAlex require explicit
  `--source` selection.
- Replace "Search all sources" examples with "Search enabled default sources".
- Add one bounded recent-search example:

```powershell
python skills/sci-search/sci_search.py "GNSS NLOS" --year-from 2022 --year-to 2026 --sort recent --limit 5
```

- Explain that `--limit` applies per source and `--sort recent` is the default.
- Update both English and Chinese descriptions in `README.md`, the source count
  comments in both repository trees, and the `sci-search` card text in
  `docs/index.html`.

- [ ] **Step 2: Verify documentation matches the implemented contract**

```powershell
rg -n "Seven-Source|seven sources|7 sources|七源|七大数据源|Search all sources" README.md skills/sci-search/SKILL.md docs/index.html
conda run -n aut-sci-write python skills/sci-search/sci_search.py --help
```

Expected: the stale-claim search returns no matches. CLI help lists
`--year-from`, `--year-to`, and `--sort {relevance,recent}`.

- [ ] **Step 3: Run deterministic final verification**

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p "test_*.py" -v
conda run --no-capture-output -n aut-sci-write python -m ruff check --select 'F,E9' skills/sci-search/sci_search.py tests/test_sci_search.py
conda run -n aut-sci-write python -m compileall -q skills/sci-search/sci_search.py tests/test_sci_search.py
git diff --check 9849e59..HEAD
```

Expected: the full suite passes, targeted Ruff and compilation checks pass,
and Git reports no whitespace errors.

- [ ] **Step 4: Run one bounded live API check without cache writes**

```powershell
conda run -n aut-sci-write python skills/sci-search/sci_search.py "GNSS NLOS" --year-from 2022 --year-to 2026 --sort recent --limit 2 --source all --no-cache
```

Verify from sanitized output that the attempted order is WoS, Springer Nature
(Meta), Springer Nature (Open Access), Scopus; every returned paper has a year
from 2022 through 2026; final output is descending by year; and no credential
appears. Provider downtime or quota errors must be recorded as observed rather
than converted into a false pass.

- [ ] **Step 5: Append the implementation record to `progress.md`**

Append one entry with this structure and the exact observed test outcomes:

```markdown
## 2026-07-28 - Task: Improve sci-search default strategy and result quality

### What was done

- Changed the default search to WoS, Springer Metadata, Springer Open Access,
  and Scopus in priority order while retaining explicit access to other sources.
- Added inclusive year bounds, recent/relevance sorting, corrected WoS citation
  parsing, provider-aware queries, and cross-source paper identity.
- Updated user documentation for the revised search contract.

### Testing

- `conda run -n aut-sci-write python -m unittest discover -s tests -p "test_*.py" -v` - all tests passed.
- `conda run --no-capture-output -n aut-sci-write python -m ruff check --select 'F,E9' skills/sci-search/sci_search.py tests/test_sci_search.py` - passed; 53 pre-existing full-Ruff findings remain outside this task.
- `conda run -n aut-sci-write python -m compileall -q skills/sci-search/sci_search.py tests/test_sci_search.py` - passed.
- Bounded `GNSS NLOS` live query - record the four attempted sources, returned
  year range, ordering, and any provider-specific availability error exactly as
  observed without including API keys.
- `git diff --check 9849e59..HEAD` - passed.

### Notes

- `skills/sci-search/sci_search.py` - revised source orchestration, provider
  queries, citation parsing, result processing, and cache identity.
- `tests/test_sci_search.py` - added deterministic coverage for the revised
  search contract.
- `skills/sci-search/SKILL.md` - documented source defaults and new CLI options.
- `README.md` - updated English and Chinese search descriptions.
- `docs/index.html` - updated the public sci-search feature description.
- `progress.md` - recorded implementation and verification evidence.
- Rollback point: commit `9849e59`; `git switch main` returns to the unchanged
  main branch, or `git switch -c sci-search-before-fix 9849e59` creates a
  recovery branch at the pre-implementation state.
```

- [ ] **Step 6: Commit documentation and the verified progress record**

```powershell
git add -- README.md docs/index.html skills/sci-search/SKILL.md progress.md
git commit -m "docs: update sci-search default strategy"
git status --short --branch
```

Expected: the commit succeeds and `git status` reports a clean `dev` branch.
