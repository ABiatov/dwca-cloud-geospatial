# Prompt 10b: Large Archive Streaming And GeoParquet Optimization

## Required Skills

- `geospatial-pipeline`: chunked conversion pipeline, bounded-memory writer handoff and spatial optimization strategy.
- `data-package-spec`: GeoParquet large-output schema, metadata, validation and bundle contract.
- `dwca-archive-parser`: streaming/chunked occurrence row reading and parser diagnostics.
- `planning-artifact-curator`: record implementation decisions, evidence and downstream prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md`
- `docs/converter.md` if it exists.
- `planning/decisions/ADR-001-mvp-boundaries-and-interfaces.md`
- `planning/decisions/ADR-002-large-archive-geoparquet-strategy.md`
- Prompts `01` through `10`
- Latest session logs for prompts `01` through `10`
- Current parser, normalization, rejected-record, writer, metadata, validator, core API and CLI implementations.
- Prompt 08 metadata writer APIs:
  `dwca_cloud_geospatial.bundle.write_bundle_metadata`,
  `build_source_metadata`, `build_processing_metadata`,
  `write_rejected_records_csv`, `BundleWriterOptions` and
  `BundleMetadataWriteResult`. Current Prompt 08 inputs still use collected
  `OccurrenceReadResult` and `OccurrenceNormalizationResult`; this prompt may
  need to add a chunked-compatible adapter or summary object rather than
  requiring fully materialized accepted/rejected tuples for large archives.
- Prompt 08 processing metadata already records non-large-output GeoParquet
  mode declarations for `covering_bbox_column`, `spatial_sorting` and
  `partitioned_dataset` as disabled/null until this prompt implements those
  modes.
- Prompt 03 occurrence row reader API:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `iter_occurrence_rows`, `OccurrenceReadResult` and
  `OccurrenceSourceRecord`.
- Prompt 04/05 normalization APIs and models:
  `normalize_occurrence_records`, `normalize_occurrence_record`,
  `OccurrenceNormalizationResult`, `OccurrenceNormalizationCounts`,
  `NormalizedOccurrenceRecord`, `RejectedOccurrenceRecord`,
  `TypeConversionFailure` and `OccurrenceNormalizationWarning`.
- Prompt 06 FlatGeobuf writer API and large-output behavior:
  `write_flatgeobuf_occurrences`, `FlatGeobufWriterOptions`,
  `FlatGeobufWriterWarning`, `FlatGeobufDependencyError` and
  `large_indexed_flatgeobuf_write`.
- Prompt 07 GeoParquet writer API:
  `dwca_cloud_geospatial.geoparquet.write_geoparquet_occurrences`,
  `GeoParquetWriteResult`, `GeoParquetWriterOptions`,
  `GeoParquetDependencyError`, `DEFAULT_GEOPARQUET_RELATIVE_PATH` and
  `GEOPARQUET_PROJECTION_COLUMNS`.
- Prompt 07 GeoParquet behavior: `data/occurrences.parquet`, streaming
  PyArrow `ParquetWriter` batches, WKB point geometry in `geometry`,
  GeoParquet `1.1.0`, `OGC:CRS84`, file-level bbox metadata, ZSTD
  compression and default `row_group_size=100_000`.
- Post-Prompt-07 accepted large-archive decision:
  - before claiming support for tens of millions of records, the converter
    must provide a bounded-memory pipeline;
  - required shape is streaming/chunked occurrence reader, chunked
    normalization result handoff, streaming GeoParquet accepted-record writer,
    streaming rejected-record/report writer and bounded-memory counts/warnings
    aggregation;
  - for large GeoParquet 1.1 outputs, a covering `bbox` struct column is
    default-on;
  - for large GeoParquet outputs, spatial sorting is default-on and
    strategy-configurable;
  - partitioned GeoParquet dataset output is an optional large-dataset mode
    enabled by configuration or threshold.
- Post-Prompt-07 validation toolchain decision:
  `planning/decisions/ADR-003-geoparquet-validation-toolchain.md` accepts
  layered GeoParquet validation. Required checks use PyArrow. Optional
  GeoParquet-aware checks use `geoparquet-io`, DuckDB and Pyogrio/GDAL when
  available, and missing optional tools should be recorded as warnings or
  skipped checks when PyArrow validation passes.
- Prompt 09 bundle validator API:
  `dwca_cloud_geospatial.validation.validate_output_bundle`,
  `BundleValidationResult`, `BundleValidationIssue` and
  `BundleValidationCheck`.
- Prompt 09 current validator scope: single-file GeoParquet outputs are
  validated with required PyArrow checks; optional `geoparquet-io`, DuckDB and
  Pyogrio/GDAL checks are recorded as structured checks/skips; FlatGeobuf
  inspection is dependency-dependent through Pyogrio/GDAL; FlatGeobuf
  attribute-level `quality_flags` validation depends on readable geospatial
  table support. Partitioned GeoParquet dataset validation is not implemented
  yet and belongs to this prompt if partitioned output is implemented.
- Prompt 09 validation result behavior: `BundleValidationResult.status` is
  `passed`, `passed_with_warnings` or `failed`; required failures appear in
  `.errors`, optional/dependency skips appear in `.warnings` and `.checks`,
  and `.to_dict()` / `.to_json()` are available for CLI/GUI consumers.
- Local GeoParquet cookbook references:
  - `examples/code/geomermaids-GeoParquet_Writing_cookbook.md`
  - `examples/code/geomermaids-GeoParquet_Reading_Cookbook.md`

## Goal

Implement the bounded-memory large-archive conversion path and GeoParquet
large-output optimizations accepted in ADR-002, without changing the default
conversion format away from FlatGeobuf.

## Tasks

- Design and implement a chunked occurrence conversion handoff that avoids
  materializing all source, accepted or rejected records for large archives.
- Add or adapt a streaming/chunked occurrence reader API while preserving the
  existing Prompt 03 reader behavior for small tests and backwards-compatible
  callers where practical.
- Add a chunked normalization handoff or adapter that can emit accepted
  records, rejected records, conversion failures and warnings per chunk.
- Aggregate counts, type conversion failures, warnings, bounds and output row
  counts in bounded memory.
- Implement a streaming rejected-record/report writer so rejected rows do not
  need to be retained as a full tuple before report output.
- Extend GeoParquet writing for large GeoParquet `1.1.0` outputs with a
  default-on `bbox` struct covering column containing numeric `xmin`, `ymin`,
  `xmax` and `ymax` fields for point geometries in `OGC:CRS84`.
- Add spatial sorting for large GeoParquet outputs with a configurable
  strategy. Start with a bounded strategy that does not require loading all
  records into Python memory; if a full-file sort cannot be bounded, document
  and implement a partition/grid-based or external-helper strategy instead of
  calling `sorted(records)`.
- Add configuration and metadata fields for:
  - large-output mode;
  - GeoParquet covering bbox enabled/disabled;
  - spatial sort enabled/disabled;
  - spatial sort strategy;
  - partitioned output enabled/disabled;
  - partition key, grid strategy or threshold when used.
- Implement partitioned GeoParquet dataset output only if the core API and
  manifest/validator contract can support it cleanly in this prompt; otherwise
  preserve a documented config/threshold design and tests for rejecting or
  warning on unsupported partitioned mode.
- Ensure generated GeoParquet and FlatGeobuf still represent the same accepted
  record set when both are selected unless processing metadata documents a
  deliberate export filter.
- Add synthetic or fixture-based large-output tests that demonstrate bounded
  memory behavior at the API level without committing large files to the repo.
- Add tests for bbox covering column schema/content, spatial sort metadata,
  processing metadata aggregation, rejected-report streaming and count
  reconciliation.
- Add or update validation tests so large-output bbox covering and spatial
  sorting metadata are checked with required PyArrow validation and optional
  `geoparquet-io`/DuckDB checks when installed.
- If partitioned GeoParquet dataset output is implemented, extend
  `validate_output_bundle` and its tests to validate partition manifests,
  file inventory, aggregate row counts, GeoParquet metadata and required
  projection columns across all declared partition files. If partitioned
  output remains deferred, preserve an explicit unsupported-mode validation
  warning or failure path.
- Update `docs/development_plan.md`, `docs/output_format.md`,
  `docs/converter.md` if present, GeoParquet knowledge-base docs and
  downstream prompts when implementation details are accepted.

## Constraints

- Do not use GeoPandas as the primary writer or large-archive processing path.
- Do not switch the default conversion format from FlatGeobuf.
- Do not add GeoParquet 2.0 unless a new accepted decision is documented first.
- Do not introduce a required PostgreSQL/PostGIS database, permanent API
  service, scheduler or cloud-specific runtime.
- Do not implement a Python in-memory full sort for large-output spatial
  sorting.
- Do not commit large generated datasets to the repository.
- Keep small-fixture tests fast and deterministic.

## Acceptance Criteria

- A large-archive conversion path can process records through parser,
  normalization, GeoParquet writer and rejected-report writer without requiring
  full accepted/rejected materialization.
- GeoParquet large-output mode writes a valid GeoParquet `1.1.0` file with
  WKB point geometry, `OGC:CRS84`, ZSTD compression, row groups around
  `100_000`, file-level bbox metadata and a covering `bbox` struct column.
- Large-output spatial sorting is implemented with a bounded strategy or the
  prompt records a concrete blocked reason and preserves an API/config design
  that avoids full in-memory sorting.
- Processing metadata records large-output strategy decisions and reconciles
  source, accepted, rejected, warning and output counts.
- Rejected records can be written as a report through a streaming path.
- Validator coverage distinguishes small-output validity from large-output
  optimization requirements.
- Tests prove bbox column content, row counts, quality flag consistency,
  `has_quality_flags` consistency and same accepted record set across selected
  outputs.

## Required Session Log

Write `session_logs/YYYY-MM-DD_10b_large_archive_streaming_geoparquet.md`
with:

- Public API and internal handoff summary.
- Chunking and bounded-memory decisions.
- GeoParquet bbox covering and spatial sorting behavior.
- Partitioned output decision, implementation or deferred design.
- Metadata and validation changes.
- Synthetic large-output test strategy and results.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- Known limitations and remaining large-output risks.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `11` through `14` if public API names, conversion options,
bundle paths, metadata fields, validation coverage, viewer assumptions, GUI
options or known limitations changed.
