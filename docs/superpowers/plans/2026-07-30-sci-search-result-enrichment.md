# Sci-Search Result Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every author, merge approved metadata from duplicate provider
records, reconstruct OpenAlex abstracts, and produce a verified live GNSS NLOS
Markdown report.

**Architecture:** Keep the existing sequential fetchers and shared
post-processing flow in `sci_search.py`. Add one focused OpenAlex reconstruction
helper, one conservative record-merge helper, and one reusable provider-label
helper; `dedupe_results` will preserve first-seen order while replacing each
matched entry with a merged copy.

**Tech Stack:** Python 3.11, standard-library `unittest`,
`unittest.mock`, `urllib`, JSON, Conda environment `aut-sci-write`.

## Global Constraints

- Keep the default provider order unchanged: WoS, Springer Metadata, Springer
  Open Access, Scopus.
- Do not add providers, change provider queries, change result ranking, alter
  API credentials, or add an output format.
- Preserve the first-seen record's `source`, DOI, URL, year, journal, and
  citation value when already populated.
- A later record may replace only an abstract with a longer non-empty abstract
  or an author list with a longer non-empty list.
- Keep the Markdown abstract preview at 300 characters.
- Keep OpenAlex explicit-only; do not add it to `--source all`.
- Never print, fixture, document, or commit a real API key.
- Preserve existing file encoding and avoid unrelated formatting or
  refactoring.

---

### Task 1: Reconstruct OpenAlex Abstracts

**Files:**
- Modify: `tests/test_sci_search.py`
- Modify: `skills/sci-search/sci_search.py:800-865`

**Interfaces:**
- Consumes: OpenAlex `abstract_inverted_index` values from each work object.
- Produces: `reconstruct_openalex_abstract(index: object) -> str`.
- Produces: OpenAlex paper dictionaries whose `abstract` contains reconstructed
  text or `""`.

- [ ] **Step 1: Verify the focused baseline**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
```

Expected: every existing focused sci-search test passes before new tests are
added.

- [ ] **Step 2: Add failing reconstruction and fetcher tests**

Add these methods to `SciSearchTests`:

```python
def test_reconstruct_openalex_abstract_orders_repeated_tokens(self):
    index = {
        "GNSS": [0, 3],
        "signals": [1],
        "improve": [2],
    }
    reconstruct = getattr(
        self.module,
        "reconstruct_openalex_abstract",
        lambda value: None,
    )

    abstract = reconstruct(index)

    self.assertEqual(abstract, "GNSS signals improve GNSS")

def test_reconstruct_openalex_abstract_ignores_invalid_positions(self):
    reconstruct = getattr(
        self.module,
        "reconstruct_openalex_abstract",
        lambda value: None,
    )

    self.assertEqual(reconstruct(None), "")
    self.assertEqual(reconstruct({}), "")
    self.assertEqual(
        reconstruct({
            "valid": [0],
            "ignored": ["bad"],
        }),
        "valid",
    )

def test_openalex_fetcher_parses_inverted_abstract(self):
    payload = {
        "results": [{
            "title": "GNSS Paper",
            "authorships": [],
            "publication_year": 2026,
            "doi": "https://doi.org/10.1000/openalex",
            "primary_location": {
                "source": {"display_name": "Journal"},
                "landing_page_url": "https://example.test/paper",
            },
            "abstract_inverted_index": {
                "Urban": [0],
                "GNSS": [1],
                "positioning": [2],
            },
            "cited_by_count": 4,
        }],
    }
    with mock.patch.object(self.module, "get_config_value", return_value=""), \
            mock.patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=FakeResponse(payload),
            ):
        papers = self.module.OpenAlexFetcher().search("GNSS", 1)

    self.assertEqual(papers[0]["abstract"], "Urban GNSS positioning")
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
```

Expected: the two direct helper tests fail with `None` instead of the expected
strings, and the fetcher test fails because the current OpenAlex paper uses an
empty abstract.

- [ ] **Step 4: Add the minimal reconstruction helper**

Add this helper immediately before `OpenAlexFetcher`:

```python
def reconstruct_openalex_abstract(index: object) -> str:
    if not isinstance(index, dict):
        return ""

    positioned_words = []
    for word, positions in index.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int) and not isinstance(position, bool):
                positioned_words.append((position, word))

    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)
