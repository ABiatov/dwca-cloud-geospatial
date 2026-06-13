---
id: geoparquet-output
status: accepted
applies_to:
  - geospatial conversion
  - GeoParquet outputs
  - metadata/provenance
  - validation
sources:
  - examples/code/geoparquet/README.md
  - examples/code/geoparquet/format-specs/geoparquet.md
  - examples/code/geomermaids-GeoParquet_Writing_cookbook.md
  - examples/code/geoparquet-io/README.md
  - examples/code/dwca2parquet/REFERENCE.md
---

# GeoParquet Output

## Use In This Project

GeoParquet is the primary analytical geospatial output for occurrence records with usable coordinates. It should remain a normal Parquet table with explicit geospatial metadata, suitable for DuckDB, GeoPandas, QGIS, GDAL, and other readers.

## Geometry Rules

- Build point geometry only from parsed normalized `decimal_longitude` and
  `decimal_latitude`.
- Store coordinates in longitude, latitude order.
- Preserve original coordinate columns alongside geometry.
- Use null geometry or rejected-row reporting for missing or invalid coordinates, according to the accepted output policy.
- Geometry should be limited to the occurrence/core table unless an accepted extension-specific geometry use case exists.

## CRS

Darwin Core coordinates are normally WGS84 longitude/latitude. For GeoParquet metadata, prefer explicit CRS information. Be careful about axis order:

- WKB coordinate order is x, y, meaning longitude, latitude.
- OGC:CRS84 is longitude-latitude.
- EPSG:4326 is often used in tools, but its formal axis order can be latitude-longitude. Avoid ambiguity in accepted specs.

## Version Guidance

Candidate publishing default:

- GeoParquet 1.1 is the safest broad-compatibility default today.
- GeoParquet 2.0 may be useful when the project controls downstream readers and toolchain support is mature.
- GeoParquet 1.0 should generally be avoided for new published outputs because it lacks newer metadata and optimization features.

Confirm current reader support before making a long-lived decision.

## Optimization Practices

Useful practices from GeoParquet tooling and cookbooks:

- ZSTD compression for cloud or network-bound reads.
- Reasonable row group sizes for query pruning.
- Spatial sorting, such as Hilbert ordering or bbox ordering, before writing large files.
- GeoParquet 1.1 covering bbox columns for large WKB outputs so readers can
  prune row groups using Parquet statistics.
- Attribute or coarse-grid partitioning for large datasets when it matches
  common query filters, publishing constraints or update workflows.

## Validation

GeoParquet outputs should use layered validation:

- PyArrow is the required baseline validator for Parquet readability,
  GeoParquet footer metadata, schema, projection fields and row counts.
- `geoparquet-io` is the preferred optional spec-aware validator when
  installed.
- DuckDB is the preferred optional analytical reader for query access, row
  groups, metadata inspection and future bbox/spatial-pruning checks.
- GDAL/OGR or Pyogrio checks are useful best-effort reader checks when the
  local build supports Parquet/GeoParquet.
- Missing optional validation tools should be reported as skipped checks or
  warnings, not failures, when required PyArrow validation passes.

## Resolved By Accepted Docs

- The accepted baseline GeoParquet version is `1.1.0`, with `OGC:CRS84`, WKB point geometry, ZSTD compression, enabled statistics and configurable row group size. This is recorded in the accepted GeoParquet writer stack in `docs/development_plan.md`.
- Prompt 07 implemented `dwca_cloud_geospatial.geoparquet.write_geoparquet_occurrences`
  for explicit analytical output at `data/occurrences.parquet`. The writer
  streams accepted normalized records into PyArrow `ParquetWriter` row groups,
  defaults to `row_group_size=100_000`, writes ZSTD-compressed Parquet and
  stores GeoParquet metadata in the footer under the `geo` key.
- The production dependency is PyArrow. Install with the `geoparquet` optional
  extra, or with the full writer-capable `flatgeobuf` extra, which also
  includes PyArrow.
- The accepted optional validation toolchain is documented in
  `planning/decisions/ADR-003-geoparquet-validation-toolchain.md`. Install the
  `validation` extra to get PyArrow, DuckDB and `geoparquet-io`.
- Prompt 09 implemented required PyArrow GeoParquet validation for declared
  single-file `data/occurrences.parquet` outputs inside
  `validate_output_bundle`. Optional `geoparquet-io`, DuckDB and
  Pyogrio/GDAL checks are recorded as structured checks, warnings or skips
  depending on local dependency support.
- GeoParquet writing should start from accepted `NormalizedOccurrenceRecord`
  values produced by normalization after Prompt 05 quality rules, not
  parser-level `OccurrenceSourceRecord` rows. Rejected coordinate rows belong
  in `reports/rejected_records.csv` and processing metadata.
- GeoParquet must preserve the accepted nullable `quality_flags` string and
  `has_quality_flags` boolean from the normalized records.
- File-level bbox metadata is included in GeoParquet metadata.
- For large GeoParquet 1.1 outputs, a covering `bbox` struct column with
  `xmin`, `ymin`, `xmax` and `ymax` is default-on. Small fixtures and small
  local outputs may omit it until the covering-bbox implementation exists, but
  large-output conversion must not rely only on file-level bbox metadata.
- For large GeoParquet outputs, spatial sorting is default-on and
  strategy-configurable. Start with a bounded local strategy such as
  longitude/latitude or bbox min-corner sorting, and allow later Hilbert
  sorting through DuckDB, geoparquet-io or an equivalent helper.
- Partitioned GeoParquet dataset output remains an optional large-dataset mode
  enabled by configuration or threshold when a single
  `data/occurrences.parquet` file is impractical. Partitioned dataset
  validation remains future work with that mode.
- The accepted large-archive pipeline direction is streaming/chunked
  occurrence reading, chunked normalization handoff, streaming GeoParquet
  accepted-record writing, streaming rejected-record/report writing and
  bounded-memory counts/warnings aggregation.
- GeoParquet 2.0 support is deferred to post-MVP. The MVP and default output remain GeoParquet `1.1.0` for broad reader compatibility. GeoParquet 2.0 may be added later as an explicit opt-in output option only after target downstream readers and validation tools demonstrate reliable support. Adding 2.0 must not change the default GeoParquet version without a separate accepted decision.

## Open Questions

- None currently.
