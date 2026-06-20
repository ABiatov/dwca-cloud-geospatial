# Prompt 15: GBIF Download DOI Citation In Viewer Provenance

## Required Skills

- `gbif-api-integration`: use the official GBIF download metadata API and
  avoid scraping GBIF web pages.
- `data-package-spec`: preserve DOI/citation provenance in `metadata/source.json`
  and `manifest.json`.
- `static-viewer-contract`: display citation in the Provenance panel with DOI
  links while keeping the viewer static.
- `planning-artifact-curator`: record accepted behavior, verification evidence
  and follow-up prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/output_format.md`
- `docs/viewer_contract.md`
- `docs/converter.md`
- `docs/developer_setup.md`
- `planning/decisions/`
- Latest relevant `session_logs/`
- `.codex/prompts/08_manifest_metadata_writers.md`
- `.codex/prompts/10_core_api_cli.md`
- `.codex/prompts/12_static_viewer.md`
- `.codex/prompts/14_demo_docs_hardening.md`
- `src/dwca_cloud_geospatial/bundle.py`
- `src/dwca_cloud_geospatial/conversion.py`
- `src/dwca_cloud_geospatial/cli.py`
- `src/dwca_cloud_geospatial/validation.py`
- `viewer/app.js`
- `tests/test_bundle_metadata.py`
- `tests/test_bundle_validation.py`
- `tests/test_conversion.py`
- `tests/test_cli.py`
- `tests/test_static_viewer.py`
- Example archive and generated bundle:
  - `examples/dwca/0038004-260519110011954.zip`
  - `examples/dwca/0038004-260519110011954/`
  - `examples/test_outputs/0038004-260519110011954/`
- Official GBIF docs to re-check before changing API behavior:
  - `https://www.gbif.org/citation-guidelines`
  - `https://techdocs.gbif.org/en/data-use/api-downloads`
  - `https://techdocs.gbif.org/en/openapi/v1/occurrence`

## Current Behavior To Preserve

- The converter is file-based: local DwC-A archive in, static bundle out.
- Generated bundles contain `metadata/source.json` and `manifest.json`.
- `metadata/source.json.gbif` already has nullable keys:
  `dataset_key`, `download_key`, `doi`, `citation`, `license`.
- `manifest.source` summarizes source DOI/citation from
  `dataset`, then `gbif`, then `obis`.
- The viewer already reads source metadata and displays Provenance rows.
- The viewer must not call GBIF, OBIS or any project backend. Any GBIF lookup
  must happen during conversion or through explicitly supplied metadata.
- Missing DOI/citation must remain valid for non-GBIF archives and GBIF
  archives where metadata is unavailable.

## Problem

For GBIF occurrence downloads, official citation guidance requires citing the
download DOI as a URL. For the sample download page:

`https://www.gbif.org/occurrence/download/0038004-260519110011954`

the page recommends:

`GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b`

The current converter can read EML metadata from the archive, but this sample
archive does not provide the final DOI citation in a way that fills
`metadata/source.json.gbif.doi` or `metadata/source.json.gbif.citation`.
Consequently the viewer has no citation to display.

## Goal

Add support to `dwca-cloud-geospatial convert` so generated bundles can carry
the official GBIF occurrence download DOI citation, and make the viewer render
that citation in Provenance with an active `doi.org` link.

## Design Requirements

- Use `metadata/source.json.gbif.doi` and `metadata/source.json.gbif.citation`
  for GBIF occurrence download DOI/citation metadata.
- Keep `metadata/source.json.dataset.citation` for general source/EML dataset
  citation metadata. Do not force GBIF download citations into `dataset` unless
  a deliberate schema decision updates `docs/output_format.md`.
- Preserve `manifest.source.doi` and `manifest.source.citation` fallback
  behavior so consumers can find citation metadata from the manifest summary.
- Prefer the official GBIF API over scraping `www.gbif.org`:
  `GET https://api.gbif.org/v1/occurrence/download/{download_key}`.
- Treat live GBIF API access as explicit/opt-in conversion-time enrichment, not
  hidden default behavior, unless project docs are deliberately changed to
  accept default network access.
- Allow a no-network/manual path for reproducible local conversion, for example
  by accepting explicit GBIF DOI/citation/download-key metadata through CLI
  options and/or `ConversionOptions`.
- If direct REST is implemented, define:
  - explicit connect/read timeout;
  - contactable `User-Agent`;
  - JSON `Accept` header;
  - bounded retries with exponential backoff and jitter for transient network
    or 5xx failures;
  - `HTTP 429` handling using `Retry-After` when present;
  - structured warnings when enrichment fails but conversion can continue;
  - no secrets in logs.
- Read-only GBIF download metadata lookup must not require authentication.
- Do not add download-creation flows, GBIF credentials, occurrence search or
  taxonomy matching.

## Suggested Implementation Shape

1. Add a small GBIF download metadata module or helper, for example
   `src/dwca_cloud_geospatial/gbif.py`, with a pure parser/formatter core and
   a small optional HTTP client.