```

Replace the OpenAlex paper's current empty abstract assignment with:

```python
"abstract": reconstruct_openalex_abstract(
    work.get("abstract_inverted_index")
),
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
```

Expected: all focused tests pass.

- [ ] **Step 6: Commit the OpenAlex change**

```powershell
git add -- tests/test_sci_search.py skills/sci-search/sci_search.py
git commit -m "feat: parse OpenAlex abstracts"
```

---

### Task 2: Merge Duplicate Metadata and Render Complete Authors

**Files:**
- Modify: `tests/test_sci_search.py`
- Modify: `skills/sci-search/sci_search.py:1027-1117`

**Interfaces:**
- Consumes: paper dictionaries already compared by `papers_match`.
- Produces: `merge_paper_records(primary: Dict, duplicate: Dict) -> Dict`.
- Produces: `source_label(source: str) -> str`.
- Changes: `dedupe_results(results: List[Dict]) -> List[Dict]` returns copied,
  enriched records while retaining first-seen order.
- Changes: `format_markdown(paper: Dict, index: int) -> str` renders every
  author, merged sources, and the abstract provider.

- [ ] **Step 1: Add failing merge tests**

Add these tests to `SciSearchTests`:

```python
def test_dedupe_results_merges_missing_fields_without_mutating_inputs(self):
    wos = {
        "source": "wos",
        "title": "GNSS NLOS Mitigation",
        "authors": ["A. Author"],
        "year": "2026",
        "journal": "",
        "url": "https://example.test/wos",
        "doi": "10.1000/merge",
        "abstract": "",
        "times_cited": 12,
    }
    springer = {
        "source": "springer_meta",
        "title": "GNSS NLOS Mitigation",
        "authors": ["A. Author", "B. Author", "C. Author", "D. Author"],
        "year": "2026",
        "journal": "GPS Solutions",
        "url": "https://example.test/springer",
        "doi": "10.1000/merge",
        "abstract": "A complete abstract supplied by Springer.",
        "times_cited": "",
    }

    merged = self.module.dedupe_results([wos, springer])

    self.assertEqual(len(merged), 1)
    self.assertEqual(merged[0]["source"], "wos")
    self.assertEqual(merged[0]["sources"], ["wos", "springer_meta"])
    self.assertEqual(merged[0]["journal"], "GPS Solutions")
    self.assertEqual(merged[0]["url"], "https://example.test/wos")
    self.assertEqual(merged[0]["times_cited"], 12)
    self.assertEqual(merged[0]["authors"], springer["authors"])
    self.assertEqual(merged[0]["abstract"], springer["abstract"])
    self.assertEqual(merged[0]["abstract_source"], "springer_meta")
    self.assertNotIn("sources", wos)
    self.assertEqual(wos["abstract"], "")
    self.assertEqual(springer["abstract"], "A complete abstract supplied by Springer.")

def test_dedupe_results_keeps_longer_abstract_and_records_its_source(self):
    wos = {
        "source": "wos",
        "title": "Shared Paper",
        "doi": "10.1000/longer",
        "abstract": "Short abstract.",
    }
    springer = {
        "source": "springer_oa",
        "title": "Shared Paper",
        "doi": "10.1000/longer",
        "abstract": "A substantially longer abstract returned by the OA provider.",
    }

    merged = self.module.dedupe_results([wos, springer])

    self.assertEqual(merged[0]["abstract"], springer["abstract"])
    self.assertEqual(merged[0]["abstract_source"], "springer_oa")
```

Update `test_dedupe_results_uses_normalized_doi_across_sources` so it verifies
the enriched record rather than exact equality with the original input:

```python
deduped = self.module.dedupe_results([wos, scopus])

