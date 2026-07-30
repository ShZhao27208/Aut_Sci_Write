# Sci-Search Result Enrichment Design

## Goal

Improve the final search report without changing provider priority or result
ordering:

- show every author returned for a paper;
- preserve the first-seen provider record while enriching it with approved
  fields from duplicate records returned by later providers;
- reconstruct OpenAlex abstracts from `abstract_inverted_index`;
- verify the behavior with deterministic tests and a bounded live
  `GNSS NLOS` report.

## Scope

The implementation is limited to
`skills/sci-search/sci_search.py`, its focused tests, user-facing search
documentation, the generated test report, and the required progress log.

It will not add providers, change default providers, change provider query
syntax, change result ranking, alter API credentials, or introduce a new
output format.

## Result Merge Contract

`dedupe_results` continues to preserve first-seen order. When
`papers_match` identifies a duplicate, the first record remains the primary
record.

For scalar metadata such as `doi`, `journal`, `year`, `url`, and
`times_cited`, a later duplicate fills the field only when the primary value is
missing. A later value never overwrites an existing primary value.

For `abstract`, a later duplicate fills a missing primary abstract. When both
records contain an abstract, the longer non-empty abstract is retained because
providers can return different preview lengths. The record stores
`abstract_source` so the report identifies which provider supplied the retained
abstract.

For `authors`, the non-empty list containing more author names is retained.
This addresses providers that return abbreviated or incomplete author lists
without attempting unreliable name-by-name reconciliation.

The merged record carries an ordered `sources` list containing every provider
that contributed a duplicate record. The original `source` value remains
unchanged for compatibility. Markdown output renders the ordered source list
with the existing human-readable provider labels.

The merge operates on copied result dictionaries so post-processing does not
mutate raw provider results supplied by callers.

## OpenAlex Abstract Reconstruction

OpenAlex returns abstracts as a mapping from tokens to one or more integer word
positions. A focused helper will:

1. return an empty string when the index is absent or empty;
2. flatten every token-position pair;
3. sort pairs by integer position;
4. join tokens with a single space.

The reconstructed value becomes the OpenAlex paper's `abstract`. Existing
OpenAlex title, author, DOI, journal, URL, and citation handling remains
unchanged.

## Markdown Presentation

The authors line joins the complete stored author list and no longer truncates
after three names or appends `et al.`.

Source labels use the merged `sources` list when present and fall back to the
existing `source` field for older records. When an abstract is present, output
also renders its human-readable `abstract_source`. All other report fields and
the current 300-character abstract preview remain unchanged.

## Error Handling

Malformed or absent OpenAlex abstract data produces an empty abstract rather
than failing the whole provider search. The helper ignores unusable positions
while preserving valid token-position pairs.

Result enrichment is conservative: lower-priority providers cannot replace
existing primary metadata except when they provide a longer abstract or a more
complete author list. Both exceptions are visible through the retained source
metadata.

## Testing

Deterministic regression tests will cover:

- all authors are rendered without `et al.`;
- a later duplicate fills a missing abstract while preserving the primary
  source and citation count;
- the longer of two non-empty abstracts is retained with the correct abstract
  source;
- a longer duplicate author list replaces an incomplete primary list;
- merged source labels are rendered in provider order;
- OpenAlex inverted indexes reconstruct repeated tokens in position order;
- missing or empty OpenAlex indexes produce an empty abstract.

The red-green cycle will first run the new focused tests against current code
and confirm failures for the expected missing behavior. After implementation,
the focused test module, the full repository test suite, scoped Ruff checks,
Python compilation, and whitespace checks will run.

Finally, the CLI will perform a no-cache live query for `GNSS NLOS`, inclusive
years 2022 through 2026, recent-first ordering, and write a bounded Markdown
report to `docs/reports/2026-07-30-gnss-nlos-search.md`. Verification will
confirm the file exists, contains results, renders complete author lists,
identifies contributing and abstract sources, and includes abstracts when
returned by the contributing providers. Live provider availability is reported
as observed evidence rather than treated as a deterministic unit-test
condition.
