---
name: gbif-api-integration
description: Guides optional GBIF REST API and pygbif integration for fetching source DwC-A or occurrence downloads, including base URLs, authentication, User-Agent, retries and 429 handling, occurrence search vs asynchronous downloads, download predicates, formats, download keys, DOI metadata, and output provenance.
---

# Skill: GBIF API Integration

## Purpose

Design and review optional GBIF API integration for fetching source data before the local DwC-A-to-geospatial conversion pipeline. The converter must still work with local DwC-A archives that did not come from GBIF.

## When to use

Use this skill when work involves:
- implementing or reviewing a GBIF REST/`pygbif` client;
- fetching GBIF occurrence downloads or metadata;
- deciding between occurrence search and asynchronous downloads;
- creating download requests, predicates, polling, download keys and DOI metadata;
- handling rate limits, retries, timeouts and credentials;
- deciding what GBIF metadata belongs in output provenance.

Do not use this skill for ordinary parsing of an already available non-GBIF DwC-A archive.

## Instructions

### 1. Start from official GBIF contracts

Check current official documentation before changing API contracts:
- API reference: `https://techdocs.gbif.org/en/openapi/`
- Occurrence API: `https://techdocs.gbif.org/en/openapi/v1/occurrence`
- API downloads: `https://techdocs.gbif.org/en/data-use/api-downloads`
- API introduction and clients: `https://techdocs.gbif.org/en/data-use/api-introduction`
- pygbif docs: `https://techdocs.gbif.org/en/data-use/pygbif`

Use `https://api.gbif.org/` as the public API base URL. Do not scrape `www.gbif.org` or rely on undocumented browser endpoints.

### 2. HTTP client rules

Every direct REST client must define:
- explicit connect/read timeouts;
- `User-Agent` containing a project URL or contact email;
- JSON `Accept`/`Content-Type` where applicable;
- bounded retries with exponential backoff and jitter for transient 5xx/network failures;
- `HTTP 429` handling using `Retry-After` when present;
- structured logging of endpoint, method, status, attempt count and elapsed time;
- no secrets in logs.

Most read-only GBIF API calls do not need authentication. Download creation and other protected operations use HTTP Basic Auth with the GBIF username, not email, and a password/token sourced from environment variables or secret storage.

### 3. pygbif is optional

GBIF clients simplify API use but may not cover all API methods or parameters.

Use `pygbif` when it cleanly exposes the required endpoint, parameters and metadata. Use direct REST when `pygbif` lacks a method/parameter, hides required metadata, lags behind official docs, or makes predicate construction/audit harder.

Record the chosen path (`pygbif` or REST), library version if applicable, endpoint, request parameters and response identifiers in output provenance metadata.

### 4. Occurrence search vs downloads

Use occurrence search for:
- small probes, counts, debugging and previews;
- checking parameter behavior before creating a larger download;
- limited paginated reads where volume is clearly bounded.

Use asynchronous downloads for:
- bulk occurrence retrieval;
- jobs likely to be long-running through search pagination;
- workflows needing DOI citation and reproducible source packages.

If the result is fed into this repository's converter, prefer downloading a supported archive/table format and then treating it as a source input with preserved provenance.

### 5. Download request rules

Download request JSON should include:
- `creator`;
- notification addresses where required;
- `format` (`SIMPLE_CSV`, `DWCA` or another officially supported format);
- a predicate tree using download API keys in `UPPER_CASE_WITH_UNDERSCORES`;
- `checklistKey` when occurrence taxonomy must be explicit.

Prefer `in` predicates for many values of the same field. Validate WKT geometry before `within` predicates. Persist the request JSON exactly enough to replay or audit it later.

### 6. Output provenance

For every GBIF interaction that affects generated outputs, preserve:
- endpoint or download URL;
- request parameters or predicate JSON;
- response identifiers such as download key, DOI, dataset key and occurrence keys;
- timestamps and final status;
- selected taxonomy/checklist key when relevant;
- client path (`pygbif` or REST) and version when applicable;
- warning/error summaries.

## Output expectations

When answering integration questions, return:

1. API path choice: `pygbif` or direct REST, with reason.
2. Endpoint(s), parameters and auth requirements.
3. Retry/rate-limit behavior.
4. Search vs download decision.
5. Output provenance fields to store.
6. Risks or docs to re-check.

## Checklist

- Is `User-Agent` explicit and contactable?
- Are timeouts, retries and `429` behavior defined?
- Is Basic Auth limited to operations that require it?
- Was `pygbif` coverage checked instead of assumed?
- Is occurrence search avoided for bulk extraction?
- Are download request JSON, key, DOI and status preserved?
