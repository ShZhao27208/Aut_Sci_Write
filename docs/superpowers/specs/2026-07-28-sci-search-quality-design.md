# Sci-Search Search Quality Design

Date: 2026-07-28
Status: Approved for implementation planning

## Objective

Improve the default `sci-search` result quality and make recent-literature
searches predictable without expanding the project into a new search
framework.

The default search must query these sources in order:

1. Web of Science
2. Springer Nature Metadata
3. Springer Nature Open Access
4. Scopus

arXiv, PubMed, Semantic Scholar, and OpenAlex remain available only through an
explicit `--source` selection and do not run as part of the default search.

## Scope

The implementation will:

- change the default source set and execution order;
- add optional year bounds and a result sort mode;
- correct Web of Science citation parsing;
- stop forcing multiword Springer and Scopus queries into exact phrases;
- deduplicate cross-source results by DOI first and normalized title second;
- use the same paper identity rules when adding new cache entries;
- update automated tests and user-facing documentation; and
- verify the configured APIs with one small live search after unit tests pass.

The implementation will not:

- add IEEE Xplore to `sci-search`;
- expand or replace the static journal metrics database;
- remove the four non-default source implementations;
- migrate or rewrite existing library cache files; or
- introduce concurrent API requests or a new search adapter framework.

## Command-Line Contract

`--source all` remains the default for compatibility, but "all" means the
four enabled default sources listed above. The existing individual values
`arxiv`, `pubmed`, `wos`, `springer`, `springer_meta`, `springer_oa`, `scopus`,
`semantic_scholar`, and `openalex` remain valid. `--source springer` continues
to run Metadata followed by Open Access.

The command adds:

- `--year-from YYYY`: optional inclusive lower publication-year bound;
- `--year-to YYYY`: optional inclusive upper publication-year bound; and
- `--sort relevance|recent`: result ordering, defaulting to `recent`.

Each year must contain four digits. Either bound may be used alone. When both
are present, `--year-from` must not be greater than `--year-to`. Invalid values
are rejected by the CLI before any network request.

`--limit` remains a per-source limit. A default search can therefore return up
to four times the limit before deduplication.

## Source Queries

The existing fetcher classes remain responsible for source-specific request
construction and response parsing.

### Web of Science

- Keep topic search as `TS=(<query>)`.
- Append an inclusive `PY=(start-end)` condition when a year bound is
  supplied. A missing lower bound uses 1900; a missing upper bound uses the
  current calendar year.
- Use `sortField=PY+D` for `recent`.
- Leave the API's relevance order unchanged for `relevance`.
- Read the citation count from the Starter API `citations[].count` structure.
  Missing citation information remains an empty value.

### Springer Metadata and Open Access

- Remove the quotes that currently force the entire user query to be an exact
  phrase.
- Add `datefrom:YYYY-01-01` and `dateto:YYYY-12-31` constraints to the query
  for the supplied inclusive year bounds.
- Preserve the provider's result order for `relevance`.
- Apply local year validation after parsing because the two Springer endpoints
  can differ in date behavior.

### Scopus

- Build `TITLE-ABS-KEY(<query>)` without automatically quoting the full query.
  User-supplied operators or explicit quotes remain part of the query.
- Add inclusive `PUBYEAR` constraints for supplied year bounds.
- Request cover-date descending order for `recent` and relevance order for
  `relevance`.

### Explicit Non-Default Sources

arXiv, PubMed, Semantic Scholar, and OpenAlex continue to use their current
query behavior. When selected explicitly, the shared post-processing stage
still applies requested year bounds, sorting, and deduplication.

## Post-Processing

All fetched papers pass through one shared post-processing sequence:

1. Reject papers with a parseable year outside the requested inclusive range.
   Papers without a parseable year are also rejected when a year bound is
   active.
2. Deduplicate records while preserving the highest-priority record.
3. Apply the requested final ordering.

For `recent`, results are ordered by publication year descending. Ties retain
source priority and provider order. For `relevance`, source priority and each
provider's returned order are preserved because relevance scores are not
comparable across APIs.

Source priority is the default execution order. For an explicitly selected
single source, provider order is preserved.

## Paper Identity

A DOI is normalized by trimming whitespace, removing a leading `doi:` or
`https://doi.org/`, and comparing case-insensitively.

Two records that both provide a DOI are duplicates only when their normalized
DOIs match. When either record lacks a DOI, the normalized title is the
fallback comparison. Title normalization lowercases text, replaces punctuation
with spaces, and collapses whitespace. Records with neither a DOI nor a usable
title are not collapsed.

The first matching record is retained. Later records are not merged. New
library-cache writes use the same identity rules, but existing duplicate cache
entries are not migrated.

## Failure Behavior

In a default search, a missing API key or one failed source is reported and the
remaining sources continue. An explicitly requested key-gated source retains
the current clear configuration error and exits without searching unrelated
sources.

Error messages must continue to redact API keys. No test fixture, generated
URL assertion, documentation example, or progress entry may contain a real
credential.

## Verification

Unit tests will cover:

- default source selection and exact execution order;
- explicit access to each non-default source;
- CLI year validation;
- source-specific query parameters for year and sort options;
- non-exact multiword Springer and Scopus queries;
- Web of Science citation parsing;
- inclusive post-fetch year filtering;
- `recent` and `relevance` ordering;
- DOI normalization and title-fallback deduplication; and
- cache identity behavior across sources.

After unit tests and the repository test suite pass, one small live query will
exercise WoS, Springer Metadata, Springer Open Access, and Scopus with a bounded
year range. The live check is diagnostic rather than a deterministic automated
test because provider availability and result sets can change.

## Documentation

Update `skills/sci-search/SKILL.md`, both language sections in `README.md`, and
the relevant `docs/index.html` copy so they describe the four-source default,
explicit optional sources, year bounds, and sort behavior.
