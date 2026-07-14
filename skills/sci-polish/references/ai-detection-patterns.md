# AI Detection Patterns — Academic Text Feature Library

This reference catalogs identifiable AI-generated text patterns for academic writing.
Use it during Phase A (De-AI) to scan and flag AI traces before rewriting.

Sources: avoid-ai-writing (109-word list), AIGC-Detector-Pro (12 characteristics),
humanize (9 signals), academic-writing-skills (tone-thresholds.yaml).

---

## Detection Principles

AI detectors measure two core signals:

1. **Perplexity** (word predictability): AI text median ~21.2 vs human ~35.9 (AUC=0.78)
2. **Burstiness** (sentence length variance): human variance is 2-3x that of AI text

Secondary signals: lexical repetition, structural uniformity, punctuation fingerprint,
hedge density, RLHF voice markers.

---

## I. Lexical Patterns (Highest Priority)

### P0 — Tier 1: Must-Replace Words (appear → immediate flag)

| Word | Academic Replacements |
|------|---------------------|
| delve | examine, investigate, explore |
| leverage | use, apply, exploit, build on |
| utilize | use |
| robust | reliable, stable, consistent |
| comprehensive | thorough, complete, [N]-dimension |
| streamline | simplify, accelerate |
| pivotal | important, critical (with evidence) |
| landscape | field, domain, area |
| underscore | show, demonstrate, indicate |
| elucidate | explain, clarify |
| tapestry | (describe actual complexity) |
| beacon | (rewrite entirely) |
| cutting-edge | latest, newest, advanced |
| meticulous / meticulously | careful, detailed / carefully, precisely |
| seamless / seamlessly | smooth, easy / smoothly, easily |
| holistic / holistically | complete, full / completely, fully |
| actionable | practical, useful, concrete |
| impactful | effective, significant |
| synergy / synergies | (describe the combined effect) |
| interplay | relationship, connection |
| embrace | adopt, accept, use |
| paradigm | model, approach, framework |
| foster | encourage, support, build |
| empower | enable, let, allow |
| bolster | support, strengthen |
| spearhead | lead, drive |
| harness | use, take advantage of |
| navigate / navigating | work through, handle |
| unleash | release, enable |
| elevate | improve, raise |

### P0 — Tier 1: Must-Replace Phrases

| Phrase | Replace With |
|--------|-------------|
| delve into | explore, examine |
| deep dive | look at, examine |
| dive into | look at, examine |
| testament to | shows, proves |
| watershed moment | turning point, shift |
| in order to | to |
| due to the fact that | because |
| serves as | is |
| in light of the fact that | since |
| at its core | (cut, just state it) |
| unpack / unpacking | explain, break down |
| best practices | what works, proven methods |
| thought leadership | expert, authority |

### P1 — Tier 2: Frequency-Limited Words (max occurrences per document)

| Word | Max/Doc | Replacement Direction |
|------|---------|----------------------|
| significant | 5 | use specific data instead |
| novel | 4 | new, or state what is new |
| effective | 5 | quantify with metrics |
| furthermore | 3 | And / direct continuation |
| moreover | 3 | Also / direct continuation |
| notably | 3 | delete or state evidence directly |
| remarkable / remarkably | 3 | (delete or cite the evidence) |
| various | 5 | list specific items |
| several | 5 | give the number |
| numerous | 3 | give the number |
| important | 5 | explain why it matters |
| clearly / obviously | 3+1 | evidence indicates / results show |

### P2 — Template Phrases (delete or compress)

| AI Template | Action |
|-------------|--------|
| It is worth noting that | DELETE — state directly |
| It should be mentioned that | DELETE |
| It is important to note that | DELETE |
| In order to | → To |
| Due to the fact that | → Because |
| For the purpose of | → To / For |
| With regard to | → About |
| A large number of | → Many / [specific number] |
| In the majority of cases | → Usually / In X% of cases |
| It has been shown that | → [Author] (year) showed |
| In recent years | → Since [year] / Over the past decade |
| With the rapid development of | DELETE — enter the problem directly |
| As previously mentioned | DELETE or rephrase without callback |
| This highlights the importance of | → say what the importance IS |

### P3 — AI Transition Word Stacking

Flag when paragraph-initial position contains:
- "Furthermore," / "Moreover," / "Additionally," (cluster of 2+ in 3 paragraphs)
- "In conclusion," / "To summarize," / "In summary,"
- "As previously mentioned,"
- "It is clear that"

---

## II. Syntactic Patterns

### Sentence Length Uniformity (Burstiness Deficit)

**Detection rules:**
- 3+ consecutive sentences with word count within ±5 of each other → HIGH risk
- Full-text sentence length standard deviation < 8 → HIGH risk
- 80%+ sentences in 10-20 word band → MEDIUM risk

**Correction targets:**
- Longest sentence minus shortest ≥ 20 words
- Every 150 words: at least one sentence ≤ 6 words
- No more than 3 consecutive sentences within ±5 words of each other
- Mid-band (10-20 words) must contain < 50% of all sentences

### Structural Symmetry

