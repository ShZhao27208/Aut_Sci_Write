---
name: sci-polish
description: >
  Two-stage academic paper polishing skill. Stage A reduces AI detection traces
  (targeting GPTZero, Turnitin, Originality.ai). Stage B performs 8-dimension
  quality improvement (grammar, tone, coherence, conciseness, terminology,
  structure, argument clarity, journal compliance). Use whenever the user asks
  to polish, proofread, humanize, reduce AI rate, improve writing quality, or
  prepare a paper for submission.
author: Shuo Zhao
license: MIT
copyright: © 2026 Shuo Zhao. All rights reserved.
triggers:
  - 润色论文
  - polish paper
  - reduce AI detection
  - 降AI率
  - de-AI
  - humanize paper
  - academic polish
  - 论文润色
  - 学术改写
  - improve writing
  - proofread
  - 降低AI率
  - 论文降重
  - paper polishing
  - rewrite academic
---

# Sci-Polish — Academic Paper Polishing & De-AI

Two-stage academic paper polishing: AI trace reduction + 8-dimension quality improvement.

---

## Hard Rules (NEVER violate)

1. **NEVER modify:** LaTeX commands, math environments (`$...$`, `\[...\]`, `equation`, `align`, etc.), `\cite{}`, `\ref{}`, `\label{}`, algorithm blocks, code listings, figure/table environments (only caption text is editable)
2. **NEVER fabricate:** data, citations, experimental results, baselines, metrics, author names
3. **NEVER remove:** author's technical claims without explicit permission
4. **NEVER introduce:** Tier 1 AI words (see `references/word-choice-anti-ai.md`) during Phase B edits
5. **Mark as `[PENDING VERIFICATION]`:** any claim you cannot verify from the text
6. **Preserve meaning:** the exact semantic content of every technical statement must be unchanged
7. **Output format:** revised text + polish report. No preamble or trailing changelog unless user asks
8. **When uncertain about domain terminology:** keep the original, flag for user review

---

## Execution Modes

| Mode | Command | Behavior |
|------|---------|----------|
| `full` (default) | "polish this paper" | Phase A → Phase B (all 8 dimensions) |
| `deai-only` | "just reduce AI rate" / "只降AI率" | Phase A only |
| `polish-only` | "just polish, skip de-AI" / "只润色" | Phase B only (all 8 dimensions) |
| `polish-select` | "fix grammar and coherence" | Phase B, selected dimensions only |

---

## Step 0: Input Processing

1. **Identify input format:**
   - PDF → extract visible text (preserve section structure)
   - LaTeX → extract visible paragraphs (protect all commands)
   - Markdown / plain text → use directly
2. **Identify protection zones:** math environments, citations, labels, algorithm blocks, code blocks, figure/table environments
3. **Ask target journal** (optional): affects Dimension 8 scoring. If not specified, use general academic standards.
4. **Confirm execution mode:** full / deai-only / polish-only / polish-select

---

## Step 1: Phase A — De-AI Editing

Reference files:
- `references/ai-detection-patterns.md` — pattern library for scanning
- `references/de-ai-strategies.md` — rewriting strategies
- `references/word-choice-anti-ai.md` — word replacement table

### 1.1 Scan

Scan text against `ai-detection-patterns.md`. Categorize findings:
- **High priority:** Tier 1 words, template phrases, burstiness deficit (SD < 8), RLHF fingerprints
- **Medium priority:** Tier 2 threshold violations, structural symmetry, transition stacking
- **Low priority:** Tier 3 context-dependent, punctuation fingerprints, minor style uniformity

### 1.2 Rewrite (Priority Order)

Follow the strategy priority from `de-ai-strategies.md`:

```
a. Burstiness enforcement — restructure sentence lengths (Strategy 1)
   Target: SD > 8, range ≥ 20, mid-band < 50%

b. Vocabulary de-AI — replace Tier 1 words, compress template phrases (Strategy 2)
   Consult word-choice-anti-ai.md for replacements

c. Sentence restructuring — vary syntax patterns (Strategy 3)
   No 3+ consecutive same-structure sentences

d. Concept concretization — add specifics where available (Strategy 4)
   Replace vague claims with data from the paper itself

e. Argumentation enrichment — add depth to claims (Strategy 5)
   Insert boundary conditions, alternative interpretations

f. Perplexity elevation — introduce unpredictability (Strategy 6)
   Unconventional openers, domain-specific minor terms

g. Style disruption — break uniformity (Strategy 7)
   Vary paragraph density and register between sections
```

