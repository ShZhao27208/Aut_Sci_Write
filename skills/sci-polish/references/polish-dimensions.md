# Polish Dimensions — 8-Dimension Academic Quality Assessment

Scoring criteria and operation guide for the 8-dimension polish system (Phase B).
Each dimension is scored 1-5, with specific checkpoints and repair strategies.

Sources: academic-writing-skills (section-guide, tone-thresholds),
Aut_Sci_Write (section-guide.md, word-choice.md), humanize (hedge surgery).

---

## Scoring Scale

| Score | Meaning | Action |
|-------|---------|--------|
| 5 | Journal-ready, no modification needed | Skip |
| 4 | Minor improvements possible | Light touch only |
| 3 | Moderate issues requiring attention | Active editing |
| 2 | Clear problems present | Significant revision |
| 1 | Major rewrite needed | Extensive rework |

**Rule:** Only actively edit dimensions scoring ≤ 3. Score 4-5 dimensions receive no changes
unless a fix is zero-risk (e.g., obvious typo).

---

## Dimension 1: Grammar & Syntax

### Checkpoints

- [ ] Tense consistency (per section rules below)
- [ ] Subject-verb agreement (especially with complex subjects)
- [ ] Articles (the/a/an vs zero article in academic usage)
- [ ] Preposition collocations (domain-specific)
- [ ] Parallel structure in enumerations
- [ ] Dangling/misplaced modifiers
- [ ] that/which (restrictive vs non-restrictive clauses)
- [ ] Singular/plural consistency for technical nouns

### Academic Tense Rules

