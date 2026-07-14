# De-AI Strategies — Rewriting Guide for AI Trace Reduction

Operational guide for reducing AI detection scores in academic text.
Apply these strategies during Phase A, BEFORE the 8-dimension polish (Phase B).

Sources: humanize (9 levers), AIGC-Detector-Pro (7 rewrite techniques),
academic-writing-skills (deai/guide.md), humanizer_academic (Voice Calibration, Pattern 34).

---

## Core Formula

```
Semantic restructuring + Sentence diversification + Personalization injection + Perplexity elevation
```

## Priority Ranking (Empirical Evidence)

| Priority | Strategy | Expected Impact |
|----------|----------|----------------|
| ★★★★★ | Strategy 1 (Burstiness) + Strategy 2 (Vocabulary) | ~90% of AI score reduction |
| ★★★ | Strategy 3 (Sentence restructuring) + Strategy 6 (Perplexity) | significant additional reduction |
| ★★ | Strategy 4 (Concept concretization) + Strategy 5 (Argumentation) + Punctuation normalization | minor but measurable |
| ★ | Strategy 7 (Style disruption) + Voice Calibration | finishing touches |

Execute in priority order. After ★★★★★ strategies, re-check AI patterns before proceeding.

---

## Strategy 1: Burstiness Enforcement (Sentence Rhythm)

**Goal:** Increase sentence length variance to match human writing patterns.

### Hard Rules

1. Longest sentence minus shortest ≥ 20 words in any passage > 80 words
2. Every 150 words: at least one sentence ≤ 6 words
3. No more than 3 consecutive sentences within ±5 words of each other
4. < 50% of sentences in the 10-20 word band (the "AI comfort zone")
5. Target sentence length standard deviation > 8

### Operations

| Situation | Fix |
|-----------|-----|
| Run of similar-length sentences | Merge two into a compound sentence OR split one into a fragment |
| All sentences 12-18 words | Insert one 5-word assertion + one 25+ word sentence with subordinate clauses |
| Uniform paragraph rhythm | Vary paragraph lengths: 2-sentence para followed by 6-sentence para |
| Opening sentences all similar length | Start one paragraph with a fragment, another with a long contextual sentence |

### Examples

Before (uniform, SD ≈ 3):
> The model achieves strong performance on all benchmarks. The results demonstrate significant improvement over baselines. The ablation study confirms the contribution of each component.

After (varied, SD ≈ 12):
> On every benchmark, the model outperforms prior work. Not marginally. Table 3 shows that the gap widens on low-resource splits, where the attention re-routing mechanism contributes a 4.2-point F1 gain that vanishes when we ablate it, confirming that the architecture handles sparse supervision rather than merely fitting dense-data patterns.

---

## Strategy 2: Perplexity Injection (Vocabulary Level)

**Goal:** Replace predictable AI word choices with less predictable but accurate alternatives.

### Operations

1. **Replace Tier 1 words immediately** (see `word-choice-anti-ai.md`)
2. **Swap generic verbs for domain-specific ones:**
   - "address the problem" → "untangle the dependency issue"
   - "implement the method" → "wire up the inference pipeline"
   - "analyze the data" → "sift through the activation traces"
3. **One surprising-but-accurate word per paragraph:**
   - Not forced creativity; let the subject suggest the vocabulary
   - A materials scientist says "anneal"; a systems engineer says "thrash"
4. **Avoid synonym cycling** (a strong AI tell):
   - Pick ONE canonical noun per concept + use pronouns for variation
   - WRONG: "the model / the framework / the system / the architecture" (same thing, four labels)
   - RIGHT: "the model" + "it" + occasional "our encoder"
5. **Use concrete language over abstract:**
   - "significant improvement" → "reduces error by 12.3%"
   - "various methods" → "three encoder variants (LSTM, Transformer, Mamba)"

### Protected Terms (never replace)

- Technical terms (Transformer, attention, backpropagation, gradient descent)
- Dataset/benchmark names (ImageNet, GLUE, SQuAD)
- Mathematical symbols and LaTeX commands
- Author-defined abbreviations
- Algorithm names and method names from cited work

---

## Strategy 3: Sentence Restructuring

**Goal:** Break monotonous syntactic patterns that AI detectors flag.

### Operations

| Pattern | Restructure To |
|---------|---------------|
| Subject-verb-object chain (S-V-O, S-V-O, S-V-O) | Mix: fronted adverbial, passive (occasionally), inverted conditional |
| "First... Second... Third..." enumeration | Hierarchical argument with subordination showing logical relationships |
| All active voice | Introduce 1-2 passive sentences where the agent is unimportant |
| All passive voice | Restore subjects: "We computed..." / "The optimizer converges..." |
| "首先/其次/最后" progression | Replace with causal/conditional/contrastive connectors |
| Uniform clause structure | Insert a parenthetical remark or appositive |

### Sentence Openers to Vary

Avoid starting 3+ consecutive paragraphs with the same structure. Mix from:
- Subject-first: "The encoder processes..."
- Adverbial-first: "Under heavy load, the system..."
- Conditional-first: "When gradients explode, ..."
- Temporal-first: "After 50 epochs, ..."
- Concessive-first: "Although slower, this approach..."
- Result-first: "A 3x speedup emerges when..."

