---
id: implement-geoparquet-writer-playbook
status: candidate
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
10. Validate output with at least one GeoParquet-aware tool or reader.
11. Add tests for accepted coordinates, rejected coordinates, projection
    fields, `quality_flags`, `has_quality_flags`, `class_` to `class` output
    naming, row counts and metadata.

## Candidate Defaults

- Geometry type: `Point`.
- Coordinate order: longitude, latitude.
- CRS: explicit WGS84/CRS84 decision in accepted output spec.
- Compression: ZSTD.
- Publishing version: GeoParquet 1.1 unless a later accepted decision chooses 2.0.

## Acceptance Evidence

- File is readable as normal Parquet.
- File is recognized as GeoParquet by a geospatial reader.
- Metadata includes a `geo` key for the chosen version.
- Bounds and row counts match conversion summary.

## Related Topics

- `../topics/geoparquet_output.md`
- `../topics/validation_and_quality.md`