| Section | Default Tense | Exceptions |
|---------|--------------|------------|
| Abstract | Past (reporting done work) + Present (conclusions) | |
| Introduction | Present (general knowledge) | Past (describing others' specific experiments) |
| Methods | Past | Present (describing equipment properties) |
| Results | Past | Present ("Table 2 shows...") |
| Discussion | Mixed | Based on temporal nature of assertion |
| Conclusion | Past (summary) + Present (implications) | |

### Common Grammar Fixes

| Error Pattern | Fix |
|---------------|-----|
| "The data shows" | "The data show" (data is plural) |
| "allows to do X" | "allows us to do X" / "enables X" |
| "is comprised of" | "comprises" / "consists of" |
| "less parameters" | "fewer parameters" (countable) |
| "this work proposes" (Methods) | "this work proposed" (past tense in Methods) |

---

## Dimension 2: Academic Tone

### Checkpoints

- [ ] No contractions (don't → do not, it's → it is)
- [ ] No phrasal verbs in formal context (find out → determine, come up with → propose)
- [ ] No excessive subjectivity ("We believe" → "The results suggest")
- [ ] No emotional language ("exciting results" → "noteworthy results")
- [ ] Appropriate hedging level (neither over-hedged nor overclaiming)
- [ ] No promotional language ("groundbreaking", "revolutionary", "game-changing")
- [ ] No colloquialisms ("a lot of", "kind of", "basically")

### Hedging Calibration

| Evidence Strength | Appropriate Expression |
|-------------------|----------------------|
| Your own experimental results | "Our method achieves..." / "We observed..." |
| Strong but non-conclusive evidence | "indicates", "demonstrates", "confirms" |
| Correlational evidence | "suggests", "is associated with", "appears to" |
| Grounded speculation | "may", "could potentially", "is likely to" |
| Speculation without direct evidence | "we hypothesize", "it is plausible that" |

### Overclaim Patterns to Fix

| Overclaim | Appropriate Version |
|-----------|-------------------|
| X causes Y (without causal evidence) | X is associated with Y / X correlates with Y |
| proves that | provides evidence that / supports |
| for the first time | to the best of our knowledge, the first |
| universally / in all cases | in the cases tested / across our benchmarks |
| will revolutionize | has the potential to improve |
| clearly demonstrates | the results indicate |

---

## Dimension 3: Coherence & Flow

### Checkpoints

- [ ] Logical transitions between paragraphs (cause/contrast/progression/elaboration)
- [ ] Given-new principle: each sentence opens with known info, ends with new info
- [ ] Argument chain completeness (claim → evidence → interpretation, no gaps)
- [ ] Effective topic sentences in each paragraph
- [ ] Cross-section logical connection
- [ ] No information jumps (each step follows from the previous)

### Coherence Repair Strategies

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| Disconnected sentences | No logical link between adjacent sentences | Add connector or reorder |
| Information jump | Missing intermediate reasoning step | Insert bridging sentence |
| Unfocused paragraph | No clear single topic | Split or add topic sentence |
| Argument gap | Claim without evidence, or evidence without interpretation | Fill the missing element |
| Section disconnect | Abrupt topic change between sections | Add transitional paragraph or sentence |

### Given-New Principle Examples

Before (new-new-new, hard to follow):
> Graph neural networks aggregate neighbor features. Message passing is iterative.
> Over-smoothing occurs after many layers.

After (given-new chain):
> Graph neural networks aggregate neighbor features through iterative message passing.
> As the number of iterations grows, this repeated aggregation causes node representations
> to converge, a phenomenon known as over-smoothing.

---

## Dimension 4: Conciseness

### Checkpoints

- [ ] No redundant modifiers ("very unique" → "unique")
- [ ] No filler phrases (see word-choice-anti-ai.md template phrases)
- [ ] No repeated information across sentences
- [ ] Passive → active when active is shorter and clearer
- [ ] No throat-clearing openings
- [ ] No double negatives when a positive statement is clearer
- [ ] Nominalizations reduced ("make a comparison" → "compare")

### Compression Patterns

| Verbose | Concise |
|---------|---------|
| the method that was proposed by X | X's method |
| performed an analysis of | analyzed |
| has the capability to | can |
| exhibited a tendency to | tended to |
| on the basis of | based on |
| a total of 50 samples | 50 samples |
| in a manner that is efficient | efficiently |
| the process of training | training |
| whether or not | whether |
| in the field of machine learning | in machine learning |
| it can be seen from Figure 3 that | Figure 3 shows |
| the reason is because | because |

### Target Metrics

- Average sentence length: 15-25 words (academic sweet spot)
- Paragraph length: 3-8 sentences (varies by section)
- Words per idea: minimize without sacrificing clarity

---

## Dimension 5: Terminology

### Checkpoints

- [ ] Same concept uses same term throughout (no synonym cycling)
- [ ] Abbreviations defined on first use (separately in Abstract and Body)
- [ ] One-time abbreviations spelled out (not abbreviated)
- [ ] Domain-standard terms used correctly
- [ ] Hypernym/hyponym relationships correct
- [ ] No term overloading (same word for different concepts)

### Operation Protocol

1. **Build terminology table:** Scan text, map each concept → canonical term
2. **Check consistency:** Flag any synonym alternation for the same referent
3. **Verify abbreviations:**
   - First use has full expansion? (in both Abstract and Body separately)
   - Used only once? → don't abbreviate, spell out
   - Commonly known in the field? → may skip definition (e.g., CNN, NLP at ML venues)
4. **Flag potential misuse:** Terms that seem technically imprecise for the domain

### Common Terminology Issues

| Issue | Example | Fix |
|-------|---------|-----|
| Synonym cycling | model / framework / system / architecture (same thing) | Pick one, use pronouns for variation |
| Undefined abbreviation | "We train with DPO" (never defined) | "Direct Preference Optimization (DPO)" on first use |
| Overcrowded abbreviations | 10+ abbreviations in one page | Only abbreviate terms used 3+ times |
| Imprecise term | "algorithm" when referring to a heuristic | Use the precise term |

---

## Dimension 6: Structure & Formatting

### Checkpoints

- [ ] Section divisions appropriate for content and target venue
- [ ] Every figure/table referenced in text ("as shown in Figure 2")
- [ ] Citation format correct (narrative vs parenthetical appropriate)
- [ ] Paragraph length reasonable (not < 3 sentences or > 10 sentences)
- [ ] Lists/enumerations used appropriately (not overused)
- [ ] Equation numbering consistent (only numbered if referenced)
- [ ] Consistent heading capitalization style

### Citation Format Rules

| Style | Narrative | Parenthetical |
|-------|-----------|---------------|
| IEEE | "In [5], the authors..." | "...has been shown [5]" |
| APA | "Smith et al. (2023) showed..." | "...was demonstrated (Smith et al., 2023)" |
| Vancouver | "As reported by Smith et al.^5..." | "...has been reported.^5" |

### Figure/Table Checklist

- Every figure/table has a caption
- Caption is self-contained (understandable without main text)
- Referenced before it appears (or on same page)
- Consistent numbering (Figure 1, 2, 3... not Figure 1, Figure A, Figure 2)

---

## Dimension 7: Clarity of Argument

### Checkpoints

- [ ] Every claim has supporting evidence
- [ ] Contributions are specific and verifiable
- [ ] Causal claims backed by data (not just "X causes Y")
- [ ] Comparative claims have explicit baselines ("better than what?")
- [ ] Discussion takes a position (not balanced hedging without conclusion)
- [ ] No logical fallacies (appeal to authority, circular reasoning)

### Argument Clarity Protocol

1. **Extract claims:** Identify all contribution/result/conclusion statements
2. **Map evidence:** For each claim, identify its supporting evidence source
3. **Flag unsupported claims:** Mark as needing either evidence or weaker phrasing
4. **Check overclaims:** Identify causal assertions without sufficient evidence
5. **Verify comparatives:** Every "better/faster/more accurate" has a named baseline and metric

### Common Clarity Issues

| Issue | Example | Fix |
|-------|---------|-----|
| Unsupported claim | "Our method significantly outperforms" (no table ref) | Add "(Table 2)" or weaken to "improves upon" |
| Vague contribution | "We study the problem of X" | "We propose Y that achieves Z on benchmark W" |
| Missing baseline | "achieves good performance" | "outperforms BERT-base by 3.2 F1 on SQuAD" |
| Circular reasoning | "X is important because it matters" | State WHY it matters with external evidence |
| Unresolved discussion | Presents two views, concludes nothing | Take a position with evidence preference |

---

## Dimension 8: Journal Compliance

### Checkpoints

- [ ] Word/page count within limits
- [ ] Citation format matches venue requirements
- [ ] Section naming follows venue conventions
- [ ] Abstract structure (structured vs unstructured) matches requirements
- [ ] Figure format requirements met (DPI, color mode, file type)
- [ ] Reference format correct (BibTeX style matching)
- [ ] Required declarations present (data availability, conflicts, funding, ethics)
- [ ] Author information format correct

### When No Target Journal Specified

If the user does not specify a target journal:
- Apply general academic standards (no journal-specific checks)
- Score based on internal consistency only
- Note in report: "Journal compliance scored for general standards; specify target venue for detailed check"

### Common Venue Formats

| Venue Type | Key Requirements |
|------------|-----------------|
| IEEE Transactions | Double-column, numbered citations [1], structured abstract optional |
| NeurIPS/ICML/ICLR | Single-column submission, author-year citations, 8-9 page limit |
| ACL/EMNLP | Specific LaTeX template, ARR review format, ethics statement |
| Elsevier journals | Highlights, graphical abstract, structured abstract, keywords |
| Nature/Science | Strict word limits, specific section naming, methods often separate |
| Springer | LNCS format for conferences, varies for journals |

---

## Execution Protocol for Phase B

```
1. SCORE: Rate all 8 dimensions (1-5) based on checkpoints above
   → Record scores in the polish report template

2. IDENTIFY: Find dimensions scoring ≤ 3
   → These are the active editing targets

3. EDIT: Fix issues in order:
   Dim 1 (Grammar) → Dim 7 (Clarity) → Dim 3 (Coherence) →
   Dim 4 (Conciseness) → Dim 2 (Tone) → Dim 5 (Terminology) →
   Dim 6 (Structure) → Dim 8 (Journal)
   
   Rationale: Grammar fixes first (foundation), then logical
   structure, then style, then formatting.

4. PRESERVE: During B edits, check that Phase A improvements are not undone:
   - Burstiness maintained (sentence length variety)
   - No Tier 1 AI words reintroduced
   - No template phrases reintroduced
   - Punctuation fingerprints still clean

5. RE-SCORE: Rate edited dimensions again
   → Record "After" scores in report
```

---

## Cross-Dimension Conflicts

| Conflict | Resolution |
|----------|-----------|
| Conciseness vs Coherence | Keep transitional elements that serve logical flow |
| Burstiness (Phase A) vs Grammar | Varied sentence length must still be grammatical |
| Academic Tone vs De-AI (Phase A) | Don't reintroduce AI patterns while formalizing |
| Conciseness vs Clarity | Keep explanatory text that prevents ambiguity |
| Terminology consistency vs Perplexity | Consistent terms win; vary syntax instead of nouns |