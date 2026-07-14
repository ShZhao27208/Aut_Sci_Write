# Word Choice Anti-AI — Academic Replacement Table

Specialized word replacement reference for reducing AI detection in academic papers.
Three-tier system: Tier 1 (always replace), Tier 2 (frequency-limited), Tier 3 (context-dependent).

Sources: avoid-ai-writing detector/patterns.js (109-word list),
academic-writing-skills tone-thresholds.yaml, forbidden-terms.md,
Aut_Sci_Write sci-review/references/word-choice.md.

---

## I. Tier 1 — Always Replace (Appearance = Immediate Flag)

These words are statistically over-represented in AI-generated text and serve as
high-confidence detection signals. Replace on sight unless they are protected technical terms.

| AI Word | Academic Replacements | Context Notes |
|---------|----------------------|---------------|
| delve | examine, investigate, explore, probe | never appropriate in academic writing |
| leverage | use, apply, exploit, build on | business jargon |
| utilize | use | almost all contexts |
| robust | reliable, stable, consistent, resilient | needs quantitative evidence to support |
| comprehensive | thorough, complete, exhaustive, [N]-faceted | too vague without specifics |
| streamline | simplify, accelerate, reduce overhead | business jargon |
| pivotal | important, critical, essential | overclaiming without evidence |
| landscape | field, domain, area, space | AI signature word |
| underscore | show, demonstrate, indicate, highlight | |
| elucidate | explain, clarify, describe | unnecessarily ornate |
| tapestry | (rewrite: describe actual complexity) | never in academic CS |
| paradigm | model, approach, framework, method | unless citing Kuhn |
| cutting-edge | latest, newest, recent, advanced | promotional |
| meticulous | careful, detailed, precise, rigorous | |
| meticulously | carefully, precisely, rigorously | |
| seamless | smooth, integrated, transparent | |
| seamlessly | smoothly, without interruption | |
| holistic | complete, full, whole, end-to-end | |
| actionable | practical, useful, concrete, applicable | business jargon |
| impactful | effective, influential | not standard academic |
| synergy | (describe the combined effect directly) | business jargon |
| interplay | relationship, interaction, coupling | |
| embrace | adopt, accept, use, incorporate | |
| foster | encourage, support, promote, enable | |
| empower | enable, allow, equip | |
| bolster | support, strengthen, reinforce | |
| spearhead | lead, drive, initiate | |
| harness | use, exploit, take advantage of | |
| navigate | handle, address, work through | |
| unleash | release, enable, unlock | |
| elevate | improve, raise, enhance | |
| nestled | located, situated | never in academic |
| vibrant | active, dynamic | promotional |
| thriving | growing, active, productive | promotional |
| bustling | busy, active | never in academic |
| intricate | complex, detailed, involved | |
| enduring | lasting, persistent, long-standing | |
| daunting | difficult, challenging | too informal |
| game-changing | transformative, significant | promotional |
| unprecedented | first reported, not previously observed | qualify with evidence |
| groundbreaking | novel, original, first | qualify with evidence |
| revolutionary | new, significantly different | overclaiming |

---

## II. Tier 2 — Frequency-Limited (Exceed Threshold = Flag)

These words have legitimate academic uses but become AI tells when overused.
Monitor frequency per document.

| Word | Max per Doc | When to Replace | Replacement Direction |
|------|-------------|-----------------|----------------------|
| significant | 5 | when not backed by statistical test | report the number: "p < 0.01" or "12% improvement" |
| novel | 4 | when novelty is not substantiated | "new" or describe what is actually new |
| effective | 5 | when no metric is cited | quantify: "achieves 94.2% accuracy" |
| furthermore | 3 | paragraph-initial filler | delete, or "And" / "Also" / direct continuation |
| moreover | 3 | same as furthermore | delete, or rewrite as flowing prose |
| notably | 3 | when observation is not actually notable | delete or cite the evidence |
| remarkable / remarkably | 3 | subjective without evidence | delete or quantify |
| various | 5 | when items can be listed | name them: "three encoder types" |
| several | 5 | when count is available | give the number: "four studies" |
| numerous | 3 | same as several | give the number |
| important | 5 | when importance is asserted not shown | explain why: "critical for convergence because..." |
| clearly | 4 | when clarity is not self-evident | "the results show" or delete |
| obviously | 1 | rarely appropriate | delete entirely in most cases |

---

## III. Tier 3 — Context-Dependent (Legitimate Uses Exist)

These words are common in AI text but also have valid academic uses.
Flag only when used in a pattern that matches AI style (e.g., as filler, without evidence).

| Word | Legitimate Use | AI-Style Use (flag) |
|------|---------------|---------------------|
| demonstrate | "We demonstrate that X" (with experiment) | "This demonstrates the importance of" (no evidence) |
| enhance | "enhance resolution by 2x" (quantified) | "enhance the overall quality" (vague) |
| achieve | "achieves 95% recall" (with metric) | "achieves good results" (no metric) |
| propose | "We propose Algorithm 2" (specific) | "We propose a comprehensive framework" (vague) |
| explore | "explore the parameter space" (specific) | "explore various aspects" (vague) |
| address | "address the cold-start problem" (named) | "address these challenges" (unnamed) |
| facilitate | "facilitates gradient flow via skip connections" (mechanism) | "facilitates better understanding" (vague) |
| contribute | "contributes a 2.1-point gain" (measured) | "contributes to the field" (generic) |
| enable | "enables real-time inference" (specific capability) | "enables researchers to" (generic) |
| highlight | "highlighted in red in Figure 3" (visual) | "highlights the importance of" (filler) |

