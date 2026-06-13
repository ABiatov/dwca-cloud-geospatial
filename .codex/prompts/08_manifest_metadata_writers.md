# Prompt 08: Manifest And Metadata Writers

## Required Skills

- `data-package-spec`: bundle layout, manifest, source metadata, processing metadata, provenance and counts.
- `geospatial-pipeline`: conversion result integration with output writers.
- `planning-artifact-curator`: session log and prompt maintenance.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- Prompts `01` through `07`
- Latest session logs for prompts `01` through `07`
- Current parser, normalization, quality, FlatGeobuf and GeoParquet writer APIs.
- Prompt 06 FlatGeobuf writer API:
  `dwca_cloud_geospatial.flatgeobuf.write_flatgeobuf_occurrences`,
  `FlatGeobufWriteResult`, `FlatGeobufWriterOptions`,
  `FlatGeobufWriterWarning`, `FlatGeobufDependencyError`,
  `DEFAULT_FLATGEOBUF_RELATIVE_PATH` and
  `FLATGEOBUF_PROJECTION_COLUMNS`.
- Prompt 06 writes accepted records under `exports/occurrences.fgb`, requests
  `SPATIAL_INDEX=YES` by default, returns structured large indexed-write
  warnings with code `large_indexed_flatgeobuf_write`, and raises
  `FlatGeobufDependencyError` when optional Pyogrio/PyArrow/GDAL support is
  unavailable.
- Prompt 06 dependency follow-up: `pyproject.toml` now provides the
  `flatgeobuf` optional extra. The documented full install command is
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"`; the local `.venv/`
  verified Pyogrio `0.12.1`, GDAL `3.11.4`, PyArrow `24.0.0`, FlatGeobuf
  driver `rw`, and real FlatGeobuf writer tests passed with no dependency
  skip.
- Prompt 06 large-output behavior: the writer does not automatically disable
  spatial indexing for large accepted record sets. With the default
  `spatial_index=True`, it warns before writing when feature count is high or
  estimated index memory is high, but still attempts the indexed write unless a
  later core-conversion policy changes that behavior.
- Prompt 07 GeoParquet writer API:
  `dwca_cloud_geospatial.geoparquet.write_geoparquet_occurrences`,
  `GeoParquetWriteResult`, `GeoParquetWriterOptions`,
  `GeoParquetDependencyError`, `DEFAULT_GEOPARQUET_RELATIVE_PATH` and
  `GEOPARQUET_PROJECTION_COLUMNS`.
- Prompt 07 writes accepted records under `data/occurrences.parquet`, uses a
  streaming PyArrow `ParquetWriter`, stores WKB point geometry in `geometry`,
  writes GeoParquet `1.1.0` metadata with `OGC:CRS84` PROJJSON,
  longitude-latitude axis order, geometry bbox, ZSTD compression and default
  `row_group_size=100_000`.
- Prompt 07 dependency behavior: GeoParquet production writes require
  `pyarrow>=24`. `pyproject.toml` provides a `geoparquet` optional extra, and
  the documented full writer-capable `.venv/` install
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"` also provides PyArrow.
- Prompt 07 projection behavior: GeoParquet uses the broad normalized
  analytical projection from `NormalizedOccurrenceRecord.to_dict()`, including
  `class` instead of Python attribute `class_`, required GeoParquet fields,
  optional source-preservation fields, `quality_flags`, `has_quality_flags`
  and the `geometry` column. When FlatGeobuf and GeoParquet are both selected,
  they should receive the same accepted normalized record set unless
  processing metadata documents an export filter.
- Post-Prompt-07 large-archive decision: before claiming support for tens of
  millions of records, the converter must provide a chunked large-archive
  pipeline with streaming/chunked occurrence reading, chunked normalization
  handoff, streaming GeoParquet accepted-record writing, streaming
  rejected-record/report writing and bounded-memory counts/warnings
  aggregation. Processing metadata should be shaped so it can summarize this
  chunked path without requiring fully materialized records.
