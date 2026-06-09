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
4. Check Parquet and GeoParquet files open.
5. Validate GeoParquet metadata and geometry data.
6. Confirm row counts match conversion reports.
7. If raw core or extension table exports are generated, confirm extension relationship keys can join to core keys.
8. Validate FlatGeobuf or PMTiles files if present.
9. Check viewer manifest paths, bounds, layers, and field names.
10. Confirm normalized output fields use snake_case project names and do not
    emit parser/source camelCase terms; `class` is the output field, not
    Python attribute `class_`.
11. Validate `quality_flags` as nullable `|`-delimited strings and split them
    for exact-token checks.
12. Reconcile `warning_count`, `warnings`, and `type_conversion_failures` in
    processing metadata.
13. Write a validation report with errors, warnings, and tool versions.

## Acceptance Evidence

- Validation fails on missing files.
- Validation fails or warns on invalid GeoParquet metadata.
- Validation reports skipped/invalid coordinate counts.
- Validation catches malformed `quality_flags` tokens or delimiter usage.
- Validation reconciles warning counts with processing warnings.
- Validation report is saved as a portable JSON or text artifact.

## Related Topics

- `../topics/validation_and_quality.md`
- `../topics/geoparquet_output.md`
- `../topics/pmtiles_viewer.md`
