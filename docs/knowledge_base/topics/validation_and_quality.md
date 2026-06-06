---
id: validation-and-quality
status: candidate
applies_to:
  - DwC-A parsing
  - field mapping and normalization
  - geospatial conversion
  - GeoParquet outputs
  - metadata/provenance
sources:
  - examples/code/dwca2parquet/REFERENCE.md
  - examples/code/geoparquet/format-specs/geoparquet.md
  - examples/code/geomermaids-GeoParquet_Writing_cookbook.md
  - examples/code/dwca-tools/docs/TEST_ARCHIVES_PLAN.md
---

# Validation And Quality

## Use In This Project

The converter should make data quality explicit. Invalid, skipped, default-filled, cast-failed, or null-geometry records should be reported rather than silently disappearing.

## Parser Validation

Check:

- archive structure;
- path traversal in zip members;
- presence and parseability of `meta.xml`;
- declared files exist;
- declared field indexes match row shape;
- encodings, delimiters, quote characters, and header lines;
- core ID and extension `coreid` consistency where possible.

## Coordinate Validation

Check:

- `decimalLatitude` and `decimalLongitude` exist;
- values parse as numbers;
- longitude is within `[-180, 180]`;
- latitude is within `[-90, 90]`;
- null, empty, or invalid coordinates are counted;
- geometry nulls and rejected rows are explained.

Candidate quality flags:

- `missing_coordinates`
- `invalid_latitude`
- `invalid_longitude`
- `zero_zero_coordinate`
- `coordinate_out_of_range`
- `type_conversion_failed`
- `dwca_default_applied`

## Output Validation

Check:

- Parquet files open with a normal Parquet reader.
- GeoParquet metadata validates against the chosen version.
- Geometry column is readable by at least one geospatial reader.
- CRS and coordinate order are explicit.
- Row counts match expected accepted/skipped counts.
- Extension tables can join back to core records.
- Manifest paths point to existing files.

## Diagnostics

Write diagnostics as portable files, likely JSON and/or CSV:

- conversion summary;
- warnings;
- rejected or skipped record counts by reason;
- type conversion failure counts;
- coordinate validation summary;
- output file inventory;
- source archive metadata.

## Resolved By Accepted Docs

- Invalid or incomplete coordinate records are rejected from geospatial outputs and preserved through diagnostics/reports, including stable reason codes. `docs/development_plan.md` M2 requires invalid or incomplete coordinate records to be rejected, M3 requires `reports/rejected_records.csv` when records are rejected or skipped, and `docs/output_format.md` makes that report conditional on at least one rejected/skipped record.
- Validation should exist both during conversion and as a separate validation surface. `docs/development_plan.md` M3 calls for a bundle validation command or API, and M4 calls for a CLI command for validating an existing output bundle.
- For MVP, type conversion failures should be counted by field and reason in processing metadata. Optional-field conversion failures should set normalized values to null and emit warnings when the failure rate for a field is `>= 5%` of parsed records. Critical-field failures, including coordinate parsing failures, should reject affected records with stable reason codes. The conversion should fail only when no accepted occurrence records remain, required provenance fields cannot be produced, or parser/metadata structure prevents reliable row interpretation. Future releases may add configurable warning/failure thresholds.

## Open Questions

- None currently.
