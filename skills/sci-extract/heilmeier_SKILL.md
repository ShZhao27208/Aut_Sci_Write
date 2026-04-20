---
name: paper-reader-heilmeier
description: Read a research paper end to end and produce a single Heilmeier-style analysis that doubles as both summary and critique. Use this skill whenever the user shares a research paper (PDF upload, arXiv link, arXiv ID, DOI, or pasted paper text) and asks anything that resembles "read this", "summarize this paper", "what does this paper do", "analyze this paper", "give me a Heilmeier analysis", "review this paper", or simply drops a paper into the chat with little explanation. Trigger this skill even when the user does not explicitly say "Heilmeier" — any request to digest, summarize, review, or critically assess an academic paper should activate it. Do NOT use this skill for non-academic articles, blog posts, or news.
---

<!-- Copyright (c) 2026 Zhiyao Zhang -->
<!-- SPDX-License-Identifier: MIT -->

# Paper Reader + Heilmeier's Catechism

This skill produces a single inline markdown response: a modified Heilmeier's Catechism analysis that absorbs the structured summary into the catechism itself. There is no separate summary section.

## Step 1: Acquire the paper

Always read the paper fresh. Never rely on memory of the paper, even if the title looks familiar.

| Input type                       | Action                                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| PDF in `/mnt/user-data/uploads/` | Read it via the appropriate tool (see the `pdf-reading` skill if available).            |
| arXiv link, arXiv ID, or DOI     | Use `web_fetch` on the arXiv abstract page, then on the PDF/HTML version for full text. |
| Pasted text in the chat          | Use directly.                                                                           |
| Just a title with no link        | Ask the user for a link or upload before proceeding. Do not guess the paper.            |

If the paper is long, prioritize: abstract, introduction, method/theory, experiments, conclusion. Skim related work only if useful for question 2.

## Step 2: Answer the modified Heilmeier questions

Answer each of the seven questions below as a labeled subsection, in order. For each question, the rules differ on (a) whether your own evaluation is allowed and (b) whether external citations are allowed. Read the rules carefully before writing each subsection.

### Question 1. What are you trying to do?

Open with a one-sentence statement of the paper's contribution written for a smart non-specialist, with absolutely no jargon. Ban acronyms and any technical term a first-year undergrad would not know. If a term of art is unavoidable, define it parenthetically in plain words. Then add one or two sentences expanding the objective in slightly more technical language.

Opinions allowed: no. Stay faithful to the paper.
External citations allowed: no.

### Question 2. What is the problem, how is it done today, and what are the limits of current practice?

Describe the real-world or scientific problem the paper addresses, then give a brief overview of how the field handles it at the time of the paper, and what the limitations are. This is meant to be a self-contained landscape paragraph, not a literature review. Cover the main competing approaches in plain prose.

Opinions allowed: a small amount, only if it sharpens the framing of the limits.
External citations allowed: no. Do not search for or cite outside sources here. Just give an overview from the paper and your general knowledge of the field.

### Question 3. What is new in the approach, including core idea, math, and method, and why does the paper claim it will succeed?

This is the technical heart of the response and absorbs what would otherwise be a "method" summary. Cover, in this order:

1. The central technical move that distinguishes the paper from prior work.
2. The key mathematical objects and formulation. Include the main equation or two, define every symbol you introduce, use display math with `\left` and `\right` for brackets, keep inline math on one line, and prefer standard LaTeX notation.
3. How the proposed method actually solves the problem mechanically.
4. The paper's own claim about why the approach will succeed.

Opinions allowed: NO. This subsection is strictly about what the paper says and proposes. Save your evaluation for questions 4, 5, and 6.
External citations allowed: no.

### Question 4. Who cares? If successful, what difference does it make?

Discuss the impact: which communities benefit, what becomes possible, and whether this paper has actually shifted the field since publication.

Opinions allowed: yes. This is one of the questions where your judgment matters most.
External citations allowed: yes, and encouraged when assessing post-publication impact (adoption by other groups, follow-up papers, deployment). Every external citation must come from a `web_search` or `web_fetch` you actually ran in this turn.

### Question 5. What are the risks?

Cover both the risks the paper itself acknowledges and the ones you see independently. Be concrete: contamination, reward hacking, failure modes, narrow benchmarks, scaling, reproducibility.

Opinions allowed: yes.
External citations allowed: yes, when an outside source materially supports a risk claim.

### Question 6. How much will it cost?

Interpret as compute, data, engineering effort, or deployment cost, depending on the paper. State which interpretation you are using. Pull whatever numbers the paper provides (token counts, batch sizes, GPU hours, data volumes) and translate into a rough sense of "what would it take to reproduce this".

Opinions allowed: yes, especially for the "what would it take to reproduce" framing.
External citations allowed: yes. Be careful not to conflate this paper's costs with related work by the same authors. If you cite a cost figure, state exactly which paper or model that figure refers to.

### Question 7. What are the experiments and results?

Cover the experimental setup (benchmarks, datasets, baselines, metrics, ablations) and the headline results. This subsection answers "what are the criteria for success and did the paper meet them". Note any conspicuous gap between claims and evidence.

Opinions allowed: small amount, only for noting gaps between claims and evidence.
External citations allowed: no.

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


---
 
## Copyright
 
Copyright (c) 2026 Zhiyao Zhang. All rights reserved. 