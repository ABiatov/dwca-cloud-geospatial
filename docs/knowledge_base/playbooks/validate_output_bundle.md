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

## Steps

1. Read the output manifest.
2. Confirm every declared file exists.
3. Validate source metadata and conversion summary.
4. Check Parquet and GeoParquet files open with PyArrow.
5. Validate GeoParquet metadata and geometry data with required PyArrow checks.
6. Run optional GeoParquet-aware checks when available: `geoparquet-io` first,
   DuckDB second, and Pyogrio/GDAL as best-effort reader checks. Report missing
   optional tools as warnings or skipped checks when PyArrow validation passes.
7. Confirm row counts match conversion reports.
8. If raw core or extension table exports are generated, confirm extension relationship keys can join to core keys.
9. Validate FlatGeobuf or PMTiles files if present. FlatGeobuf validation is
   dependency-dependent: use the documented `.[dev,flatgeobuf]` stack when
   available, and report skipped geospatial file-inspection checks as warnings
   rather than failing otherwise.
10. Check viewer manifest paths, bounds, layers, and field names.
11. Confirm normalized output fields use snake_case project names and do not
    emit parser/source camelCase terms; `class` is the output field, not
    Python attribute `class_`.
12. Validate `quality_flags` as nullable `|`-delimited strings and split them
    for exact-token checks.
13. Reconcile `warning_count`, `warnings`, and `type_conversion_failures` in
    processing metadata.
14. Reconcile FlatGeobuf writer warnings recorded in processing metadata,
    including non-fatal `large_indexed_flatgeobuf_write` warnings for indexed
    writes over large accepted record sets.
15. Write a validation report with errors, warnings, skipped checks and tool
    versions.

## Acceptance Evidence

- Validation fails on missing files.
- Validation fails or warns on invalid GeoParquet metadata.
- Validation treats PyArrow GeoParquet checks as required and
  `geoparquet-io`, DuckDB and Pyogrio/GDAL checks as optional
  dependency-dependent checks.
- Validation reports skipped/invalid coordinate counts.
- Validation catches malformed `quality_flags` tokens or delimiter usage.
- Validation reconciles warning counts with processing warnings.
- Validation treats `large_indexed_flatgeobuf_write` as a non-fatal processing
  warning unless a later accepted core-conversion policy changes it.
- Validation report is saved as a portable JSON or text artifact.

## Related Topics

- `../topics/validation_and_quality.md`
- `../topics/geoparquet_output.md`
- `../topics/pmtiles_viewer.md`
