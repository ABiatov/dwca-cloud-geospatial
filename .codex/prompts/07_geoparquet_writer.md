# Prompt 07: GeoParquet Writer

## Required Skills

- `geospatial-pipeline`: point geometry conversion and geospatial output consistency.
- `data-package-spec`: GeoParquet metadata, occurrence projection and bundle contract.
- `planning-artifact-curator`: record decisions and update downstream prompts.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- Prompts `01` through `06`
- Latest session logs for prompts `01` through `06`
- Current FlatGeobuf writer and normalized occurrence implementation.
- Prompt 03 source-record handoff API for provenance context:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `OccurrenceReadResult` and `OccurrenceSourceRecord`.

## Goal

Write explicit analytical GeoParquet output at `data/occurrences.parquet`.

## Tasks

- Implement a streaming PyArrow-based GeoParquet writer.
- Reuse existing fixture roots from Prompt 01, including
  `tests/fixtures/output_bundles/` for bundle/output fixtures when needed.
- Encode point geometry as WKB in a binary `geometry` column.
- Add GeoParquet `1.1.0` metadata.
- Declare CRS `OGC:CRS84` and longitude-latitude coordinate order.
- Use ZSTD compression and configurable row group sizing, with an initial default around 100,000 rows.
- Include the required GeoParquet projection fields from `docs/output_format.md`.
- Compute or preserve file-level bounds for metadata handoff.
- Ensure generated GeoParquet and FlatGeobuf represent the same accepted record set when both are selected, unless a documented export filter exists.
- Add tests with PyArrow validation and a GeoParquet-aware check when locally available.

## Constraints

- Do not use GeoPandas as the primary writer.
- Do not switch the default conversion format from FlatGeobuf.
- Do not add GeoParquet 2.0 unless a new accepted decision is documented first.

## Acceptance Criteria

- `data/occurrences.parquet` is valid Parquet.
- GeoParquet metadata declares point geometry, `geometry` column and `OGC:CRS84`.
- Required projection columns are present.
- `quality_flags` uses the accepted nullable string representation.
- Tests validate metadata and row counts.

## Required Session Log

Write `session_logs/YYYY-MM-DD_07_geoparquet_writer.md` with:

- Writer API and dependency behavior.
- GeoParquet metadata decisions.
- Projection fields implemented.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `08` through `10` and `14` if GeoParquet paths, writer options, projection fields, metadata structures or dependency behavior changed.