2. Extract or infer `download_key` from local archive metadata where possible:
   - existing `http://rs.gbif.org/terms/1.0/downloadKey` terms;
   - `metadata.xml` / EML additional metadata such as
     `<gbif><citation identifier="0038004-260519110011954">...`;
   - GBIF download URLs like
     `https://api.gbif.org/v1/occurrence/download/request/{key}.zip`;
   - the input archive filename or directory name when it exactly matches the
     GBIF download-key pattern.
3. Add explicit conversion options for GBIF citation metadata. Choose names
   consistent with the existing code, but cover these use cases:
   - no network/default local conversion;
   - manually supplied `download_key`, DOI and citation;
   - opt-in API enrichment from inferred or supplied `download_key`.
4. Update `build_source_metadata()` / metadata writing so:
   - local EML/source values still populate `dataset.*` and rights fields;
   - `gbif.download_key`, `gbif.doi` and `gbif.citation` are filled when
     explicit or enriched GBIF download metadata is available;
   - `gbif.citation` uses the official recommended form when API fields are
     sufficient, including DOI as `https://doi.org/...`;
   - non-GBIF archives keep nullable GBIF fields as `null`.
5. Update `manifest.source` only through the existing source summary path, not
   by duplicating citation logic in conversion or CLI handlers.
6. Update the static viewer Provenance rendering:
   - render DOI rows as links to `https://doi.org/{doi}` when the value is a
     DOI string or DOI URL;
   - render DOI URLs inside Citation values as active links;
   - build DOM nodes safely instead of using `innerHTML`;
   - keep plain text for citation text outside the DOI URL;
   - preserve `target="_blank"` and `rel="noopener noreferrer"` on external
     links.
7. Update docs so users understand:
   - how to run conversion without network access;
   - how to pass explicit GBIF DOI/citation metadata;
   - how to enable API enrichment if implemented;
   - where citation metadata appears in `metadata/source.json`, `manifest.json`
     and the viewer.

## Tests To Add Or Update

- Unit tests for extracting a GBIF download key from sample EML/additional
  metadata and download URLs.
- Unit tests for normalizing DOI values:
  - `10.15468/dl.3xbk5b`;
  - `https://doi.org/10.15468/dl.3xbk5b`;
  - absent or malformed values.
- Unit tests for formatting the GBIF citation string from API-like metadata.
- Conversion/bundle metadata tests showing `metadata/source.json.gbif.doi` and
  `metadata/source.json.gbif.citation` populated from explicit/manual metadata
  without network.
- If API enrichment is implemented, mock the HTTP client. Do not make tests
  depend on live GBIF network access.
- Validation tests should continue accepting nullable GBIF/OBIS fields and
  should not require DOI/citation for all bundles.
- Static viewer tests should assert that:
  - `viewer/app.js` contains DOI link rendering for Provenance;
  - citation DOI URLs are rendered as links safely;
  - missing citation values remain omitted without error.
- CLI tests should cover the selected command-line surface, including:
  - manual citation/DOI arguments if added;
  - opt-in enrichment flag behavior using a mocked client or lower-level core
    function, not live network.

## Acceptance Criteria

- Running `dwca-cloud-geospatial convert` with the accepted no-network/manual
  metadata path can produce:

  ```json
  {
    "gbif": {
      "download_key": "0038004-260519110011954",
      "doi": "10.15468/dl.3xbk5b",
      "citation": "GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b"
    }
  }
  ```

- `manifest.source.doi` and `manifest.source.citation` expose the same GBIF
  DOI/citation through the existing summary fallback when dataset/OBIS values
  are absent.
- The viewer Provenance panel displays the citation and the DOI URL is an
  active link to `https://doi.org/10.15468/dl.3xbk5b`.
- The viewer remains fully static and performs no GBIF API requests.
- Non-GBIF archives and GBIF archives without DOI metadata still convert and
  validate with nullable DOI/citation fields.
- Automated tests cover metadata generation, viewer link rendering logic and
  CLI/core option behavior without live network dependency.
- Documentation describes the citation workflow and cites the official GBIF
  citation guidelines.

## Constraints

- Do not scrape GBIF download web pages.
- Do not require live network access for ordinary conversion.
- Do not require GBIF credentials.
- Do not add a backend service.
- Do not make DOI/citation mandatory for all bundles.
- Do not duplicate manifest/source summary logic in CLI handlers.
- Do not use `innerHTML` for citation rendering.
- Preserve safe static-hosting behavior and existing viewer no-map-layer states.

## Required Session Log

Write `session_logs/YYYY-MM-DD_15_gbif_doi_citation.md` with:

- Implemented CLI/API option names and defaults.
- GBIF download key inference rules.
- DOI/citation normalization and formatting behavior.
- Network behavior, if any, including timeout/retry and failure semantics.
- Source metadata and manifest fields populated.
- Viewer DOI link behavior.
- Test commands run and results.
- Any docs updated.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

- Update `.codex/prompts/14_demo_docs_hardening.md` if final demo/docs
  hardening should mention the GBIF citation workflow.
- Update future prompts if conversion option names, source metadata schema or
  viewer provenance behavior changes.
