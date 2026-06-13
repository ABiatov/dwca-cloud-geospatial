# Prompt 09: Bundle Validation

## Required Skills

- `data-package-spec`: output bundle validation, schema versions, file inventory and counts.
- `geospatial-pipeline`: generated geospatial file checks.
- `planning-artifact-curator`: log validation evidence and update downstream prompts.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- Prompts `01` through `08`
- Latest session logs for prompts `01` through `08`
- Current bundle writer implementation and tests.
- Prompt 06 FlatGeobuf writer API and projection constants:
  `write_flatgeobuf_occurrences`, `FlatGeobufWriteResult`,
  `FlatGeobufWriterWarning`, `FlatGeobufDependencyError`,
  `DEFAULT_FLATGEOBUF_RELATIVE_PATH` and
  `FLATGEOBUF_PROJECTION_COLUMNS`.
- Prompt 06 dependency behavior: production writes require optional
  Pyogrio/PyArrow/GDAL support, while tests can validate projection and
  guardrails through the isolated backend seam. Validation should report
  FlatGeobuf file-inspection skips as dependency-dependent warnings when local
  dependencies are absent.
- Prompt 06 dependency follow-up: `pyproject.toml` includes the `flatgeobuf`
  optional extra and `docs/developer_setup.md` documents
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"`. The local `.venv/`
  verified Pyogrio `0.12.1`, GDAL `3.11.4`, PyArrow `24.0.0`, FlatGeobuf
  driver `rw`, `tests/test_flatgeobuf_writer.py` with `6 passed`, and the full
  test suite with `27 passed`.
- Prompt 06 large-output behavior: large FlatGeobuf indexed writes emit
  structured warning code `large_indexed_flatgeobuf_write` but are not stopped
  and do not auto-switch to `SPATIAL_INDEX=NO`. Validator work should check
  that any emitted writer warnings are preserved in metadata once Prompt 08
  records them.
- Prompt 07 GeoParquet writer API and projection constants:
  `write_geoparquet_occurrences`, `GeoParquetWriteResult`,
  `GeoParquetWriterOptions`, `GeoParquetDependencyError`,
  `DEFAULT_GEOPARQUET_RELATIVE_PATH` and `GEOPARQUET_PROJECTION_COLUMNS`.
- Prompt 07 GeoParquet behavior: `data/occurrences.parquet` is written with
  PyArrow streaming batches, WKB point geometry in `geometry`, GeoParquet
  `1.1.0` metadata, `OGC:CRS84` PROJJSON with longitude-latitude axis order,
  geometry bbox, ZSTD compression and configurable row group size defaulting
  to `100_000`.
- Prompt 07 dependency behavior: production GeoParquet writing requires
  `pyarrow>=24`; validation should always perform normal Parquet/footer checks
  when PyArrow is available and report GeoParquet-aware reader checks as
  dependency-dependent warnings or skips when local GDAL/Pyogrio/other
  geospatial readers cannot inspect the file.
- Prompt 07 verification used PyArrow `24.0.0`; PyArrow-focused GeoParquet
  writer tests passed, while the Pyogrio/GDAL GeoParquet-aware reader check
  skipped when local GDAL Parquet read support was unavailable.
- Post-Prompt-07 validation toolchain decision:
  `planning/decisions/ADR-003-geoparquet-validation-toolchain.md` accepts
  layered GeoParquet validation. PyArrow checks are required for declared
  GeoParquet files. Optional GeoParquet-aware checks should run when available
  in this preferred order: `geoparquet-io`, DuckDB, then Pyogrio/GDAL as a
  best-effort geospatial reader check. Missing optional tools or unavailable
  local GDAL Parquet support should be reported as warnings/skipped checks, not
  as failures, when required PyArrow validation passes.
- Prompt 09 validation dependency setup: `pyproject.toml` provides a
  `validation` optional extra containing PyArrow, DuckDB and `geoparquet-io`.
  The full local writer and validation install is
  `python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"`.
