# Prompt 14: GBIF Download DOI Citation

Date: 2026-06-20

## Implemented Option Names And Defaults

- Core API: added `dwca_cloud_geospatial.gbif.GbifDownloadOptions`.
- `ConversionOptions.gbif` defaults to `GbifDownloadOptions()`, which means:
  - `download_key=None`;
  - `doi=None`;
  - `citation=None`;
  - `enrich=False`;
  - no GBIF network access during ordinary conversion.
- CLI flags:
  - `--gbif-download-key`;
  - `--gbif-doi`;
  - `--gbif-citation`;
  - `--gbif-enrich`.
- GUI follow-up: the GUI now exposes a `GBIF DOI citation lookup` checkbox
  that maps to `GbifDownloadOptions(enrich=True)`, equivalent to CLI
  `--gbif-enrich`. It is selected by default; clearing it keeps GUI conversion
  no-network unless explicit GBIF metadata is supplied through the Python API.

## GBIF Download Key Inference Rules

The converter resolves the GBIF occurrence download key from:

1. explicit `GbifDownloadOptions.download_key` / `--gbif-download-key`;
2. source occurrence rows or streaming source-value summaries containing
   `http://rs.gbif.org/terms/1.0/downloadKey` or
   `http://rs.gbif.org/terms/1.0/download_key`;
3. declared EML/additional metadata with GBIF citation identifiers or GBIF
   occurrence download URLs;
4. input archive filename or directory name when it exactly matches the GBIF
   download-key pattern, with an optional `.zip` suffix.

Malformed explicit download keys raise `ConversionError`. Missing inferred
keys remain valid and nullable unless API enrichment is requested, in which
case a structured non-fatal warning is recorded.

## DOI And Citation Behavior

- `normalize_doi()` accepts:
  - `10.15468/dl.3xbk5b`;
  - `https://doi.org/10.15468/dl.3xbk5b`;
  - `doi:10.15468/dl.3xbk5b`.
- The stored DOI value is a bare DOI string, for example
  `10.15468/dl.3xbk5b`.
- Malformed explicit DOI values raise `ConversionError`.
- API-like metadata with `doi` and `created` formats a GBIF occurrence
  download citation as:

```text
GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b
```

- Manually supplied citation text is preserved as provided.
- GBIF download citation metadata stays in `metadata/source.json.gbif`; it is
  not forced into `metadata/source.json.dataset`.

## Network Behavior

- Ordinary conversion does not contact GBIF, OBIS or any project backend.
- `--gbif-enrich` / `GbifDownloadOptions(enrich=True)` opts in to a read-only
  direct REST lookup:

```text
GET https://api.gbif.org/v1/occurrence/download/{download_key}
```

If that JSON endpoint does not provide DOI/citation values, enrichment also
uses the citation endpoint:

```text
GET https://api.gbif.org/v1/occurrence/download/{download_key}/citation
```

The citation endpoint response is normalized enough to preserve a canonical
`https://doi.org/...` DOI URL, and the bare DOI is extracted into
`metadata/source.json.gbif.doi`, `manifest.source.doi` and
`metadata/processing.json.source_provenance.gbif.doi`.

- Authentication is not required.
- The client sets:
  - JSON or text `Accept` header, depending on endpoint;
  - contactable project `User-Agent`;
  - explicit connect/read timeout option values;
  - bounded retries;
  - exponential backoff with jitter for transient failures;
  - HTTP 429 handling using numeric `Retry-After` when present.
- Lookup failures do not fail conversion. They add a structured warning such
  as `gbif_download_metadata_lookup_failed` to
  `metadata/processing.json.warnings`.
- No download creation, GBIF credentials, occurrence search or taxonomy
  matching were added.

## Source Metadata And Manifest Fields

Manual no-network conversion can now produce:

```json
{
  "gbif": {
    "dataset_key": "cd6e21c8-9e8a-493a-8a76-fbf7862069e5",
    "download_key": "0038004-260519110011954",
    "doi": "10.15468/dl.3xbk5b",
    "citation": "GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b",
    "license": null
  }
}
```

`manifest.source.doi`, `manifest.source.citation` and
`manifest.source.gbif_download_key` continue to use the existing source
summary fallback path. Dataset-level EML citation fields still take priority
over GBIF and OBIS fields in `manifest.source`.

`metadata/processing.json.source_provenance.gbif` repeats the resolved GBIF
`download_key`, `doi`, `citation` and `license` values for processing audit.

Nullable GBIF/OBIS fields remain valid for non-GBIF archives and GBIF
archives without DOI/citation metadata.

## Viewer DOI Link Behavior

- The static viewer still reads generated static files only.
- It does not call GBIF, OBIS or any backend to fill citation fields.
- Provenance DOI rows render as external `https://doi.org/{doi}` links when
  the source value is a bare DOI or DOI URL.
- DOI URLs embedded inside citation text render as active external links while
  surrounding citation text remains text nodes.
- Citation rendering uses DOM node creation and does not use `innerHTML`.
- Links use `target="_blank"` and `rel="noopener noreferrer"`.
- Missing DOI/citation values remain omitted without error.

## Docs Updated

