# Prompt 14: Demo, Documentation And MVP Hardening

## Required Skills

- `planning-artifact-curator`: consolidate accepted decisions, evidence, open questions and next actions.
- `data-package-spec`: final output bundle docs and validation evidence.
- `dwca-archive-parser`: parser documentation accuracy.
- `geospatial-pipeline`: end-to-end converter behavior and tests.
- `static-viewer-contract`: viewer documentation and static hosting behavior.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md` if it exists.
- `docs/converter.md` if it exists.
- `docs/viewer_contract.md` if it exists.
- `docs/deployment.md` if it exists.
- All prompts `01` through `13`, including `10b`
- Latest session logs for prompts `01` through `13`, including `10b` when present
- Current tests, examples and generated sample bundle instructions.
- Prompt 02 inspection API and docs:
  `dwca_cloud_geospatial.inspection.inspect_dwca`,
  `docs/dwca_parser.md`, the CLI command
  `dwca-cloud-geospatial inspect [--json] <archive>`, and fixtures under
  `tests/fixtures/dwca/minimal_occurrence/`.
- Prompt 03 occurrence row reader API and docs:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `iter_occurrence_rows`, `OccurrenceReadResult`,
  `OccurrenceSourceRecord`, `docs/dwca_parser.md`, and occurrence parser
  fixtures under `tests/fixtures/dwca/minimal_occurrence/`.
- Prompt 04 occurrence normalization API and docs:
  `dwca_cloud_geospatial.normalization.normalize_occurrence_records`,
  `normalize_occurrence_record`, `OccurrenceNormalizationResult`,
  `OccurrenceNormalizationCounts`, `NormalizedOccurrenceRecord`,
  `RejectedOccurrenceRecord`, `docs/dwca_parser.md`, and normalization
  fixtures under `tests/fixtures/dwca/minimal_occurrence/normalization/`.
- Prompt 05 quality-rule API additions:
  `TypeConversionFailure`, `OccurrenceNormalizationWarning`, `warning_count`,
  `type_conversion_failures`, `warnings`, nullable exact-token
  `quality_flags`, `has_quality_flags`, and quality-rule fixtures under
  `tests/fixtures/dwca/minimal_occurrence/quality_rules/`.
- Prompt 06 FlatGeobuf writer API:
  `dwca_cloud_geospatial.flatgeobuf.write_flatgeobuf_occurrences`,
  `FlatGeobufWriteResult`, `FlatGeobufWriterOptions`,
  `FlatGeobufWriterWarning`, `FlatGeobufDependencyError`,
  `DEFAULT_FLATGEOBUF_RELATIVE_PATH`, `FLATGEOBUF_PROJECTION_COLUMNS`, and
  tests in `tests/test_flatgeobuf_writer.py`. The writer produces
  `exports/occurrences.fgb`, uses an optional Pyogrio/PyArrow/GDAL production
  backend, requests `SPATIAL_INDEX=YES` by default, emits structured
  `large_indexed_flatgeobuf_write` warnings for risky indexed writes, and has
  dependency-specific real FlatGeobuf checks that skip explicitly when local
  geospatial writer dependencies are absent.
- Prompt 06 dependency follow-up: `pyproject.toml` includes the `flatgeobuf`
  optional extra and `docs/developer_setup.md` documents
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"`. The local `.venv/`
  verified Pyogrio `0.12.1`, GDAL `3.11.4`, PyArrow `24.0.0`, FlatGeobuf
  driver `rw`, Prompt 06 writer tests with `6 passed`, and the full suite with
  `27 passed`.
- Prompt 06 large-data limitation to preserve in final docs: the current
  parser, normalizer and FlatGeobuf writer still materialize full record sets
  in memory. For very large DwC-A inputs, such as 5 million accepted
  occurrence records, the writer estimates about 320,000,000 bytes for
  spatial-index construction, emits `large_indexed_flatgeobuf_write`, keeps
  `SPATIAL_INDEX=YES` by default, and attempts the write. It may take a long
  time, consume substantial memory, or fail; it does not auto-switch to
  `SPATIAL_INDEX=NO` unless a future accepted change introduces that behavior.