- Post-Prompt-07 large GeoParquet output decision: for large GeoParquet 1.1
  outputs, a covering `bbox` struct column is default-on; for large
  GeoParquet outputs, spatial sorting is default-on and strategy-configurable;
  partitioned GeoParquet dataset output is an optional large-dataset mode
  enabled by configuration or threshold. Processing metadata must record
  whether these modes were used, including strategy, threshold or partition key
  when applicable.
- Prompt 04/05 normalization API, quality and count/rejection models:
  `normalize_occurrence_records`, `OccurrenceNormalizationResult`,
  `OccurrenceNormalizationCounts`, `NormalizedOccurrenceRecord` and
  `RejectedOccurrenceRecord`, plus Prompt 05 `TypeConversionFailure` and
  `OccurrenceNormalizationWarning`.
- Use Prompt 04 counts for `source_records`, `parsed_records`,
  `accepted_records` and `rejected_records`; use Prompt 05 `warning_count`,
  `type_conversion_failures` and `warnings` for processing metadata; use
  `RejectedOccurrenceRecord.to_dict()` or an equivalent explicit column
  mapping for `reports/rejected_records.csv`.
- When serializing accepted normalized records for metadata/projection helpers,
  preserve the Prompt 04 `class_` to output `class` mapping and avoid emitting
  source camelCase Darwin Core terms as normalized fields.
- Prompt 03 source-record handoff API for parser provenance context:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `OccurrenceReadResult` and `OccurrenceSourceRecord`.
- Post-Prompt-03 handoff clarification: EML content extraction was deferred
  deliberately and is not a blocker for Prompt 04 normalization. Prompt 08 is
  the first prompt expected to read the declared `ArchiveMetadata.metadata_file`
  contents for `metadata/source.json`.

## Goal

Generate the static output bundle metadata files: `manifest.json`, `metadata/source.json`, `metadata/processing.json`, and conditional `reports/rejected_records.csv`.

## Tasks

- Implement output directory layout exactly as documented.
- Reuse existing fixture roots from Prompt 01, including
  `tests/fixtures/output_bundles/` for sample bundle fixtures.
- Write `manifest.json` with schema versions, id, title, timestamps, generator, source summary, files inventory, layers, viewer defaults and counts.
- Write `metadata/source.json` from archive, DwC-A, EML, dataset, rights, GBIF and OBIS provenance when available.
- Implement the EML content extraction deferred from Prompt 02/03 by reading
  the declared `ArchiveMetadata.metadata_file` when present and safely
  available. Missing EML values must remain nullable source metadata fields.
- Write `metadata/processing.json` with effective configuration, field mapping, quality rules, counts, type conversion failures, warnings and validation summary placeholder.
- Include FlatGeobuf writer warnings, especially
  `large_indexed_flatgeobuf_write`, in processing metadata when emitted by the
  writer.
- Write `reports/rejected_records.csv` only when at least one record is rejected or skipped.
- Omit files not generated from `manifest.files`.
- Include file size and checksum where practical.
- Add tests for FlatGeobuf-only default bundle and explicit GeoParquet bundle inventory.

## Constraints

- Missing GBIF/OBIS values must be null, not invented.
- `reports/rejected_records.csv` must be absent when no records are rejected.
- Do not implement full bundle validation here beyond local writer consistency checks; Prompt 09 owns validator behavior.

## Acceptance Criteria

- Generated bundle layout matches `docs/output_format.md`.
- Manifest file inventory reconciles with generated files.
- Counts reconcile across conversion result and metadata.
- Conditional rejected report behavior is tested.
- Viewer fields include only fields supported by the generated projection.

## Required Session Log

Write `session_logs/YYYY-MM-DD_08_manifest_metadata_writers.md` with:

- Metadata writer APIs.
- File inventory/count behavior.
- Any source metadata limitations.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `09` through `14` if manifest shape, metadata paths, count fields, report columns or writer APIs changed.
