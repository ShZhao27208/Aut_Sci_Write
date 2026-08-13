# sci-extract

Scientific paper harvesting, extraction, and analysis toolkit.

Given a DOI, PMID, PMCID, arXiv ID, title, or search query, fetches complete metadata from multiple academic databases, retrieves the full text and figures, and writes an agent-readable markdown capture.

## Quick Start

```bash
# Single paper by DOI
python harvest_paper.py 10.1038/s41586-020-2649-2

# By title (interactive candidate selection)
python harvest_paper.py "array programming with numpy"

# Batch mode
python harvest_paper.py --batch dois.txt

# Check configured data sources
python harvest_paper.py --sources
```

## Output Structure

```
{year}_{author}_{short-title}/
├── raw.md              # Full text + inline figures, agent-readable
├── analysis.md         # Written by the host agent (not by script)
├── metadata.json       # Merged metadata from all databases
├── fulltext.xml        # Publisher XML as received
├── figures/            # Publication-resolution images
├── paper.pdf           # PDF for reference
└── _analysis_prompt.md # Instructions for writing analysis.md
```

## Features

### Multi-Source Metadata Aggregation

Queries Crossref, OpenAlex, Semantic Scholar, PubMed, Europe PMC, arXiv (no key required), plus Scopus, Web of Science, Springer, Elsevier, IEEE (with API keys).

### Full Text Retrieval

Ordered candidate strategy with automatic fallthrough:

1. Publisher OA URL (Unpaywall)
2. PMC OA S3 bucket (`pmc-oa-opendata`)
3. EuropePMC render
4. arXiv PDF (published version outranks preprint)
5. Elsevier Article Retrieval API (for `10.1016/...` DOIs, requires `ELSEVIER_INSTTOKEN`)

Each candidate is tried in order until a valid PDF (`%PDF` magic) is confirmed.

### Figure Extraction

- Publisher-resolution figures from JATS XML `<graphic>` elements
- PDF fallback: crops figure regions using PyMuPDF when publisher images unavailable
- Stale figure cleanup: prior run's orphan files are cleared before re-download
- `--skip-figures` flag for metadata-only harvests

### Extraction Status Badges

Every `raw.md` displays a status badge after the title:

| Badge | Meaning |
|-------|---------|
| 论文全文已提取（包括图片） | Full text + publisher figures |
| 论文全文已提取（图片从 PDF 截出） | Full text + figures cropped from PDF |
| 论文全文已提取（无图片） | Full text retrieved, no figures available |
| 论文全文已提取（图片按要求跳过） | Full text retrieved, figures skipped by `--skip-figures` |
| 论文全文未提取 | Only metadata/abstract captured |

### Degraded Capture Handling

When full text is unavailable, `raw.md` provides:

- Structured "Captured / Missing / Sources attempted / How to obtain" sections
- Honest gap reporting based on what was actually retrieved (not hardcoded)
- Actionable instructions for manual retrieval
- All available metadata (abstract, references, keywords) still included

### Resilient HTTP Layer

- `Retry-After` ceiling (60s): if a server asks for longer, raises immediately instead of burning retries (handles OpenAlex daily credit model)
- XXE and billion-laughs protection on all XML parsing
- Path traversal blocking on figure filenames
- Credential scrubbing in error messages

### Batch Mode

```bash
python harvest_paper.py --batch identifiers.txt --output-dir ./papers
```

- One identifier per line (DOI, PMID, arXiv ID, or title)
- Title mismatch warning when query-to-result overlap drops below 60%
- Stale `analysis.md` detection with CLI warning on re-runs

## CLI Options

```
python harvest_paper.py <query> [options]

Positional:
  query                 DOI, PMID, PMCID, arXiv ID, title, or search query

Options:
  --output-dir DIR      Output directory (default: ./sci_extract_out)
  --pick N              Auto-select Nth candidate in non-interactive mode
  --batch FILE          Process multiple identifiers from a file
  --skip-pdf            Do not download PDF
  --skip-figures        Skip figure extraction
  --verbose             Print progress details
  --sources             Show configured data sources and exit
```

## Configuration

Credentials are read from `~/.aut_sci_write/.env`:

```env
# No key required (works out of the box)
# Crossref, OpenAlex, Semantic Scholar, PubMed, Europe PMC, arXiv

# Optional: widens metadata coverage
SCOPUS_API_KEY=...
WOS_API_KEY=...
SPRINGER_API_KEY=...
IEEE_API_KEY=...

# Elsevier full text (for 10.1016/... DOIs)
ELSEVIER_API_KEY=...
ELSEVIER_INSTTOKEN=...    # Required for non-OA article full text
```

### Elsevier Full Text Access

The Elsevier Article Retrieval API only serves content hosted by Elsevier (DOIs starting with `10.1016/`). Papers from other publishers (Nature, Wiley, ACS, RSC, etc.) indexed in Scopus return 404 regardless of credentials.

To access non-OA Elsevier articles:
1. Set `ELSEVIER_API_KEY` (same key used for Scopus search)
2. Set `ELSEVIER_INSTTOKEN` (institutional token from Elsevier Developer Portal)

## Dependencies

- `requests` — HTTP client
- `PyMuPDF` (fitz) — PDF figure cropping (optional, needed for PDF fallback figures)
- `pdfplumber` — PDF text extraction (optional)
- `numpy` — Mode 2 confidence scoring (optional)

## License

MIT. See [LICENSE](../LICENSE).
