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

## Open Questions

- Whether invalid-coordinate rows remain in the main GeoParquet with null geometry or are excluded from geospatial output and preserved only in diagnostics.
- Exact threshold for warning or failing when type conversion failures are high.
- Whether validation should be a separate CLI command, part of conversion, or both.