- Validation install follow-up: the verified local Python 3.13/macOS `.venv/`
  workflow pins `pyproj==3.7.0` in the `validation` extra because newer
  `pyproj` releases may fall back to source builds requiring a system PROJ
  executable. If installation fails with `proj executable not found`, install
  the binary wheel first with
  `.venv/bin/python -m pip install --only-binary=:all: "pyproj==3.7.0"` and
  rerun the full extra install.
- Post-Prompt-07 large GeoParquet output decision: large GeoParquet 1.1
  outputs should have a default-on covering `bbox` struct column with `xmin`,
  `ymin`, `xmax` and `ymax`; large GeoParquet outputs should have default-on,
  strategy-configurable spatial sorting; partitioned GeoParquet dataset output
  remains an optional large-dataset mode enabled by configuration or threshold.
  Validator work should check these declarations and metadata when present,
  while allowing small fixtures and small local outputs to omit large-output
  extensions until implementation reaches that stage.
- Post-Prompt-07 large-archive pipeline decision: future validator and
  metadata checks should reconcile counts, bounds, warnings and rejected-record
  reports without assuming parser or normalizer results were materialized as
  full in-memory tuples.
- Prompt 04/05 normalization model names and count fields:
  `NormalizedOccurrenceRecord`, `RejectedOccurrenceRecord`,
  `OccurrenceNormalizationResult`, `OccurrenceNormalizationCounts`,
  `source_records`, `parsed_records`, `accepted_records` and
  `rejected_records`, plus Prompt 05 `warning_count`,
  `type_conversion_failures` and `warnings`.
- Prompt 03 source-record handoff API for provenance context:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `OccurrenceReadResult` and `OccurrenceSourceRecord`.

## Goal

Implement validation for generated output bundles.

## Tasks

- Validate that `manifest.json`, `metadata/source.json` and `metadata/processing.json` exist and parse.
- Reuse existing fixture roots from Prompt 01, including
  `tests/fixtures/output_bundles/` for valid and invalid bundle fixtures.
- Validate supported schema versions.
- Validate every `manifest.files[].path` exists.
- Validate checksums when `sha256` is present.
- Validate GeoParquet files when declared, including GeoParquet metadata and required projection columns, using required PyArrow checks.
- Run optional GeoParquet-aware validation with `geoparquet-io`, DuckDB and
  Pyogrio/GDAL when installed, recording unavailable tools as structured
  warnings or skipped checks.
- Validate FlatGeobuf declarations and required projection columns when feasible with local dependencies.
- Reconcile row counts across manifest, processing metadata, geospatial outputs and rejected report.
- Validate rejected CSV required columns when the report exists.
- Validate viewer fields are present in data or omitted from `manifest.viewer`.
- Validate `quality_flags` representation, delimiter rule and exact-token
  semantics after splitting on `|`.
- Validate `has_quality_flags` consistency where the output projection
  includes it.
- Validate processing metadata warning counts and type conversion failure
  structures.
- Expose a core validation API with structured result objects.
- Add tests for valid and invalid bundles.

## Constraints

- Do not make validation require optional geospatial dependencies when the
  required PyArrow GeoParquet checks can run; report skipped optional checks as
  warnings.
- Do not change output format silently. If validation reveals spec problems, update `docs/output_format.md` first only when a new accepted decision is warranted.

## Acceptance Criteria

- Valid sample bundles pass.
- Intentionally broken file inventory, counts or required columns fail with actionable errors.
- Validation result can be consumed by CLI and future GUI.
- Tests cover both passing and failing cases.

## Required Session Log

Write `session_logs/YYYY-MM-DD_09_bundle_validation.md` with:

- Validator API summary.
- Checks implemented and dependency-dependent checks.
- Optional validation tool versions and skipped-check behavior.
- Failure cases tested.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `10` and `14` if validation command names, result objects, error structures or validation coverage changed.
