---
name: sci-extract
description: Read an academic paper end to end and extract professional research insights, figures, metadata, and critique. Use this skill whenever the user shares a scientific paper, review paper, survey paper, systematic review, meta-analysis, scoping review, arXiv link, DOI, PDF, or pasted paper text and asks to read, summarize, analyze, extract, digest, review, critique, or explain it. For original research papers, produce a modified Heilmeier analysis. For review literature, produce a field-map extraction covering scope, taxonomy, evidence quality, consensus, controversies, gaps, and future directions. Do NOT use this skill for non-academic articles, blog posts, or news.
author: Shuo Zhao         
contributor: Zhiyao Zhang
license: MIT
copyright: © 2026 Shuo Zhao. © 2026 Zhiyao Zhang. All rights reserved.
triggers:
  - 提取论文
  - 分析论文
  - 论文摘要
  - 核心发现
  - 提取结论
  - 论文要点
  - 分析PDF
  - 提取数据
  - 表征分析
  - extract insights
  - analyze paper
  - summarize paper
  - extract figures
  - core findings
  - Main points of the paper
  - analyze paper
  - Analyze the PDF
  - Extract data
  - Characterization analysis
  - review paper
  - survey paper
  - systematic review
  - meta-analysis
  - literature review
  - scoping review
  - field map
---

# Sci-Extract — Scientific Extraction

Professional extraction of core insights and figures from scientific PDF papers.