self.assertEqual(len(deduped), 1)
self.assertEqual(deduped[0]["source"], "wos")
self.assertEqual(deduped[0]["sources"], ["wos", "scopus"])
```

- [ ] **Step 2: Add a failing Markdown presentation test**

Add:

```python
def test_format_markdown_renders_all_authors_and_source_provenance(self):
    paper = {
        "source": "wos",
        "sources": ["wos", "springer_meta"],
        "title": "GNSS Paper",
        "authors": ["A", "B", "C", "D"],
        "year": "2026",
        "journal": "",
        "url": "https://example.test/paper",
        "doi": "10.1000/report",
        "abstract": "Abstract text",
        "abstract_source": "springer_meta",
    }

    markdown = self.module.format_markdown(paper, 1)

    self.assertIn("- **Authors:** A, B, C, D", markdown)
    self.assertNotIn("et al.", markdown)
    self.assertIn(
        "**Sources:** Web of Science, Springer Nature",
        markdown,
    )
    self.assertIn(
        "- **Abstract Source:** Springer Nature",
        markdown,
    )
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
```

Expected: merge tests fail because duplicates are still discarded, and the
presentation test fails because authors are truncated and provenance is not
rendered.

- [ ] **Step 4: Add reusable source labels**

Replace the inline source-label conditionals with:

```python
SOURCE_LABELS = {
    "wos": "Web of Science",
    "springer_meta": "Springer Nature",
    "springer_oa": "Springer Nature (OA)",
    "scopus": "Scopus",
    "semantic_scholar": "Semantic Scholar",
    "openalex": "OpenAlex",
}


def source_label(source: str) -> str:
    return SOURCE_LABELS.get(source, source.upper())
```

- [ ] **Step 5: Implement conservative record merging**

Add immediately before `dedupe_results`:

```python
def _has_value(value: object) -> bool:
    return value not in (None, "", [], {})


def _paper_sources(paper: Dict) -> List[str]:
    sources = paper.get("sources")
    if isinstance(sources, list):
        return [source for source in sources if isinstance(source, str) and source]
    source = paper.get("source", "")
    return [source] if isinstance(source, str) and source else []


def merge_paper_records(primary: Dict, duplicate: Dict) -> Dict:
    merged = dict(primary)
    if isinstance(primary.get("authors"), list):
        merged["authors"] = list(primary["authors"])

    sources = _paper_sources(primary)
    for source in _paper_sources(duplicate):
        if source not in sources:
            sources.append(source)
    merged["sources"] = sources

    for field in ("doi", "journal", "year", "url", "times_cited"):
        if not _has_value(merged.get(field)) and _has_value(duplicate.get(field)):
            merged[field] = duplicate[field]

    primary_authors = merged.get("authors")
    duplicate_authors = duplicate.get("authors")
    if not isinstance(primary_authors, list):
        primary_authors = []
    if not isinstance(duplicate_authors, list):
        duplicate_authors = []
    if len(duplicate_authors) > len(primary_authors):
        merged["authors"] = list(duplicate_authors)

    primary_abstract = str(merged.get("abstract") or "").strip()
    duplicate_abstract = str(duplicate.get("abstract") or "").strip()
    if duplicate_abstract and len(duplicate_abstract) > len(primary_abstract):
        merged["abstract"] = duplicate_abstract
        merged["abstract_source"] = (
            duplicate.get("abstract_source") or duplicate.get("source", "")
        )
    elif primary_abstract:
        merged["abstract"] = primary_abstract
        merged["abstract_source"] = (
            merged.get("abstract_source") or merged.get("source", "")
        )

    return merged
```

Change `dedupe_results` to merge into copied records:

```python
def dedupe_results(results: List[Dict]) -> List[Dict]:
    """Deduplicate cross-source results while keeping first-seen order."""
    deduped = []
    for paper in results:
        for index, existing in enumerate(deduped):
            if papers_match(existing, paper):
                deduped[index] = merge_paper_records(existing, paper)
                break
        else:
            copied = dict(paper)
            if isinstance(paper.get("authors"), list):
                copied["authors"] = list(paper["authors"])
            if isinstance(paper.get("sources"), list):
                copied["sources"] = list(paper["sources"])
            deduped.append(copied)
    return deduped