- `docs/converter.md`: manual no-network citation flags, opt-in enrichment,
  API endpoint, citation-guideline links and GUI checkbox behavior.
- `docs/output_format.md`: GBIF occurrence download DOI/citation field
  semantics and viewer DOI link behavior.
- `docs/viewer_contract.md`: Provenance DOI/citation link behavior and static
  no-backend boundary.
- `README.md`, `docs/developer_setup.md`,
  `docs/development_plan.md` and
  `planning/decisions/ADR-001-mvp-boundaries-and-interfaces.md`: optional
  conversion-time GBIF DOI/citation lookup boundary and GUI default checkbox
  behavior.
- `.codex/prompts/13_tkinter_gui.md`: GUI default checkbox behavior for GBIF
  DOI/citation lookup.
- `.codex/prompts/15_demo_docs_hardening.md`: Prompt 14 option names and
  provenance/viewer behavior to preserve.

## Verification Evidence

Official GBIF docs rechecked before implementation:

- `https://www.gbif.org/citation-guidelines`
- `https://techdocs.gbif.org/en/data-use/api-downloads`
- `https://techdocs.gbif.org/en/openapi/v1/occurrence`

Manual no-network sample conversion:

```bash
.venv/bin/dwca-cloud-geospatial convert examples/dwca/0038004-260519110011954.zip /private/tmp/dwca-gbif-citation-bundle --format geoparquet --overwrite --gbif-download-key 0038004-260519110011954 --gbif-doi 10.15468/dl.3xbk5b --gbif-citation "GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b"
```

Result: conversion succeeded with `1168` accepted records and `0` rejected
records. PyArrow emitted sandbox-related `sysctlbyname` CPU feature warnings,
but the bundle was written.

Generated bundle verification:

```bash
.venv/bin/python -c "import json; p='/private/tmp/dwca-gbif-citation-bundle'; s=json.load(open(p+'/metadata/source.json')); m=json.load(open(p+'/manifest.json')); print(json.dumps({'gbif': s['gbif'], 'manifest_source': m['source']}, indent=2, sort_keys=True))"
```

Result: `metadata/source.json.gbif.doi`,
`metadata/source.json.gbif.citation`, `manifest.source.doi` and
`manifest.source.citation` contained the expected DOI/citation values.

Validation:

```bash
.venv/bin/dwca-cloud-geospatial validate /private/tmp/dwca-gbif-citation-bundle
```

Result: `passed_with_warnings`, `Errors: 0`, `Warnings: 1`. The warning was
the known optional Pyogrio/GDAL GeoParquet reader skip.

Automated verification:

```bash
.venv/bin/python -m compileall -q src tests
```

Result: passed.

```bash
.venv/bin/python -m pytest tests -q
```

Result: `92 passed, 1 skipped`.

```bash
git diff --check
```

Result: passed.

## Prompt Updates

- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/15_demo_docs_hardening.md`.

## Follow-Up: Citation Endpoint Enrichment Fix

After implementation review, live `--gbif-enrich` conversion still left DOI
and citation as `null` when the GBIF JSON metadata endpoint did not expose
those fields. Fixed enrichment to call:

```text
GET https://api.gbif.org/v1/occurrence/download/{download_key}/citation
```

when DOI/citation are not already supplied manually. The citation endpoint
returns the official string, for example:

```text
GBIF.org (10 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.9t5b2m
```

Implementation details:

- The citation endpoint requires a compatible Accept header; strict
  `Accept: text/plain` returned HTTP 406 in live verification, while
  `Accept: text/plain, */*` succeeded.
- DOI is extracted from the citation string and stored as a bare DOI.
- Citation text is normalized so accidental `https: //doi.org/...` spacing is
  corrected to `https://doi.org/...`.
- Resolved GBIF download metadata is now written to
  `metadata/processing.json.source_provenance.gbif` as well as
  `metadata/source.json.gbif` and `manifest.source`.

Live verification:

```bash
curl -fsS https://api.gbif.org/v1/occurrence/download/0049663-260519110011954/citation
```

Result:

```text
GBIF.org (10 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.9t5b2m
```

```bash
.venv/bin/dwca-cloud-geospatial convert examples/dwca/0038004-260519110011954.zip /private/tmp/dwca-gbif-enrich-citation-endpoint --format geoparquet --overwrite --gbif-download-key 0049663-260519110011954 --gbif-enrich
```

Result: conversion succeeded with `1168` accepted records and `0` rejected
records. `metadata/source.json.gbif`, `manifest.source` and
`metadata/processing.json.source_provenance.gbif` all contained:

```json
{
  "doi": "10.15468/dl.9t5b2m",
  "citation": "GBIF.org (10 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.9t5b2m"
}
```

Validation:

```bash
.venv/bin/dwca-cloud-geospatial validate /private/tmp/dwca-gbif-enrich-citation-endpoint
```

Result: `passed_with_warnings`, `Errors: 0`, `Warnings: 1`. The warning was
the known optional Pyogrio/GDAL GeoParquet reader skip.

Automated verification:

```bash
.venv/bin/python -m pytest tests -q
```

Result: `94 passed, 1 skipped`.

```bash
.venv/bin/python -m compileall -q src tests
git diff --check
```

Result: passed.