---

## Strategy 4: Concept Concretization

**Goal:** Replace abstract AI-style claims with specific, verifiable statements.

### Operations

| Abstract (AI) | Concrete (Human) |
|---------------|-----------------|
| significant improvement | reduces error by X% (Table 2) |
| many studies | three recent studies [1-3] |
| various methods | LSTM, Transformer, and Mamba encoders |
| large dataset | 2.4M training samples from CommonCrawl |
| high performance | 94.2% accuracy on the held-out test split |
| state-of-the-art results | surpasses GPT-4 by 3.1 BLEU on WMT23 |
| real-world applications | deployed in production at [company] serving 10K QPS |

### When Specifics Are Unavailable

- Mark as `[PENDING VERIFICATION]`
- Use hedged framing: "on the order of..." / "approximately..."
- Reference the source: "as reported in Table X of [Author]"

---

## Strategy 5: Argumentation Enrichment

**Goal:** Transform linear AI argumentation into multi-dimensional human reasoning.

### AI Pattern (Linear)
```
Claim → Explanation → Conclusion
```

### Human Pattern (Multi-dimensional)
```
Claim → Evidence from experiment → Contrasting evidence from literature
→ Qualification/boundary condition → Interpretation with limitations acknowledged
```

### Operations

1. **Add comparative references:** "Unlike [Author]'s approach, which assumes..."
2. **Insert boundary conditions:** "This holds for batch sizes > 32; below that threshold..."
3. **Include methodological reflection:** "We note that this comparison is confounded by..."
4. **Acknowledge alternative interpretations:** "An equally plausible explanation is..."
5. **Show awareness of limitations:** "The improvement may partially stem from..."

---

## Strategy 6: Perplexity Elevation (Advanced)

**Goal:** Use unconventional but correct expressions that increase text unpredictability.

### Operations

1. **Unconventional sentence openers:** Start with a result, an aside, or a datum rather than context
2. **Domain-specific minor terminology:** Use precise sub-field terms that a specialist would know
3. **Observational asides in data description:** "Interestingly, the loss surface near epoch 30 resembles..."
4. **Non-template transitions:** Replace formulaic connectors with content-bearing bridges
5. **Vary information density:** Some sentences are dense (multi-clause, data-heavy); others are sparse (single observation)

### Example

Before: "Furthermore, the results clearly demonstrate that our method significantly outperforms the baseline."

After: "The gap is largest on the long-tail classes — 8.7 F1 points — where the baseline's uniform prior hurts most."

---

## Strategy 7: Style Disruption

**Goal:** Break the uniform "well-polished AI" style that detectors recognize.

### Operations

1. **Inter-paragraph style variation:** Some paragraphs tighter and more telegraphic; others more expansive with subordinate clauses
2. **Occasional imperfect transitions:** Not every paragraph connects smoothly to the next; a slight topic shift is human
3. **Section-specific register shifts:** Methods can be drier and more procedural; Discussion can be more speculative
4. **Break the "perfect paragraph" arc:** Let one paragraph serve two ideas, or end one thought mid-paragraph
5. **Asymmetric depth:** Spend 3 sentences on an important detail, 1 sentence on a less important one (AI tends to balance)

---

## Voice Calibration (Optional — Requires Author Sample)

When the user provides previously published papers by the same author:

### Process

1. **Extract author profile:**
   - Average sentence length and standard deviation
   - Preferred transition words and frequency
   - Punctuation habits (comma density, parenthetical usage)
   - Tense patterns per section type
   - Hedging style (which hedge words they actually use)
2. **Match the profile:**
   - Use the author's ACTUAL sentence length distribution, not a generic "human" one
   - Adopt their specific connector preferences
   - Mirror their punctuation density
3. **Advantage:** Replaces AI patterns with the author's real voice rather than generic "humanized" voice

---

## Execution Protocol

### Phase A Execution Order

```
1. SCAN: Identify all AI traces using ai-detection-patterns.md
   → Categorize as High / Medium / Low priority

2. REWRITE (Priority order):
   a. Burstiness enforcement (Strategy 1) — restructure sentence lengths
   b. Vocabulary de-AI (Strategy 2) — replace Tier 1 words and template phrases
   c. Sentence restructuring (Strategy 3) — vary syntax patterns
   d. Concept concretization (Strategy 4) — add specifics where available
   e. Argumentation enrichment (Strategy 5) — add depth to claims
   f. Perplexity elevation (Strategy 6) — introduce unpredictability
   g. Style disruption (Strategy 7) — break uniformity

3. SELF-AUDIT: Re-scan output against ai-detection-patterns.md
   → Any remaining High-priority patterns? Fix them.
   → Check burstiness metrics: SD > 8? Range ≥ 20? Mid-band < 50%?

4. VERIFY PRESERVATION:
   → All LaTeX commands intact?
   → All citations intact?
   → All technical claims unchanged in meaning?
   → No fabricated data or references?
```

### Constraints During De-AI

- NEVER sacrifice meaning for score reduction
- NEVER add information not present or derivable from the original
- Preserve the exact logical structure of arguments
- If a Tier 1 word is the technically correct term in context, KEEP it and flag for user review
- Burstiness changes must not create run-on sentences or fragments that damage readability
