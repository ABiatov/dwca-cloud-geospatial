---
id: dwca-to-parquet-patterns
status: candidate
applies_to:
  - DwC-A parsing
  - field mapping and normalization
  - geospatial conversion
  - GeoParquet outputs
  - metadata/provenance
sources:
  - examples/code/dwca2parquet/README.md
  - examples/code/dwca2parquet/REFERENCE.md
  - examples/code/dwca-tools/README.md
---

# DwC-A To Parquet Patterns

## Use In This Project

The baseline converter should turn DwC-A core and extension tables into portable Parquet-family files while preserving source structure and provenance. Geometry can be added when coordinates are usable.

## Candidate Pipeline

1. Open the DwC-A archive safely.
2. Parse `meta.xml` into a schema object.
3. For each declared data file, stream CSV rows in batches.
4. Apply field names and descriptor defaults.
5. Add relationship columns such as `_id` and `_coreid`.
6. Optionally normalize well-known Darwin Core field types.
7. Build point geometry from valid coordinates when geometry output is enabled.
8. Write Parquet or GeoParquet with compression and metadata.
9. Copy or summarize source metadata such as `eml.xml`.
10. Write a conversion report with row counts, warnings, skipped records, and output paths.

## Raw And Interpreted Modes

Candidate behavior:

- Raw mode keeps source values as strings and minimizes interpretation.
- Interpreted mode casts known Darwin Core fields into typed columns and may create geometry by default.
- Geometry may be opt-in for raw mode and opt-out for interpreted mode.

This split is useful because biodiversity data often contains non-standard values in date and numeric fields.

## Type Mapping Candidates

Likely typed fields:

- `decimalLatitude`, `decimalLongitude`, `coordinateUncertaintyInMeters`, `coordinatePrecision` as floating point.
- `individualCount`, `year`, `month`, `day` as integers when parseable.
- boolean-like fields such as `hasGeospatialIssues` or `hasCoordinate` as booleans when parseable.
- `eventDate` kept as string, with optional derived parsed start/end dates.

Type conversion failures should set nulls or reject rows according to accepted policy, and should always be counted.

## Table Shape

Prefer normalized table outputs first:

- one Parquet file for the core;
- one Parquet file per extension;
- shared relationship keys for joins;
- optional denormalized outputs only when explicitly requested.

Denormalization can duplicate core records and can explode row counts when multiple one-to-many extensions are joined.

## Write Settings

Candidate defaults to evaluate:

- ZSTD compression for read-heavy, network-friendly outputs.
- Dictionary encoding for repeated categorical strings.
- Row group sizing chosen for expected query patterns.
- Explicit file metadata for source archive, row type, conversion mode, generated time, and tool version.

## Open Questions

- Exact baseline mode default: raw-first, interpreted-first, or explicit mode required.
- Whether Parquet output should always include all rows with null geometry, or whether final geospatial outputs should separate skipped coordinate rows.
- How much metadata belongs in Parquet footers versus a separate manifest JSON.

