---
id: validate-output-bundle-playbook
status: candidate
applies_to:
  - output bundle
  - validation
  - metadata/provenance
  - static viewer contract
sources:
  - docs/knowledge_base/topics/validation_and_quality.md
  - docs/knowledge_base/topics/geoparquet_output.md
  - examples/code/geoparquet/
  - examples/code/geoparquet-io/
---

# Validate Output Bundle

## Goal

Confirm that generated files are internally consistent, readable by expected tools, and safe to publish as static assets.

The implemented core entry point is
`dwca_cloud_geospatial.validation.validate_output_bundle(bundle_root)`. It
returns `BundleValidationResult` with `status`, `errors`, `warnings`,
`checks`, `checked_files`, `has_errors`, `skipped_checks`, `to_dict()` and
`to_json()`.

## Steps

1. Read the output manifest.
2. Confirm every declared file exists.
3. Confirm every declared checksum matches when `sha256` is present, and
   confirm ungenerated files are omitted from `manifest.files`.
4. Validate source metadata and conversion summary. Missing EML, GBIF or OBIS
   values are valid nulls, not validation failures.
5. Check Parquet and GeoParquet files open with PyArrow.
6. Validate GeoParquet metadata and geometry data with required PyArrow checks.
7. Run optional GeoParquet-aware checks when available: `geoparquet-io` first,
   DuckDB second, and Pyogrio/GDAL as best-effort reader checks. Report missing
   optional tools as warnings or skipped checks when PyArrow validation passes.
8. Confirm row counts match conversion reports.
9. If `reports/rejected_records.csv` is present, validate required columns and
   reconcile its row count. If no records are rejected, confirm the report is
   absent and omitted from `manifest.files`.
10. If raw core or extension table exports are generated, confirm extension relationship keys can join to core keys.
11. Validate FlatGeobuf or PMTiles files if present. FlatGeobuf validation is
   dependency-dependent: use the documented `.[dev,flatgeobuf]` stack when
   available, and report skipped geospatial file-inspection checks as warnings
   rather than failing otherwise.
12. Check viewer manifest paths, bounds, layers, and field names.
13. Confirm normalized output fields use snake_case project names and do not
    emit parser/source camelCase terms; `class` is the output field, not
    Python attribute `class_`.
14. Validate `quality_flags` as nullable `|`-delimited strings and split them
    for exact-token checks.
15. Reconcile `warning_count`, `warnings`, and `type_conversion_failures` in
    processing metadata.
16. Reconcile FlatGeobuf writer warnings recorded in processing metadata,
    including non-fatal `large_indexed_flatgeobuf_write` warnings for indexed
    writes over large accepted record sets.
17. Return or save a validation result with errors, warnings, skipped checks
    and tool versions.

Current implementation notes:

- Single-file GeoParquet output at `data/occurrences.parquet` is validated
  with required PyArrow checks, including `bbox` covering schema/content when
  that large-output column is present.
- Partitioned GeoParquet dataset validation remains future work because
  partitioned output is deferred and rejected when requested.
- FlatGeobuf validation checks projection fields and counts through
  Pyogrio/GDAL when available. Row-level FlatGeobuf `quality_flags` validation
  depends on local geospatial table reader support.
- Optional `geoparquet-io`, DuckDB and Pyogrio/GDAL checks should be treated
  as structured warnings or skipped checks when required PyArrow validation
  passes.

## Acceptance Evidence

- Validation fails on missing files.
- Validation fails on checksum mismatches when `sha256` is present.
- Validation fails or warns on invalid GeoParquet metadata.
- Validation treats PyArrow GeoParquet checks as required and
  `geoparquet-io`, DuckDB and Pyogrio/GDAL checks as optional
  dependency-dependent checks.
- Validation reports skipped/invalid coordinate counts.
- Validation catches malformed `quality_flags` tokens or delimiter usage.
- Validation accepts missing GBIF/OBIS source metadata values as null.
- Validation confirms conditional rejected-report presence and row counts.
- Validation reconciles warning counts with processing warnings.
- Validation treats `large_indexed_flatgeobuf_write` as a non-fatal processing
  warning unless a later accepted core-conversion policy changes it.
- Validation result is available as portable JSON through
  `BundleValidationResult.to_json()` and can later be surfaced by CLI or GUI.

## Related Topics

- `../topics/validation_and_quality.md`
- `../topics/geoparquet_output.md`
- `../topics/pmtiles_viewer.md`