- Over-symmetric IMRAD (each section has near-equal paragraph count)
- Paragraph length uniformity (80% of paragraphs are 5-7 sentences)
- "Topic sentence + evidence + restatement" three-part formula in every paragraph

### Copula Avoidance (AI tells)

AI avoids "is"/"has" and uses fancier alternatives:
- "serves as" / "stands as" / "marks" / "represents" → use "is" or "has"
- "boasts" / "features" / "offers" → use "has" or "includes"

---

## III. Discourse-Level Patterns

### RLHF Fingerprints

- Unsolicited balanced tradeoffs (hedging both sides without taking a position)
- "Helpful assistant" register (overly accommodating tone)
- Safety disclaimers and knowledge-cutoff statements
- Negation-framing pivots: "not just X, it's Y" / "not merely A, but B"
- Fake insight markers: "essentially", "in fact", "the key is", "more importantly"

### Structural Templates

- Intro + 3 bullet points structure
- "There are three main factors: ..."
- Numbered sections for everything
- Perfect paragraph-per-idea arc (no unresolved thoughts)
- Fake concession: "While X is true, Y" with no genuine contrast
- Lecture colon: "The conclusion is:" / "The reason is simple:"

### Argumentation Linearity

- Linear: claim → explanation → conclusion (no multi-dimensional evidence)
- No methodology reflection or limitation discussion
- No comparison with alternative interpretations
- Vague referents: "this shows", "these factors", "various aspects"

---

## IV. Punctuation Fingerprints

| Mark | AI Pattern | Threshold | Academic Norm |
|------|-----------|-----------|---------------|
| Em dash (—) | 3-5x human frequency | max 1 per 300 words | use commas or periods instead |
| Semicolons (;) | overused as clause linker | rare in academic prose | only for list items with commas |
| Mid-sentence colon (:) | used for "dramatic reveal" | max 1 per paragraph | only to introduce lists/definitions |
| Exclamation (!) | occasionally appears | 0 in body text | never in academic body |
| Curly quotes ("") | typography signal | use straight quotes | depends on venue style |

---

## V. Content-Depth Indicators

| Indicator | AI Pattern | Human Pattern |
|-----------|-----------|---------------|
| Vocabulary repetition | "significant", "effective", "important" cycling | domain-specific precise vocabulary |
| Concept abstraction | vague qualifiers without data | specific numbers, conditions, parameters |
| Citation integration | generic "studies show" | "[Author] (year) demonstrated that [specific finding]" |
| Methodological depth | surface description | equipment models, parameter values, experimental conditions |
| Limitation awareness | absent or token mention | genuine reflection on constraints and tradeoffs |
| Style consistency | uniform register throughout | natural variation between sections |

---

## VI. Section-Specific AI Tells

### Abstract
- Opens with "In recent years" or "With the rapid development of"
- Uses "significant improvement" without numbers
- Claims "novel" without specifying novelty

### Introduction
- "has attracted growing attention" / "has been extensively studied"
- Three-part parallel structure for all claims
- Overclaiming: "for the first time", "unprecedented", "revolutionary"

### Methods
- Passive voice throughout without naming the agent
- "In order to achieve X, we utilize Y" pattern
- Uniform sentence length in procedural descriptions

### Results
- "significant improvement" without effect size or p-value
- "clearly demonstrates" / "obviously shows" without letting data speak
- Perfectly balanced presentation (no prioritization of findings)

### Discussion
- "Despite these limitations" as a transition formula
- Balanced hedging without committing to interpretation
- "Future work should explore" as generic closer

### Conclusion
- Restating the full methodology (should be brief)
- "In conclusion, this paper presents" opener
- Generic "broader implications" without specifics

---

## VII. Quantitative Thresholds

From `tone-thresholds.yaml` — use for automated/semi-automated checking:

```yaml
term_thresholds:
  significant: 5
  comprehensive: 3
  effective: 5
  novel: 4
  robust: 4
  important: 5
  various: 5
  several: 5
  numerous: 3
  furthermore: 3
  moreover: 3
  notably: 3
  remarkable: 3
  clearly: 4

burstiness:
  consecutive_paragraphs: 3
  opening_token_count: 2

punctuation:
  max_em_dashes_per_doc: 5
  ban_exclamation_in_body: true

overclaim_patterns:
  - "caused by" → soften causal
  - "determines" → soften causal
  - "proves that" → soften causal
  - "for the first time" → qualify novelty
  - "unprecedented" → qualify novelty
  - "universally" → bound universal
  - "in all cases" → bound universal
  - "will revolutionize" → hedge application
```

---

## Priority Ranking for De-AI Editing

Based on empirical evidence (humanizer_academic Pattern 34):

| Priority | Category | Impact |
|----------|----------|--------|
| ★★★★★ | Sentence rhythm (burstiness) + Vocabulary de-AI | ~90% of detection reduction |
| ★★★ | Structural diversification + Perplexity elevation | ~7% additional |
| ★★ | Transition word correction + Punctuation normalization | ~2% additional |
| ★ | Register/voice adjustment | ~1% additional |

Always fix in this order: highest-impact patterns first.
