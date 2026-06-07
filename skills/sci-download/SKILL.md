---
name: sci-download
description: >
  学术论文 PDF 下载。支持 8 个数据源：Elsevier、Springer Nature、IEEE Xplore、
  arXiv、Unpaywall、Semantic Scholar、PubMed Central、知网(CNKI)。
  自动根据 DOI 前缀路由到对应数据源，未知 DOI 自动尝试 Unpaywall → Semantic Scholar。
author: Shuo Zhao
license: MIT
copyright: © 2026 Shuo Zhao. All rights reserved.
triggers:
  - 下载论文
  - 下载文献
  - download paper
  - download PDF
  - DOI
  - 10.1016
  - 10.1038
  - 10.1007
  - 10.1109
  - arXiv download
  - ScienceDirect
  - Elsevier
  - Springer
  - IEEE
  - Unpaywall
  - PubMed Central
  - PMC
  - 知网
  - CNKI
---

# Sci-Download — Unified Paper Download Skill

Academic paper PDF download tool with intelligent DOI routing across 8 sources.

## Trigger Phrases
- "下载这篇论文 10.1038/s41586-023-06600-9"
- "download paper by DOI"
- "从 arXiv 下载 2301.07041"
- "下载知网论文"

## Capabilities

| Source | Type | Auth | Coverage |
|--------|------|------|----------|
| **Elsevier/ScienceDirect** | API | API Key | Elsevier journals |
| **Springer Nature** | API | API Key | Springer/Nature OA |
| **IEEE Xplore** | API | API Key | IEEE/IET |
| **arXiv** | Direct | None | Physics/CS/Math preprints |
| **Unpaywall** | API | Email only | Any DOI → OA version |
| **Semantic Scholar** | API | None | Cross-source OA aggregation |
| **PubMed Central** | Direct | None | Biomedical OA |
| **CNKI (知网)** | FSSO/WebVPN | University account | Chinese journals/theses |

## Auto-Routing

The CLI automatically selects the source based on identifier format:

```
10.1016/... → Elsevier
10.1038/... → Springer Nature
10.1007/... → Springer Nature
10.1109/... → IEEE Xplore
2301.07041  → arXiv
PMC1234567  → PubMed Central
12345678    → PubMed (PMID)
中文关键词   → CNKI
Other DOI   → Unpaywall → Semantic Scholar (waterfall)
```

## Usage

Main script: `./sci_download.py`

```bash
# Auto-route by DOI prefix
python skills/sci-download/sci_download.py "10.1038/s41586-023-06600-9"

# Download arXiv paper (auto-detected)
python skills/sci-download/sci_download.py "2301.07041"

# Force a specific source
python skills/sci-download/sci_download.py "10.1021/acs.nanolett.3c00123" --source unpaywall

# Search papers (requires --source)
python skills/sci-download/sci_download.py --search "perovskite solar cells" --source semantic_scholar --limit 5

# Search arXiv
python skills/sci-download/sci_download.py --search "large language model" --source arxiv --limit 5

# Show config and API key status
python skills/sci-download/sci_download.py --status

# Custom output directory
python skills/sci-download/sci_download.py "2301.07041" --output-dir ./papers
```

## Configuration

API keys are stored in `~/.aut-sci-download/.env` (auto-created on first use).

### Set API Keys

```bash
cd skills/sci-download
python -c "from config import update_config; update_config('elsevier_api_key', 'YOUR_KEY')"
python -c "from config import update_config; update_config('springer_api_key', 'YOUR_KEY')"
python -c "from config import update_config; update_config('ieee_api_key', 'YOUR_KEY')"
python -c "from config import update_config; update_config('unpaywall_email', 'you@email.com')"
```

### Key Sources

| Service | URL | Notes |
|---------|-----|-------|
| Elsevier | https://dev.elsevier.com/ | Free, Article Retrieval API |
| Springer | https://dev.springernature.com/ | Free, OA only |
| IEEE | https://developer.ieee.org/ | Free tier |
| Unpaywall | N/A | Just provide email |

### Free Sources (no key needed)
- arXiv, Semantic Scholar, PubMed Central

### CNKI Setup

```bash
python skills/sci-download/cnki_download.py set-mode fsso
python skills/sci-download/cnki_download.py status
# Login at https://fsso.cnki.net → export cookies → save to ~/.aut-sci-download/fsso_cookies.json
```

## Dependencies

```
requests, pycryptodome, beautifulsoup4
```

---
## © License & Copyright
**Aut_Sci_Write** — Autonomous Scientific Writer

- **Author**: Shuo Zhao
- **License**: MIT License
- **Copyright**: © 2026 Shuo Zhao. All rights reserved.
