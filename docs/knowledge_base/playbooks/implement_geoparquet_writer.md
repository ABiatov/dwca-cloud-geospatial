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

Write occurrence records with usable coordinates to a valid GeoParquet file while preserving Darwin Core fields and provenance.

## Steps

1. Start from parsed core table batches.
2. Normalize or cast coordinate fields according to selected conversion mode.
3. Validate latitude and longitude ranges.
4. Build point geometry from longitude, latitude.
5. Preserve original coordinate columns.
6. Write Parquet with compression and schema metadata.
7. Add GeoParquet metadata for geometry column, CRS, geometry type, and bbox.
8. Record null-geometry or skipped-row counts.
9. Validate output with at least one GeoParquet-aware tool or reader.
10. Add tests for valid coordinates, invalid coordinates, null geometry, and metadata.

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