```

- [ ] **Step 6: Render all authors and provenance**

Build provider labels from the merged source list:

```python
sources = _paper_sources(paper)
source_labels = [source_label(source) for source in sources]
source_heading = "Sources" if len(source_labels) > 1 else "Source"
```

Use all authors and the computed source heading:

```python
lines = [
    f"### {index}. {paper['title']}{status_icon}",
    f"- **Authors:** {', '.join(paper['authors'])}",
    (
        f"- **Year:** {paper['year']} | **{source_heading}:** "
        f"{', '.join(source_labels)}"
    ),
]
```

Before the abstract preview, render its provider:

```python
if paper.get("abstract"):
    abstract_source = paper.get("abstract_source") or paper.get("source", "")
    if abstract_source:
        lines.append(
            f"- **Abstract Source:** {source_label(abstract_source)}"
        )
    lines.append(f"- **Abstract:** {paper['abstract'][:300]}...")
```

- [ ] **Step 7: Run focused and full tests**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p test_sci_search.py -v
conda run -n aut-sci-write python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: the focused tests and complete repository test suite pass.

- [ ] **Step 8: Commit the merge and presentation change**

```powershell
git add -- tests/test_sci_search.py skills/sci-search/sci_search.py
git commit -m "fix: enrich duplicate sci-search results"
```

---

### Task 3: Document, Verify, and Generate the Live Report

**Files:**
- Modify: `README.md`
- Modify: `skills/sci-search/SKILL.md`
- Modify: `docs/index.html`
- Create: `docs/reports/2026-07-30-gnss-nlos-search.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: the enriched Markdown output implemented in Tasks 1 and 2.
- Produces: user-facing documentation and one committed live search report.

- [ ] **Step 1: Update user-facing behavior documentation**

Add concise wording to the English and Chinese search sections in `README.md`,
the result-description section in `skills/sci-search/SKILL.md`, and the
matching `docs/index.html` feature copy:

```text
Cross-source duplicates retain the highest-priority record while filling
approved missing metadata, preferring the more complete author list and
abstract. Reports list every author and identify contributing sources and the
abstract provider. OpenAlex abstracts are reconstructed when OpenAlex is
selected explicitly.
```

Use the equivalent Chinese wording in the Chinese README section:

```text
跨源重复论文保留最高优先级记录，同时补充允许合并的缺失元数据，并优先采用更完整的作者列表和摘要。报告展示全部作者，并标明贡献来源及摘要来源。显式选择 OpenAlex 时会重建其倒排摘要。
```

