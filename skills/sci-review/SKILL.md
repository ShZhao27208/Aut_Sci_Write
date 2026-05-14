---
name: sci-review
description: Specialized workflows for drafting, refining, and responding to academic literature reviews and peer review feedback. Use this skill for literature review outlines, research-gap synthesis, reviewer rebuttals, response letters, and academic writing tone repair.
author: Shuo Zhao
license: MIT
copyright: Copyright 2026 Shuo Zhao. All rights reserved.
triggers:
  - literature review
  - respond to reviewers
  - rebuttal
  - research gap
  - paper writing
  - refine abstract
---

# Sci-Review

Use this skill to produce structured literature-review writing and professional reviewer responses.

## Literature Review Structure

Use this four-part structure unless the user requests a different journal format:

1. **Introduction**: background, problem definition, gap identification, and contribution.
2. **Methodology**: taxonomy, method classes, comparison dimensions, and performance evidence.
3. **Challenges**: phenomenon, cause, and direction. Make the problem visible before proposing a route forward.
4. **Conclusion**: distilled insights and a future roadmap.

Prefer specific evidence over broad claims. Replace vague phrases such as "significantly better" with measured comparisons when data is available.

## Rebuttal Structure

For each reviewer point, use:

1. **Reviewer concern**: restate the concern accurately and neutrally.
2. **Response**: answer with evidence, clarification, or a limitation acknowledgement.
3. **Revision plan**: state the exact manuscript change, including section, table, figure, appendix, or experiment when possible.

Avoid adversarial phrasing such as "reviewer misunderstood" or "the reviewer is wrong". Use constructive language such as "we will clarify this point in the manuscript" or "we agree that additional evidence would improve the presentation".

## Validation

The skill includes a lightweight validator. Run from the `skills/sci-review/` directory:

```bash
# From the skills/sci-review/ directory:
python scripts/validate_review_output.py --case literature-review --output output.md
python scripts/validate_review_output.py --case rebuttal --output output.md
python scripts/validate_review_output.py --list-golden
```

The validator checks required section names and banned phrases. Golden cases live in `tests/golden_cases.json`; they define expected output features rather than exact wording.

## Best Practices

- Read the source literature, reviewer comments, or draft before rewriting.
- Preserve technical nuance. Do not invent experiments, results, baselines, or citations.
- Mark uncertainty explicitly when source evidence is missing.
- Keep tone professional, direct, and evidence-driven.