- Prompt 07 GeoParquet writer API:
  `dwca_cloud_geospatial.geoparquet.write_geoparquet_occurrences`,
  `GeoParquetWriteResult`, `GeoParquetWriterOptions`,
  `GeoParquetDependencyError`, `DEFAULT_GEOPARQUET_RELATIVE_PATH`,
  `GEOPARQUET_PROJECTION_COLUMNS`, and tests in
  `tests/test_geoparquet_writer.py`. The writer produces
  `data/occurrences.parquet`, uses streaming PyArrow `ParquetWriter` batches,
  stores WKB point geometry in `geometry`, writes GeoParquet `1.1.0` metadata
  with `OGC:CRS84` PROJJSON longitude-latitude axis order, stores file-level
  bbox metadata, uses ZSTD compression, and defaults to
  `row_group_size=100_000`.
- Prompt 07 dependency follow-up: `pyproject.toml` includes the `geoparquet`
  optional extra for `pyarrow>=24`; `docs/developer_setup.md` documents
  `python -m pip install -e "${REPO}[dev,geoparquet]"`, while the full
  writer-capable `.venv/` workflow can continue using
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"` because that extra also
  provides PyArrow. Local verification used PyArrow `24.0.0`; PyArrow
  GeoParquet writer tests passed, and the dependency-dependent
  Pyogrio/GDAL GeoParquet-aware reader check skipped when local GDAL Parquet
  read support was unavailable.
- Post-Prompt-07 validation toolchain decision to preserve in final docs:
  PyArrow is the required baseline GeoParquet validator; `geoparquet-io` and
  DuckDB are preferred optional validation tools; Pyogrio/GDAL remains a
  best-effort reader check. Missing optional validation tools should be
  reported as warnings or skipped checks, not as failures when PyArrow
  validation passes. The full local writer and validation install is
  `python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"`.
- Validation installation evidence to preserve: the local Python 3.13/macOS
  `.venv/` uses `pyproj==3.7.0` in the `validation` extra because newer
  `pyproj` releases may require a source build with system PROJ. The verified
  optional validation stack included `geoparquet-io 1.3.0`, DuckDB `1.5.1`,
  PyProj `3.7.0`, PyArrow `24.0.0`, Pyogrio `0.12.1` and GDAL `3.11.4`.
- Prompt 07 record-set rule to preserve: when FlatGeobuf and GeoParquet are
  both selected, both writers should receive the same accepted
  `NormalizedOccurrenceRecord` set unless processing metadata documents an
  explicit export filter.
- Prompt 08 bundle metadata writer API:
  `dwca_cloud_geospatial.bundle.write_bundle_metadata`,
  `build_source_metadata`, `build_processing_metadata`,
  `write_rejected_records_csv`, `BundleWriterOptions`,
  `BundleMetadataWriteResult`, and path constants for `manifest.json`,
  `metadata/source.json`, `metadata/processing.json` and
  `reports/rejected_records.csv`. Prompt 08 writes the rejected-record report
  only when rejected records exist, inventories only generated files in
  `manifest.files`, includes size and SHA-256 checksums where practical, and
  preserves FlatGeobuf writer warning `large_indexed_flatgeobuf_write` in
  `metadata/processing.json.warnings`.
- Prompt 08 EML/source metadata limitation to preserve: source metadata reads
  the declared `ArchiveMetadata.metadata_file` when safely available and
  extracts common EML dataset/rights values, but missing GBIF/OBIS values stay
  null and are not invented.
- Post-Prompt-07 large-archive decision to preserve in final docs: before the
  converter claims support for tens of millions of records, it must provide a
  bounded-memory pipeline with streaming/chunked occurrence reading, chunked
  normalization handoff, streaming GeoParquet accepted-record writing,
  streaming rejected-record/report writing and bounded-memory counts/warnings
  aggregation.
