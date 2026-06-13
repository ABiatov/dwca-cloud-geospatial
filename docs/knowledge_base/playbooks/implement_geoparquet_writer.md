---
id: implement-geoparquet-writer-playbook
status: accepted
applies_to:
  - geospatial conversion
  - GeoParquet outputs
  - metadata/provenance
sources:
  - docs/knowledge_base/topics/dwca_to_parquet_patterns.md
  - docs/knowledge_base/topics/geoparquet_output.md
  - examples/code/geoparquet/format-specs/geoparquet.md
  - examples/code/geomermaids-GeoParquet_Writing_cookbook.md
---

# Implement GeoParquet Writer

## Goal

Write accepted normalized occurrence records with usable coordinates to a valid
GeoParquet file while preserving project fields and provenance.

## Steps

1. Start from accepted `NormalizedOccurrenceRecord` values produced by
   `normalize_occurrence_records`.
2. Use parsed `decimal_longitude` and `decimal_latitude`; do not repeat
   parser-level Darwin Core term extraction.
3. Build point geometry from longitude, latitude.
4. Preserve original coordinate strings through `raw_decimal_longitude` and
   `raw_decimal_latitude` when included in the projection.
5. Exclude `RejectedOccurrenceRecord` values from GeoParquet rows; they belong
   in reports/metadata.
6. Write Parquet with compression and schema metadata.
7. Add GeoParquet metadata for geometry column, CRS, geometry type, and bbox.
8. Record accepted/rejected counts from `OccurrenceNormalizationResult`.
9. Preserve nullable `quality_flags` and `has_quality_flags` from accepted
   normalized records.
10. For large GeoParquet 1.1 outputs, add a default-on `bbox` struct covering
    column with `xmin`, `ymin`, `xmax` and `ymax`.
11. For large GeoParquet outputs, apply a default-on spatial sort using the
    configured strategy so row-group bboxes stay useful for predicate pushdown.
12. Keep partitioned GeoParquet dataset output as an explicit large-dataset
    mode enabled by configuration or threshold.
13. Validate output with required PyArrow checks and optional GeoParquet-aware
    tools when installed, preferring `geoparquet-io`, then DuckDB, then
    Pyogrio/GDAL as a best-effort reader check.
14. Add tests for accepted coordinates, rejected coordinates, projection
    fields, `quality_flags`, `has_quality_flags`, `class_` to `class` output
    naming, row counts and metadata.

## Candidate Defaults

- Geometry type: `Point`.
- Coordinate order: longitude, latitude.
- CRS: explicit WGS84/CRS84 decision in accepted output spec.
- Compression: ZSTD.
- Publishing version: GeoParquet 1.1 unless a later accepted decision chooses 2.0.
- Row group size: default around 100,000 rows.
- Large-output bbox covering: default-on for GeoParquet 1.1.
- Large-output spatial sorting: default-on, strategy configurable.
- Partitioned dataset output: optional large-dataset mode by configuration or
  threshold.

## Large Archive Handoff

The large-archive converter path should not materialize full accepted or
rejected record sets. Future implementation should connect:

1. streaming/chunked occurrence reader;
2. chunked normalization result handoff;
3. streaming GeoParquet accepted-record writer;
4. streaming rejected-record/report writer;
5. bounded-memory counts and warning aggregation.

## Acceptance Evidence

- File is readable as normal Parquet.
- File is recognized as GeoParquet by a geospatial reader.
- Metadata includes a `geo` key for the chosen version.
- Bounds and row counts match conversion summary.
- Large-output tests or benchmarks demonstrate bounded memory and useful
  row-group spatial pruning behavior.

Prompt 07 implemented this playbook with
`dwca_cloud_geospatial.geoparquet.write_geoparquet_occurrences`. PyArrow
validation is required for the test suite when PyArrow is installed.
GeoParquet-aware reader validation remains dependency-dependent. The preferred
optional order is `geoparquet-io`, then DuckDB, then Pyogrio/GDAL as a
best-effort reader check. Missing optional tools should skip or warn when
required PyArrow validation passes.

## Related Topics

- `../topics/geoparquet_output.md`
- `../topics/validation_and_quality.md`