### 1.3 Self-Audit

After rewriting, re-scan output against `ai-detection-patterns.md`:
- Any remaining High-priority patterns? → fix them
- Burstiness check: SD > 8? Range ≥ 20? Mid-band < 50%?
- Protection zones intact? (LaTeX commands, math, citations unchanged)
- Meaning preserved? (no semantic drift from original)

---

## Step 2: Phase B — 8-Dimension Polish

Reference file: `references/polish-dimensions.md`

### 2.1 Score All Dimensions (1-5)

Rate each dimension based on the checkpoints in `polish-dimensions.md`:
1. Grammar & Syntax
2. Academic Tone
3. Coherence & Flow
4. Conciseness
5. Terminology
6. Structure & Formatting
7. Clarity of Argument
8. Journal Compliance

### 2.2 Edit Dimensions Scoring ≤ 3

Edit in this order (foundation → logic → style → format):
```
Dim 1 (Grammar) → Dim 7 (Clarity) → Dim 3 (Coherence) →
Dim 4 (Conciseness) → Dim 2 (Tone) → Dim 5 (Terminology) →
Dim 6 (Structure) → Dim 8 (Journal)
```

### 2.3 Preservation Check

During Phase B editing, verify Phase A improvements are maintained:
- Burstiness NOT reduced (sentence length variety preserved)
- No Tier 1 AI words reintroduced
- No template phrases reintroduced
- Punctuation fingerprints still clean (em dash count, etc.)

### 2.4 Re-Score

Rate edited dimensions again. Record "Before" and "After" scores for the report.

---

## Step 3: Output

### 3.1 Revised Text

Output the complete polished text with all modifications applied.
Format matches the input format (LaTeX → LaTeX, Markdown → Markdown, etc.).

### 3.2 Polish Report

Generate report using `templates/polish-report.md`:

- **Phase A summary:** Number of AI traces detected and fixed, by priority level
- **Phase B scorecard:** 8 dimensions, before/after scores, key changes per dimension
- **Top modifications:** Up to 10 most significant before/after comparisons with reasoning
- **Pending items:** Anything marked `[PENDING VERIFICATION]` or requiring user decision

---

## Section-Specific Guidance

### Abstract
- Phase A focus: Remove "In recent years", overclaiming words, template openings
- Phase B focus: Ensure all 6 elements present (context, gap, approach, insight, results, significance)
- Length: Check against venue limits (typically 150-250 words)

### Introduction
- Phase A focus: Break three-part parallel structures, remove "has attracted growing attention"
- Phase B focus: Contributions must be specific and verifiable, not vague

### Methods
- Phase A focus: Restore active subjects ("We" not passive-only), vary procedural sentence length
- Phase B focus: Every symbol defined before use, equations motivated and interpreted

### Results
- Phase A focus: Replace "clearly demonstrates" with data speaking for itself
- Phase B focus: Every claim backed by table/figure reference, statistical measures included

### Discussion
- Phase A focus: Break balanced-hedging patterns, ensure position is taken
- Phase B focus: Limitations acknowledged specifically, future work concrete

### Conclusion
- Phase A focus: Remove "In conclusion, this paper presents" opener
- Phase B focus: Brief, no methodology restatement, concrete future work

---

## Voice Calibration (Optional)

If the user provides their previously published papers:

1. Extract author writing profile (sentence length distribution, connector preferences, punctuation habits)
2. Use author's actual patterns as the target instead of generic "human-sounding" defaults
3. Note in report: "Voice calibrated against [paper title]"

This replaces generic de-AI rewrites with author-specific style matching.

---

## Usage Examples

**Full polish:**
> "请润色这篇论文" / "Polish this paper for NeurIPS submission"

**De-AI only:**
> "只帮我降AI率" / "Reduce the AI detection score, don't change anything else"

**Selective polish:**
> "只检查语法和术语一致性" / "Just fix grammar and check terminology consistency"

**With voice calibration:**
> "用我之前发的这篇论文的风格来润色" / "Polish matching my writing style from this published paper"

---

## © License

MIT License — © 2026 Shuo Zhao. All rights reserved.

This skill is part of the Aut_Sci_Write suite.