- Post-Prompt-07 large GeoParquet output decision to preserve in final docs:
  covering `bbox` is default-on for large GeoParquet 1.1 outputs; spatial
  sorting is default-on for large GeoParquet outputs with a configurable
  strategy; partitioned GeoParquet dataset output is an optional large-dataset
  mode enabled by configuration or threshold.
- Prompt 10b large-archive implementation when present: preserve its public
  API names, large-output options, metadata fields, validation coverage,
  benchmark or synthetic large-output evidence, and remaining limitations in
  final docs. If Prompt 10b is not completed before hardening, final docs must
  clearly state that support for tens of millions of records is not yet
  claimed.
- Post-Prompt-03 handoff clarification: the Prompt 03 `Open Issues Affecting
  Normalization` were confirmed to be scope boundaries, not blockers before
  Prompt 04. Final docs should preserve that split: source row reading in
  Prompt 03, normalization in Prompt 04, quality thresholds in Prompt 05,
  metadata/EML extraction in Prompt 08, and multi-file occurrence-core
  streaming as deferred work unless implemented later.
- Checklist DwC-A examples inspected after Prompt 02:
  `examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`,
  `examples/dwca/dwca-appendixiibernconventionua-v1.2.zip` and
  `examples/dwca/dwca-kharkivredliastua-v1.0.zip`. They are valid
  inspectable `Taxon` core archives, but they are not occurrence geospatial
  conversion inputs for the MVP workflow.

## Goal

Make the MVP understandable, repeatable and ready for external review.

## Tasks

- Run or refresh an end-to-end sample conversion note using local DwC-A examples.
- Update README and `docs/developer_setup.md` with current `.venv/`
  installation, CLI, GUI and viewer usage.
- Complete or update `docs/dwca_parser.md`, `docs/converter.md`, `docs/viewer_contract.md` and `docs/deployment.md`.
- Confirm `docs/output_format.md` matches implemented bundle behavior.
- Confirm `docs/developer_setup.md` still documents the FlatGeobuf optional
  dependency stack and real writer verification command.
- Add regression tests for parser behavior, normalization, output writing and bundle validation where gaps remain.
- Add known limitations and MVP+ roadmap, including PMTiles as deferred.
- Document the current large-DwC-A limitation clearly: full-record
  materialization remains a risk until chunked parser/normalizer/writer
  handoff is implemented.
- If Prompt 10b has been completed, replace the generic materialization
  limitation with the actual implemented bounded-memory behavior, test
  evidence and remaining scale limits.
- Document the checklist limitation clearly: checklist/Taxon DwC-A archives can
  be inspected, but the MVP converter only produces geospatial outputs from
  occurrence archives with coordinate terms.
- Include the three local checklist archives in final demo evidence as
  non-occurrence inspection examples and, when conversion exists, negative
  conversion examples with actionable errors.
- Record demo evidence and validation results.
- Remove stale prompt assumptions only if they contradict final accepted docs; otherwise leave historical prompts intact.

## Constraints

- Do not expand MVP scope to live downloads, taxonomy enrichment, PMTiles, backend services or cloud-specific deployment.
- Do not hide known limitations in code comments only; document them.
- Do not make broad refactors unrelated to hardening or docs consistency.

## Acceptance Criteria

- A fresh user can install the package, convert a sample archive and inspect the result using documented steps.
- Tests protect parser behavior, normalization, output writing and bundle validation.
- Docs clearly state what is MVP versus MVP+.
- Remaining risks and deferred work are visible.

## Required Session Log

Write `session_logs/YYYY-MM-DD_14_demo_docs_hardening.md` with:

- Final files updated.
- End-to-end demo commands and results.
- Test and validation evidence.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- Known remaining limitations.
- Suggested next MVP+ prompts or ADRs.
- `Prompt Updates`: list prompt files changed, or `None`.

## Prompt Maintenance

If this session changes accepted decisions, update canonical docs and this prompt flow description. If it identifies new MVP+ work, create new numbered prompts only after the MVP prompt sequence remains internally consistent.