---

## IV. Template Phrase Replacements

### Delete Entirely (zero information content)

- It is worth noting that
- It should be mentioned that
- It is important to note that
- It is interesting to note that
- It goes without saying that
- It bears mentioning that
- As a matter of fact

### Compress (multi-word → single word/short phrase)

| Verbose (AI) | Concise |
|--------------|---------|
| In order to | To |
| Due to the fact that | Because |
| In light of the fact that | Since / Because |
| Despite the fact that | Although / Despite |
| For the purpose of | To / For |
| With regard to / With respect to | About / On / For |
| In the event that | If |
| Prior to | Before |
| Subsequent to | After |
| At this point in time | Now / Currently |
| In the majority of cases | Usually / Often |
| A large number of | Many / [specific number] |
| Has the ability to / Has the capacity to | Can |
| Performed an analysis of | Analyzed |
| Conducted an experiment on | Tested / Measured |
| Made a comparison between | Compared |
| Exhibited a tendency to | Tended to |
| On the basis of | Based on |
| A total of [N] samples | [N] samples |
| The method that was proposed by X | X's method |
| In close proximity to | Near |
| Is indicative of | Indicates |
| Serves as evidence of | Shows / Evidences |

### Transition Replacements

| AI Transition | Replace With |
|---------------|-------------|
| Furthermore, | (delete — let next sentence follow naturally) or "Also," |
| Moreover, | (delete) or "And" |
| Additionally, | (delete) or "Also," |
| In addition to the above, | "And" |
| It is clear that | (delete — assert directly) |
| As previously mentioned, | (delete or rephrase without callback) |
| This highlights the importance of | State the importance directly |
| In conclusion, | (delete — or "The net result:" if needed) |
| To summarize, | (delete) |
| In summary, | (delete — just state the summary) |
| As mentioned earlier, | (delete) |

### Opening Phrase Replacements

| AI Opening | Replace With |
|------------|-------------|
| In recent years, | Since [year] / Over the past decade / (delete) |
| With the rapid development of X, | (delete — state the problem directly) |
| X has attracted growing attention | Research on X has expanded; [cite] showed... |
| It has been shown that | [Author] (year) showed / demonstrated |
| It is well known that | (cite the source, or just state the fact) |
| There is growing interest in | (delete — cite specific recent works) |

---

## V. Academic Protected Terms (NEVER Replace)

### Machine Learning / Deep Learning

Transformer, attention mechanism, self-attention, multi-head attention,
feedforward network, encoder, decoder, embedding, tokenizer, BERT, GPT,
backpropagation, gradient descent, SGD, Adam, learning rate, batch size,
overfitting, underfitting, regularization, dropout, batch normalization,
layer normalization, residual connection, skip connection, convolution,
pooling, activation function, ReLU, softmax, cross-entropy, loss function,
fine-tuning, pre-training, transfer learning, few-shot, zero-shot,
reinforcement learning, reward model, RLHF, DPO, PPO

### Mathematics and Statistics

p-value, confidence interval, standard deviation, variance, mean, median,
correlation, regression, distribution, hypothesis, null hypothesis,
statistical significance, effect size, ANOVA, chi-square, t-test,
Bayesian, posterior, prior, likelihood, convergence, eigenvalue,
gradient, Hessian, Jacobian, convex, non-convex, optimization

### LaTeX Commands (never modify)

\cite{}, \ref{}, \label{}, \begin{}, \end{}, \textbf{}, \textit{},
\section{}, \subsection{}, \caption{}, \includegraphics{},
\footnote{}, \url{}, \href{}, \newcommand{}, \usepackage{},
all math environments ($...$, \[...\], equation, align, etc.)

### Dataset and Benchmark Names

ImageNet, CIFAR-10/100, MNIST, COCO, VOC, SQuAD, GLUE, SuperGLUE,
MMLU, HumanEval, GSM8K, MATH, WMT, CommonCrawl, The Pile, RedPajama,
LMSYS, Chatbot Arena, MT-Bench, AlpacaEval

### Algorithm and Method Names from Literature

Always preserve method names as cited by their authors. When in doubt
about whether a term is a method name, keep the original and flag for
user review.

---

## VI. Usage Rules

1. **Scan order:** Tier 1 → Template Phrases → Tier 2 threshold check → Tier 3 context check
2. **Never replace protected terms** even if they appear in Tier 1/2 lists
3. **Context matters:** "robust optimization" (technical term) ≠ "robust framework" (AI filler)
4. **One replacement per concept:** Don't create new synonym cycling by using different replacements for the same word in nearby sentences
5. **Preserve meaning:** If no replacement preserves the exact meaning, keep the original and flag
6. **Check collocations:** Some replacements don't collocate well; "use" doesn't always work where "leverage" was (e.g., "leverage existing infrastructure" → "build on existing infrastructure", not "use existing infrastructure")