- [ ] **Step 2: Run deterministic verification**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p "test_*.py" -v
conda run --no-capture-output -n aut-sci-write python -m ruff check --select 'F,E9' skills/sci-search/sci_search.py tests/test_sci_search.py
conda run -n aut-sci-write python -m compileall -q skills/sci-search/sci_search.py tests/test_sci_search.py
git diff --check
```

Expected: every command exits zero; record the exact test count in
`progress.md`.

- [ ] **Step 3: Run a bounded live OpenAlex diagnostic**

Run:

```powershell
conda run --no-capture-output -n aut-sci-write python skills/sci-search/sci_search.py "GNSS NLOS" --source openalex --limit 3 --no-cache
```

Expected: the provider request succeeds when available and returned records
with `abstract_inverted_index` render an `Abstract` and `Abstract Source:
OpenAlex` line. Record provider errors exactly as observed without exposing
configuration values.

- [ ] **Step 4: Generate the requested live Markdown report**

Create `docs/reports/` if it does not exist, then run:

```powershell
conda run --no-capture-output -n aut-sci-write python skills/sci-search/sci_search.py "GNSS NLOS" --year-from 2022 --year-to 2026 --sort recent --limit 5 --source all --no-cache --output docs/reports/2026-07-30-gnss-nlos-search.md
```

Expected: the command attempts WoS, Springer Metadata, Springer Open Access,
and Scopus in that order and writes one report without printing a credential.

- [ ] **Step 5: Inspect the generated report**

Run:

```powershell
Get-Item -LiteralPath 'docs\reports\2026-07-30-gnss-nlos-search.md'
rg -n "^# Search Results:|^- \*\*Authors:\*\*|^\- \*\*Abstract:\*\*|^\- \*\*Abstract Source:\*\*|\*\*Sources:\*\*" docs/reports/2026-07-30-gnss-nlos-search.md
$truncatedAuthors = rg -n "et al\." docs/reports/2026-07-30-gnss-nlos-search.md
if ($LASTEXITCODE -eq 1) { 'ALL_AUTHORS_RENDERED_WITHOUT_ET_AL' } else { $truncatedAuthors; exit 1 }
```

Expected: the report exists, contains paper headings and author lines, contains
abstract/provenance lines when providers supplied them, and contains no
formatter-added `et al.`.

- [ ] **Step 6: Append the implementation record**

Append one entry to `progress.md` using the repository format:

```markdown
## 2026-07-30 - Task: Enrich sci-search results and generate a live report

### What was done

- Reconstructed OpenAlex inverted abstracts and enriched duplicate provider
  records without changing first-seen priority.
- Displayed every author and added source and abstract provenance to Markdown
  results.
- Generated the bounded GNSS NLOS report from the configured live APIs.

### Testing

- `conda run -n aut-sci-write python -m unittest discover -s tests -p
  "test_*.py" -v` - 31 tests passed.
- Scoped Ruff, Python compilation, and whitespace checks passed.
- Record the sanitized OpenAlex diagnostic result count and whether abstracts
  rendered.
- Record the four attempted default providers, returned report count, and any
  sanitized provider-specific availability error exactly as observed.

### Notes

- `skills/sci-search/sci_search.py` - summarizes the implemented parser,
  merge, and presentation changes.
- `tests/test_sci_search.py` - summarizes deterministic regression coverage.
- `README.md`, `skills/sci-search/SKILL.md`, and `docs/index.html` - summarize
  the documented behavior.
- `docs/reports/2026-07-30-gnss-nlos-search.md` - identifies the generated live
  report.
- `progress.md` - records implementation and verification evidence.
- Rollback point: commit `8d8d401`; run
  `git switch -c sci-search-before-result-enrichment 8d8d401` to create a
  recovery branch before implementation.
```

Replace the testing instruction lines with the actual observed evidence before
committing; do not leave instructional text in `progress.md`.

- [ ] **Step 7: Run final repository checks**

Run:

```powershell
conda run -n aut-sci-write python -m unittest discover -s tests -p "test_*.py" -v
conda run --no-capture-output -n aut-sci-write python -m ruff check --select 'F,E9' skills/sci-search/sci_search.py tests/test_sci_search.py
conda run -n aut-sci-write python -m compileall -q skills/sci-search/sci_search.py tests/test_sci_search.py
git diff --check
git diff --check 8d8d401..HEAD
git status --short
```

Expected: all tests pass, scoped Ruff and compilation exit zero, the branch
diff has no whitespace errors, and only the intended Task 3 files remain
uncommitted.

- [ ] **Step 8: Commit documentation and the report**

```powershell
git add -- README.md skills/sci-search/SKILL.md docs/index.html docs/reports/2026-07-30-gnss-nlos-search.md progress.md
git commit -m "docs: add enriched sci-search report"
```

- [ ] **Step 9: Verify the committed branch**

Run:

```powershell
git status --short --branch
git log --oneline --decorate -5
git diff --check 8d8d401..HEAD
```

Expected: `dev` is clean, the three implementation commits are present after
`8d8d401`, and the complete implementation diff passes whitespace validation.
