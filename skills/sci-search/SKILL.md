---
name: sci-search
description: Academic paper search and metrics analysis. Searches enabled defaults in priority order (Web of Science, Springer Metadata, Springer Open Access, Scopus) with journal impact factor data. arXiv, PubMed, Semantic Scholar, and OpenAlex require explicit source selection. Triggers on requests to search for papers or find literature.
author: Shuo Zhao         
license: MIT
copyright: © 2026 Shuo Zhao. All rights reserved. 
triggers:
  - 搜索文献
  - 查文献
  - 找论文
  - 最新论文
  - 相关文献
  - 文献检索
  - 影响因子
  - 期刊分区
  - Web of Science
  - WoS
  - SCI检索
  - arXiv
  - PubMed
  - Springer
  - Springer Nature
  - Scopus
  - Elsevier
  - Semantic Scholar
  - OpenAlex
  - find papers
  - search papers
  - literature search
  - impact factor
---

# Sci-Search — Sci Search Skill

Academic paper search and metrics analysis tool for scientific research workflows.

## Trigger Phrases
- "搜索关于 [主题] 的高影响因子论文"
- "在 Web of Science 上查找 [主题] 的最新文献"
- "search academic papers on [topic]"
- "find recent papers about [topic] on Web of Science"
- "get impact factor for [topic] papers"

## Capabilities
- **Default Search Order**: Searches enabled **Web of Science**, **Springer Metadata**, **Springer Open Access**, and **Scopus** sources in that priority order.
- **Explicit-Only Sources**: arXiv, PubMed, Semantic Scholar, and OpenAlex are searched only when selected explicitly with `--source`.
- **Web of Science Integration**: Returns SCI-indexed papers with times-cited counts — the gold standard for academic quality filtering.
- **Springer Nature Integration**: Returns articles from Springer, Nature, Palgrave Macmillan, and other Springer Nature imprints with DOI links.
- **Scopus Integration**: Elsevier's largest abstract and citation database; returns cited-by counts.
- **Semantic Scholar Integration**: AI-powered academic graph with citation counts; no API key required.
- **OpenAlex Integration**: Free and open catalog of 200M+ scholarly works; no API key required.
- **Journal Metrics**: Automatically supplements results with JCR partitions and Impact Factors (IF).
- **Ranking & Highlighting**: Highlights top-tier journals (Nature, Science, Advanced Materials, etc.).
- **Markdown Export**: Generates formatted markdown reports of search results.
- **Source Selection**: `--source all` searches enabled default sources. Use `--source arxiv`, `--source pubmed`, `--source wos`, `--source springer`, `--source springer_meta`, `--source springer_oa`, `--source scopus`, `--source semantic_scholar`, or `--source openalex` to select a source explicitly.
- **Search Controls**: `--year-from` and `--year-to` set inclusive year bounds, `--sort recent` is the default, and `--limit` applies per source.

## Configuration

### Web of Science API (Recommended for SCI literature)
Add `WOS_API_KEY` to the unified `~/.aut_sci_write/.env` file to enable Web of Science search:
```bash
WOS_API_KEY=your_wos_api_key
```
Apply for a free API key at: https://developer.clarivate.com/apis/wos-starter

The **WoS Starter API** is free to apply for and provides access to the Web of Science Core Collection — the most authoritative index of SCI/SSCI journals.

### Springer Nature API (two endpoints)
The Springer Nature API provides two separate endpoints:

**1. Metadata API** (`/meta/v2/json`) — metadata for all Springer Nature content (journals + books).
Add `SPRINGER_API_KEY` to `~/.aut_sci_write/.env`:
```bash
SPRINGER_API_KEY=your_springer_api_key
```

**2. Open Access API** (`/openaccess/json`) — full-text OA content from BMC, SpringerOpen, Nature OA articles.
Add `SPRINGER_OA_API_KEY` to `~/.aut_sci_write/.env` (falls back to `SPRINGER_API_KEY` if not set):
```bash
SPRINGER_OA_API_KEY=your_oa_api_key
```

