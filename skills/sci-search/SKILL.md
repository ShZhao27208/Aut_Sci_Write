---
name: sci-search
description: Academic paper search and metrics analysis. Searches arXiv, PubMed, and Web of Science simultaneously with journal impact factor data. Triggers on requests to search for papers or find literature.
author: Shuo Zhao         
license: MIT
copyright: © 2026 Shuo Zhao. All rights reserved. 
original: This is an original work created by the author. No reproduction or redistribution without permission.  
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
- **Triple-Source Search**: Simultaneously searches arXiv, PubMed, and **Web of Science** (when API key is configured).
- **Web of Science Integration**: Returns SCI-indexed papers with times-cited counts — the gold standard for academic quality filtering.
- **Journal Metrics**: Automatically supplements results with JCR partitions and Impact Factors (IF).
- **Ranking & Highlighting**: Highlights top-tier journals (Nature, Science, Advanced Materials, etc.).
- **Markdown Export**: Generates formatted markdown reports of search results.
- **Source Selection**: Use `--source wos` to search Web of Science only, or `--source all` for all sources.

## Configuration

### Web of Science API (Recommended for SCI literature)
Set the `WOS_API_KEY` environment variable to enable Web of Science search:
```bash
export WOS_API_KEY=your_wos_api_key
```
Apply for a free API key at: https://developer.clarivate.com/apis/wos-starter

The **WoS Starter API** is free to apply for and provides access to the Web of Science Core Collection — the most authoritative index of SCI/SSCI journals.

### Other optional variables
- `ZOTERO_USER_ID` — for Zotero integration
- `ZOTERO_API_KEY` — for Zotero integration

## Usage

Main script: `./sci_search.py`

```bash
# Search all sources (arXiv + PubMed + WoS if key set)
python skills/sci-search/sci_search.py "perovskite solar cells" --limit 5

# Search Web of Science only
python skills/sci-search/sci_search.py "solid state electrolyte" --source wos --limit 10

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