> **Note**: This skill includes contributions from two authors. See [Copyright & License](#-copyright--license) section for details.

## Features
- **Core Insights**: Automatically identify research problem, methodology, key results, innovations, applications, and limitations.
- **Review Literature Extraction**: For reviews, surveys, systematic reviews, scoping reviews, and meta-analyses, extract the field scope, taxonomy, evidence base, consensus, disagreements, evidence quality, research gaps, and future directions.
- **Paper Harvesting**: Given a DOI, PMID, PMCID, arXiv ID, title, or search query, pull complete metadata from every configured database, the native publisher XML, the full body text, and the figures, then write an agent-readable `raw.md` instead of leaving you to read a PDF.
- **Figure Detection**: Fetch publication-resolution figures from the publisher, or crop figure regions from PDF pages when the publisher ships none.
- **Metadata Extraction**: Parse title, authors, DOI, journal, and year.

## Steps：

### Step 1: Acquire the paper

Always read the paper fresh. Never rely on memory of the paper, even if the title looks familiar.

| Input type                                  | Action                                                       |
| ------------------------------------------- | ------------------------------------------------------------ |
| DOI, PMID, PMCID, arXiv ID, title, or query | Run the harvester (Mode 3 below). It writes `raw.md` with the full text and figures embedded, which you then read instead of a PDF. |
| PDF in `/mnt/user-data/uploads/`            | Read it via the appropriate tool (see the `pdf-reading` skill if available). |
| arXiv link                                  | Extract the arXiv ID and run the harvester. Fall back to `web_fetch` on the abstract page if the harvester returns no full text. |
| Pasted text in the chat                     | Use directly.                                                |
| Just a title with no link                   | Run the harvester with the title; it lists candidates and confirms the match before fetching. Do not guess the paper. |

If the paper is long, first classify the paper type, then prioritize the sections relevant to that type. For original research, prioritize abstract, introduction, method/theory, experiments, conclusion. For review literature, prioritize abstract, introduction, search/selection methods, taxonomy/classification sections, major thematic sections, summary tables, limitations, and future perspectives.

### Step 2: Classify the paper type

Before choosing the extraction template, classify the paper as one of:

- Original research article
- Narrative review / survey
- Systematic review
- Meta-analysis
- Scoping review
- Perspective / tutorial / methods overview

Use the title, abstract, introduction, and section headings. Signals for review literature include "review", "survey", "systematic review", "meta-analysis", "scoping review", "bibliometric", "taxonomy", "current status", "recent progress", "challenges", "future perspectives", and broad comparison tables.

If the paper is a review, survey, systematic review, meta-analysis, scoping review, perspective, or tutorial overview, do **not** force it into the original-research Heilmeier template. Use the Review Literature Extraction Mode below. Original research asks "what did this paper do and prove"; review literature asks "how does this paper map the field and judge the evidence".

### Step 3A: Original Research Mode - Answer the modified Heilmeier questions

Answer each of the seven questions below as a labeled subsection, in order. For each question, the rules differ on (a) whether your own evaluation is allowed and (b) whether external citations are allowed. Read the rules carefully before writing each subsection.

#### Question 1. What are you trying to do?

Open with a one-sentence statement of the paper's contribution written for a smart non-specialist, with absolutely no jargon. Ban acronyms and any technical term a first-year undergrad would not know. If a term of art is unavoidable, define it parenthetically in plain words. Then add one or two sentences expanding the objective in slightly more technical language.

Opinions allowed: no. Stay faithful to the paper.
External citations allowed: no.

#### Question 2. What is the problem, how is it done today, and what are the limits of current practice?

Describe the real-world or scientific problem the paper addresses, then give a brief overview of how the field handles it at the time of the paper, and what the limitations are. This is meant to be a self-contained landscape paragraph, not a literature review. Cover the main competing approaches in plain prose.

Opinions allowed: a small amount, only if it sharpens the framing of the limits.
External citations allowed: no. Do not search for or cite outside sources here. Just give an overview from the paper and your general knowledge of the field.

#### Question 3. What is new in the approach, including core idea, math, and method, and why does the paper claim it will succeed?

This is the technical heart of the response and absorbs what would otherwise be a "method" summary. Cover, in this order:

1. The central technical move that distinguishes the paper from prior work.
2. The key mathematical objects and formulation. Include the main equation or two, define every symbol you introduce, use display math with `\left` and `\right` for brackets, keep inline math on one line, and prefer standard LaTeX notation.
3. How the proposed method actually solves the problem mechanically.
4. The paper's own claim about why the approach will succeed.

Opinions allowed: NO. This subsection is strictly about what the paper says and proposes. Save your evaluation for questions 4, 5, and 6.
External citations allowed: no.

#### Question 4. Who cares? If successful, what difference does it make?

Discuss the impact: which communities benefit, what becomes possible, and whether this paper has actually shifted the field since publication.

Opinions allowed: yes. This is one of the questions where your judgment matters most.
External citations allowed: yes, and encouraged when assessing post-publication impact (adoption by other groups, follow-up papers, deployment). Every external citation must come from a `web_search` or `web_fetch` you actually ran in this turn.

#### Question 5. What are the risks?

Cover both the risks the paper itself acknowledges and the ones you see independently. Be concrete: contamination, reward hacking, failure modes, narrow benchmarks, scaling, reproducibility.

Opinions allowed: yes.
External citations allowed: yes, when an outside source materially supports a risk claim.

#### Question 6. How much will it cost?

Interpret as compute, data, engineering effort, or deployment cost, depending on the paper. State which interpretation you are using. Pull whatever numbers the paper provides (token counts, batch sizes, GPU hours, data volumes) and translate into a rough sense of "what would it take to reproduce this".

Opinions allowed: yes, especially for the "what would it take to reproduce" framing.
External citations allowed: yes. Be careful not to conflate this paper's costs with related work by the same authors. If you cite a cost figure, state exactly which paper or model that figure refers to.

#### Question 7. What are the experiments and results?

Cover the experimental setup (benchmarks, datasets, baselines, metrics, ablations) and the headline results. This subsection answers "what are the criteria for success and did the paper meet them". Note any conspicuous gap between claims and evidence.

Opinions allowed: small amount, only for noting gaps between claims and evidence.
External citations allowed: no.

### Step 3B: Review Literature Extraction Mode

Use this mode for review papers, survey papers, systematic reviews, meta-analyses, scoping reviews, perspective reviews, and tutorial overviews. Do not ask for a single proposed method, single experiment, or reproduction cost unless the review itself is about benchmarking or a method protocol. The goal is to reconstruct the paper's map of the field and assess how reliable that map is.

Return the following labeled subsections, in order:

#### 1. Review scope

State what field, problem, population, method family, material class, data type, or application area the paper reviews. Include explicit inclusion and exclusion boundaries when the paper gives them. If the scope is vague, say so.

#### 2. Why this review exists now

Explain the motivation: field fragmentation, rapid growth, conflicting evidence, unclear taxonomy, translation gap, reproducibility problem, new technology, or practical need. Keep this faithful to the paper before adding your own judgment.

#### 3. Taxonomy or organizing framework

Extract the categories the authors use to organize the field. Preserve the author's hierarchy and terminology. If there are multiple taxonomies, separate them. For each category, give a one-sentence meaning and the main representative approaches, study types, models, materials, datasets, diseases, interventions, or applications.

#### 4. Literature selection and evidence base

For systematic reviews, scoping reviews, and meta-analyses, extract databases searched, search period, search terms if available, inclusion criteria, exclusion criteria, screening process, final included study count, and any quality-assessment tool. For narrative reviews and surveys, state whether the search and selection method is unspecified or informal.

#### 5. Field landscape and main themes

Summarize the major research directions covered by the review. Distinguish mature areas from emerging areas. Mention important datasets, benchmark tasks, experimental platforms, clinical cohorts, model families, materials, or instruments when they are central to the review.

#### 6. Consensus findings

Extract what the reviewed literature broadly agrees on. Separate strong consensus from tentative patterns. If the review does not clearly identify consensus, say so instead of inventing one.

#### 7. Disagreements, controversies, and heterogeneity

Extract where studies conflict, where mechanisms or interpretations differ, and what explanations the review gives for inconsistent findings. For meta-analyses, include heterogeneity statistics and subgroup/sensitivity findings if reported.

#### 8. Evidence quality and bias

Assess the reliability of the reviewed evidence using what the paper reports: study design, sample size, data quality, benchmark leakage, confounding, publication bias, reproducibility, missing controls, annotation quality, evaluation metrics, or risk-of-bias tools. Mark your own assessment with a first-person phrase such as "My analysis is that," so paper content and your critique remain separate.

#### 9. Gaps and future directions

Extract the open questions, missing datasets, missing experiments, technical barriers, translation barriers, standardization needs, clinical/industrial/policy needs, and concrete future directions identified by the authors. Add your own prioritized gap assessment only with a first-person marker.

#### 10. Important figures and tables

Identify taxonomy figures, workflow diagrams, evidence maps, PRISMA flow diagrams, summary tables, comparison tables, benchmark tables, and meta-analysis forest/funnel plots. For each important figure or table, explain what role it plays in understanding the review. If figure extraction is requested, crop or save the relevant figure/table regions when tooling is available.

#### 11. Bottom-line takeaways

End with three to five concise takeaways. Each takeaway should describe something a researcher can use: a field structure, a reliable conclusion, an unresolved controversy, a weak evidence area, or a concrete research opportunity.

## Attribution rules (apply across all questions)

The user must always be able to tell paper content apart from your own analysis. In any subsection where opinions are allowed, prefix every personal judgment with one of: **"In my opinion,"**, **"My analysis is that,"**, **"My read is,"** or an equivalent first-person marker. Never blur the line. In the subsections where opinions are not allowed (questions 1 and 3), do not use these markers at all.

## Citation rules (apply across all questions)

Every external citation in your response must come from a `web_search` or `web_fetch` you actually ran in this turn. No citations from memory. There is exactly one carve-out: if the paper itself cites a prior work and you are *exactly* repeating what the paper says about that cited work, you may mention it without a web search. The moment you add anything beyond what the paper literally says, search and cite the search result.

When you do search, cite the source inline so the user can follow up.

## Length and pacing

Keep the response tight. The user has explicitly asked for fast, non-redundant output. Do not repeat the same point under multiple questions. Aim for the shortest response that fully answers all seven questions; if a question genuinely has little to say for a particular paper, keep its subsection to two or three sentences.

## Format and formatting compliance

Return everything as a single inline markdown response. Use one top-level header naming the paper, then a `##` header per question. Math compliant with: `\left` / `\right` for display brackets, inline math on one line, every symbol defined, standard LaTeX. Do not use em-dashes or en-dashes anywhere; use commas, semicolons, parentheses, or new sentences instead.

## What not to do

- Do not produce a separate "Summary" section before the catechism. The catechism is the summary.
- Do not put personal evaluation in questions 1 or 3.
- Do not invent numbers, baselines, or experimental results that are not in the paper.
- Do not insert citations from memory.
- Do not conflate this paper with related work by the same authors when stating costs or results.
- Do not analyze a paper you have not actually read this turn.

## Usage

This skill has three independent modes:

Mode 1 now starts by classifying the paper type. Original research papers use the modified Heilmeier framework. Review literature uses the Review Literature Extraction Mode, which is designed for review papers, surveys, systematic reviews, scoping reviews, and meta-analyses.

Mode 2 now supports `--paper-type auto|research|review`. For original research, it extracts research problem, methodology, key results, innovation, application, and limitations. For review literature, it extracts review scope, taxonomy, literature selection method, major themes, consensus findings, controversies, evidence quality, research gaps, future directions, and key tables/figures.

**Mode 1 — Heilmeier Analysis (AI-driven, no script needed)**
Simply share a paper and ask for analysis. The AI follows the 7-question framework above directly. No local script is required.

**Mode 2 — Core Insights Extractor (Python CLI)**
A standalone script that extracts 6 structured fields (research problem, methodology, key results, innovation, application, limitations) with confidence scores. Run from the `skills/sci-extract/` directory:

```bash
# Single PDF — outputs JSON by default
python extract_core_insights.py paper.pdf

# Choose output format
python extract_core_insights.py paper.pdf --format markdown
python extract_core_insights.py paper.pdf --format csv

# Force or auto-detect paper type
python extract_core_insights.py review.pdf --paper-type review
python extract_core_insights.py paper.pdf --paper-type auto

# Batch process a folder (4 parallel workers)
python extract_core_insights.py papers/ --batch

# Save to a specific file
python extract_core_insights.py paper.pdf --output results.json
```

**Mode 3 — Paper Harvester (Python CLI + your own analysis)**

Fetches a paper from the academic databases and lays it out on disk as markdown, so you read text and images rather than a PDF. Run from the `skills/sci-extract/` directory:

```bash
# By identifier: DOI, PMID, PMCID, or arXiv ID
python harvest_paper.py 10.1038/s41586-020-2649-2
python harvest_paper.py PMC7759461
python harvest_paper.py 2006.10256

# By title or search query: lists candidates and asks before fetching
python harvest_paper.py "array programming with numpy"
python harvest_paper.py "array programming with numpy" --pick 1   # non-interactive

# Where to write, and what to skip
python harvest_paper.py 10.1038/s41586-020-2649-2 --output-dir ./papers
python harvest_paper.py 10.1038/s41586-020-2649-2 --skip-pdf --skip-figures

# Several papers, one identifier per line
python harvest_paper.py --batch dois.txt

# Which databases are configured
python harvest_paper.py --sources
```

Each paper lands in its own directory under `./sci_extract_out/` (override with `--output-dir`):

```
2020_harris_array-programming-numpy/
├── raw.md                # complete capture in English, figures embedded inline
├── analysis.md           # YOU write this; see below
├── metadata.json         # merged record from every database, plus an audit trail
├── fulltext.xml          # publisher XML exactly as received
├── figures/              # publication-resolution images
├── paper.pdf             # kept for reference
└── _analysis_prompt.md   # instructions for writing analysis.md
```

**After the harvester finishes, you write `analysis.md`.** The script deliberately does not call any language model: you are the model, so read `_analysis_prompt.md`, read `raw.md` in full, apply the Mode 1 template that matches the paper type, and write `analysis.md` into the same directory in Chinese. No LLM API key is involved, and none should be requested from the user.

Two markdown files per paper is the point of this mode: `raw.md` is the faithful source you read, `analysis.md` is your judgment of it, and keeping them separate means the analysis never quietly rewrites the evidence.

Coverage is honest about its limits. Full text and figures require the paper to be open access; for paywalled papers the harvester still writes complete metadata, the abstract, and the PDF when one is reachable, and `raw.md` states plainly which parts were unavailable. Check the Provenance section at the bottom of `raw.md` before treating a gap as an absence in the paper itself.

The three modes are independent: Mode 1 produces a narrative analysis from a paper you already have; Mode 2 produces structured data fields from a local PDF; Mode 3 fetches the paper and prepares it for Mode 1. A common chain is Mode 3 then Mode 1.

## Configuration

Mode 2 requires `PyMuPDF`, `pdfplumber`, and `numpy`.

Mode 3 requires `requests`, and uses `PyMuPDF` when it needs to crop figures out of a PDF. Database credentials are read from the suite-wide `.env` at `~/.aut_sci_write/.env`; run `python harvest_paper.py --sources` to see what is configured. Crossref, OpenAlex, Semantic Scholar, PubMed, Europe PMC, and arXiv need no key, so the harvester is useful with an empty `.env`. Adding keys for Web of Science, Scopus, Springer, Elsevier, or IEEE widens metadata coverage and, for entitled Elsevier and Springer keys, full text.





---

## © License & Copyright

### Authors & Contributions

| Author           | Contribution                                                 | Copyright           |
| ---------------- | ------------------------------------------------------------ | ------------------- |
| **Shuo Zhao**    | Core extraction engine (features, figure detection, metadata parsing) | © 2026 Shuo Zhao    |
| **Zhiyao Zhang** | Heilmeier Analysis module (7-question catechism framework)   | © 2026 Zhiyao Zhang |

### License

**MIT License** — see [LICENSE](../LICENSE) file in the project root.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Copyright Notice

```
Copyright (c) 2026 Shuo Zhao. All rights reserved.
Copyright (c) 2026 Zhiyao Zhang. All rights reserved.

This work includes contributions from both authors under MIT license.
- Core extraction module: Copyright (c) 2026 Shuo Zhao
- Heilmeier analysis module: Copyright (c) 2026 Zhiyao Zhang
```

### Original Work Declaration

This is an original collaborative work created by the authors. No reproduction, redistribution, or commercial use without explicit permission from both authors.

**Permission is hereby granted**, free of charge, to any person obtaining a copy of this software... (**See the LICENSE file in the root directory for the full MIT terms.**)

---

*This skill is part of the Aut_Sci_Write suite. For full license terms, see the [LICENSE](../LICENSE) file in the project root.*
---