Apply for free API keys at: https://dev.springernature.com/

Use `--source springer` for both, `--source springer_meta` for metadata only, or `--source springer_oa` for Open Access only.

### Scopus API (Elsevier — largest abstract database)
Add `SCOPUS_API_KEY` to `~/.aut_sci_write/.env` to enable Scopus search:
```bash
SCOPUS_API_KEY=your_scopus_api_key
```
Apply for a free API key at: https://dev.elsevier.com/

The **Scopus Search API** covers 90M+ records across science, technology, medicine, social sciences, and arts & humanities. Requires institutional affiliation for full access.

### Semantic Scholar (free, no key required)
Works out of the box. For higher rate limits, optionally add:
```bash
SEMANTIC_SCHOLAR_API_KEY=your_key
```
Request a key at: https://www.semanticscholar.org/product/api#api-key

### OpenAlex (free, no key required)
Works out of the box. For polite pool (faster rate limits), optionally add:
```bash
OPENALEX_EMAIL=your_email@example.com
```

### Other optional `.env` values (all in `~/.aut_sci_write/.env`)
- `SPRINGER_API_KEY` - Springer Nature Metadata API key (see above)
- `SPRINGER_OA_API_KEY` - Springer Nature Open Access API key (falls back to SPRINGER_API_KEY)
- `SCOPUS_API_KEY` - Elsevier Scopus API key (see above)
- `SEMANTIC_SCHOLAR_API_KEY` - optional, for higher rate limits
- `OPENALEX_EMAIL` - optional, for polite pool access
- `NCBI_API_KEY` - optional PubMed/NCBI E-utilities API key for higher rate limits
- `NCBI_EMAIL` - optional contact email sent to NCBI E-utilities
- `NCBI_TOOL` - optional NCBI tool name; defaults to `sci-search`
- `ZOTERO_USER_ID` — for Zotero integration
- `ZOTERO_API_KEY` — for Zotero integration

## Usage

Main script: `./sci_search.py`

```bash
# Search enabled default sources (WoS + Springer Metadata + Springer Open Access + Scopus)
python skills/sci-search/sci_search.py "perovskite solar cells" --limit 5

# Search a bounded recent year range; --limit applies per source
python skills/sci-search/sci_search.py "GNSS NLOS" --year-from 2022 --year-to 2026 --sort recent --limit 5

# Search Web of Science only
python skills/sci-search/sci_search.py "solid state electrolyte" --source wos --limit 10

# Search PubMed only with NCBI E-utilities
python skills/sci-search/sci_search.py "cancer immunotherapy" --source pubmed --limit 10

# Search Springer Nature only
python skills/sci-search/sci_search.py "machine learning materials science" --source springer --limit 10

# Search Scopus only
python skills/sci-search/sci_search.py "lithium ion battery" --source scopus --limit 10

# Search Semantic Scholar only (no key needed)
python skills/sci-search/sci_search.py "transformer attention mechanism" --source semantic_scholar --limit 10

# Search OpenAlex only (no key needed)
python skills/sci-search/sci_search.py "CRISPR gene editing" --source openalex --limit 10

# Export results to markdown
python skills/sci-search/sci_search.py "graphene battery" --output results.md
```



---
## © License & Copyright
**Aut_Sci_Write** — Autonomous Scientific Writer

- **Author**: Shuo Zhao
- **License**: MIT License
- **Copyright**: © 2026 Shuo Zhao. All rights reserved.
- **Original Work**: This is an original work created by the author. No reproduction, redistribution, or commercial use without explicit permission.
  **Permission is hereby granted**, free of charge, to any person obtaining a copy of this software... (**See the LICENSE file in the root directory for the full MIT terms.**)

---
*This skill is part of the Aut_Sci_Write suite. For full license terms, see the [LICENSE](../LICENSE) file in the project root.*
---
