# Progress

## 2026-07-28 - Task: Confirm sci-search quality improvement design

### What was done

- Confirmed the four-source default search strategy and the bounded set of
  search-quality fixes.
- Added the approved design covering CLI behavior, source-specific queries,
  post-processing, deduplication, failure handling, testing, and documentation.
- Created the `dev` branch from `main` at commit `1a65700`.

### Testing

- Verified the worktree was clean before creating the branch.
- Reviewed the design for placeholders, contradictions, ambiguous behavior,
  scope expansion, and credential exposure.
- Ran `git diff --check` for whitespace and patch-format errors.

### Notes

- `docs/superpowers/specs/2026-07-28-sci-search-quality-design.md` - records the
  approved search-quality design and implementation boundaries.
- `progress.md` - records this design-stage repository change.
- Rollback point: `main` commit `1a65700`; run `git switch main` to return to
  the repository state before this task.

## 2026-07-28 - Task: Plan sci-search quality implementation

### What was done

- Converted the approved sci-search design into a five-task implementation
  plan with test-first steps, exact interfaces, verification commands, commit
  checkpoints, documentation work, and a bounded live API check.
- Kept the implementation within the existing sequential fetcher architecture
  and the previously approved scope.

### Testing

- Checked every approved design requirement against an implementation task.
- Reviewed the plan for placeholder text, contradictory signatures, uncovered
  requirements, credential exposure, and out-of-scope work.
- Confirmed the pre-implementation sci-search unit baseline passes 3 tests.
- Confirmed the focused Ruff `F,E9` rules and Python compilation pass; the
  existing files have 53 unrelated full-Ruff findings, so the plan records the
  scoped static-analysis gate instead of expanding into a file-wide cleanup.
- Ran `git diff --check` for whitespace and patch-format errors.

### Notes

- `docs/superpowers/plans/2026-07-28-sci-search-quality.md` - provides the
  executable test-driven implementation plan.
- `progress.md` - records the planning-stage repository change.
- Rollback point: commit `9849e59`; run
  `git switch -c sci-search-plan-base 9849e59` to create a recovery branch
  before the plan was added.

## 2026-07-28 - Task: Improve sci-search default strategy and result quality

### What was done

- Changed the default search to Web of Science, Springer Metadata, Springer
  Open Access, and Scopus in priority order while retaining explicit access to
  arXiv, PubMed, Semantic Scholar, and OpenAlex.
- Added inclusive year bounds, recent/relevance sorting, corrected WoS citation
  parsing, provider-specific queries, and DOI/title cross-source identity.
- Updated English, Chinese, skill, and website documentation for the revised
  search contract.

### Testing

- `conda run -n aut-sci-write python -m unittest discover -s tests -p
  "test_*.py" -v` - 25 tests passed.
- `conda run --no-capture-output -n aut-sci-write python -m ruff check
  --select 'F,E9' skills/sci-search/sci_search.py tests/test_sci_search.py` -
  passed; 53 pre-existing full-Ruff findings remain outside this task.
- `conda run -n aut-sci-write python -m compileall -q
  skills/sci-search/sci_search.py tests/test_sci_search.py` - passed.
- CLI help exposed `--year-from`, `--year-to`, and
  `--sort {relevance,recent}`; the stale seven-source claim scan returned no
  matches.
- Bounded live `GNSS NLOS` query attempted WoS, Springer Metadata, Springer
  Open Access, and Scopus in that order and returned 6 results: 2 WoS, 2
  Springer Metadata, 1 Springer Open Access, and 1 Scopus. All results were
  dated 2026 and the final order satisfied recent-first sorting. No provider
  error or credential exposure was observed.
- `git diff --check 9849e59..HEAD` and the working-tree whitespace check passed.

### Notes

- `skills/sci-search/sci_search.py` - revised source orchestration, provider
  queries, citation parsing, result processing, and cache identity.
- `tests/test_sci_search.py` - added deterministic coverage for the revised
  search contract.
- `skills/sci-search/SKILL.md` - documented default sources and new CLI options.
- `README.md` - updated English and Chinese search descriptions.
- `docs/index.html` - updated the public sci-search feature description.
- `progress.md` - recorded implementation and verification evidence.
- Rollback point: commit `9849e59`; run `git switch main` to return to the
  unchanged main branch, or `git switch -c sci-search-before-fix 9849e59` to
  create a recovery branch at the pre-implementation state.

## 2026-07-30 - Task: Confirm sci-search result enrichment design

### What was done

- Confirmed the bounded design for complete author presentation, conservative
  cross-source field enrichment, OpenAlex abstract reconstruction, and a live
  Markdown report check.
- Kept the first-seen provider as the primary record so existing provider
  priority and result ordering remain stable.

### Testing

- Reproduced the three current defects: duplicate abstracts are discarded,
  author output is truncated after three names, and OpenAlex abstracts are
  always empty.
- Confirmed the existing repository baseline passes 25 tests.
- Reviewed the design for placeholders, contradictions, ambiguity, scope
  expansion, and credential handling.

### Notes

- `docs/superpowers/specs/2026-07-30-sci-search-result-enrichment-design.md` -
  records the approved merge, OpenAlex parsing, presentation, and verification
  contracts.
- `progress.md` - records this design-stage repository change.
- Rollback point: commit `32fe388`; run
  `git switch -c sci-search-before-result-enrichment-design 32fe388` to create
  a recovery branch at the state before this design was added.

## 2026-07-30 - Task: Align sci-search result enrichment design

### What was done

- Aligned the written design with the approved behavior for retaining the
  longer available abstract and recording its provider.
- Made merged provider provenance and the generated report path explicit.

### Testing

- Rechecked the design for placeholders, contradictions, ambiguous merge
  behavior, scope expansion, and report-path consistency.
- Confirmed the corrected contract preserves provider priority while allowing
  only the approved abstract and author completeness exceptions.

### Notes

- `docs/superpowers/specs/2026-07-30-sci-search-result-enrichment-design.md` -
  clarifies abstract selection, abstract provenance, source rendering, and the
  report destination.
- `progress.md` - records this design correction.
- Rollback point: commit `cba73af`; run
  `git switch -c sci-search-before-design-alignment cba73af` to create a
  recovery branch before this correction.
