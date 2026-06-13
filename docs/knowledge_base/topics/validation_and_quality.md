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

Implemented coordinate rejection reason codes from occurrence normalization:

- `missing_coordinates`
- `invalid_latitude`
- `invalid_longitude`
- `zero_zero_coordinate`
- `coordinate_out_of_range`

These are rejection reason codes for rows excluded from accepted geospatial
outputs, not `quality_flags` on accepted records.

Implemented accepted-record quality flag codes:

- `missing_scientific_name`
- `missing_event_date`
- `missing_coordinate_uncertainty`
- `invalid_coordinate_uncertainty`
- `missing_geodetic_datum`
- `invalid_event_year`

`quality_flags` is a nullable `|`-delimited string. No flags are represented
as null, and exact-token matching requires splitting on `|`.

Implemented optional conversion failure reason codes:

- `invalid_float`
- `invalid_integer`

## Output Validation

Check:

- Parquet files open with a normal Parquet reader.
- GeoParquet metadata validates against the chosen version.
- Geometry column is readable by at least one geospatial reader.
- CRS and coordinate order are explicit.
- Row counts match expected accepted/skipped counts.
- Extension tables can join back to core records.
- Manifest paths point to existing files.

Implemented bundle validation starts at
`dwca_cloud_geospatial.validation.validate_output_bundle`. It returns
`BundleValidationResult` with `status`, required `errors`, non-fatal
`warnings`, structured `checks`, `checked_files`, `has_errors`,
`skipped_checks`, `to_dict()` and `to_json()`.

Required validation failures should be separated from optional
dependency-dependent skips. For declared GeoParquet files, PyArrow validation
is required. `geoparquet-io`, DuckDB and Pyogrio/GDAL checks are optional and
should be recorded as warnings or skipped checks when unavailable. FlatGeobuf
inspection is dependency-dependent through Pyogrio/GDAL.

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

- Prompt 04 implemented occurrence normalization through
  `dwca_cloud_geospatial.normalization.normalize_occurrence_records`. It
  returns `OccurrenceNormalizationResult` with `accepted_records`,
  `rejected_records` and counts for `source_records`, `parsed_records`,
  `accepted_records`, `rejected_records` and `warning_count`.
- Prompt 05 added quality flag assignment, `TypeConversionFailure` accounting
  by field/reason/action and `OccurrenceNormalizationWarning` entries for
  optional conversion failure rates at `>= 5%` of parsed records.
- Prompt 08 writes `metadata/processing.json` with normalization warnings and
  writer warnings. In processing metadata, `warning_count` reconciles with the
  serialized `warnings` array, including FlatGeobuf writer warnings such as
  `large_indexed_flatgeobuf_write` when emitted.
- Prompt 09 implemented `validate_output_bundle` and structured validation
  results. It checks required JSON files and schema versions, manifest
  inventory, SHA-256 checksums, required PyArrow GeoParquet metadata and
  projection fields, optional GeoParquet-aware readers, dependency-dependent
  FlatGeobuf inspection, counts, rejected CSV columns, viewer fields,
  `quality_flags` token semantics, `has_quality_flags` consistency where
  row-level data are readable, processing warning/type-conversion structures
  and nullable GBIF/OBIS provenance values.
- Prompt 09 currently validates implemented single-file GeoParquet output.
  Partitioned GeoParquet dataset validation remains future work if Prompt 10b
  implements partitioned output.
- Invalid or incomplete coordinate records are rejected from geospatial outputs and preserved through diagnostics/reports, including stable reason codes. `docs/development_plan.md` M2 requires invalid or incomplete coordinate records to be rejected, M3 requires `reports/rejected_records.csv` when records are rejected or skipped, and `docs/output_format.md` makes that report conditional on at least one rejected/skipped record.
- Validation should exist both during conversion and as a separate validation surface. `docs/development_plan.md` M3 calls for a bundle validation command or API, and M4 calls for a CLI command for validating an existing output bundle.
- For MVP, type conversion failures should be counted by field and reason in processing metadata. Optional-field conversion failures should set normalized values to null and emit warnings when the failure rate for a field is `>= 5%` of parsed records. Critical-field failures, including coordinate parsing failures, should reject affected records with stable reason codes. The conversion should fail only when no accepted occurrence records remain, required provenance fields cannot be produced, or parser/metadata structure prevents reliable row interpretation. Future releases may add configurable warning/failure thresholds.

## Open Questions

- None currently.
