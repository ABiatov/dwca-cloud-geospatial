# Prompt 13: Tkinter GUI

## Required Skills

- `geospatial-pipeline`: reuse core conversion API and preserve workflow behavior.
- `data-package-spec`: output bundle options and validation handoff.
- `planning-artifact-curator`: session log and final prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/converter.md` if it exists.
- `docs/viewer_contract.md` if it exists.
- Prompts `01` through `12`, including `10b` and `10c`
- Latest session logs for prompts `01` through `12`, including `10b` and `10c`
  when present
- Current core conversion API, CLI and viewer launch instructions.
- Prompt 10 core conversion API:
  `dwca_cloud_geospatial.conversion.convert_dwca_archive`,
  `ConversionOptions`, `ConversionResult`, `ConversionError`,
  `FLATGEOBUF_FORMAT`, `GEOPARQUET_FORMAT` and
  `SUPPORTED_OUTPUT_FORMATS`. GUI conversion must call this API instead of
  parsing, normalizing, writing geospatial files or writing bundle metadata
  directly.
- Prompt 10 output and overwrite behavior: default conversion writes
  FlatGeobuf, explicit GeoParquet uses output format `geoparquet`, both
  formats can be requested together, and existing output paths are rejected
  unless `ConversionOptions(overwrite=True)` is set by the GUI overwrite
  checkbox.
- Prompt 10 CLI reference syntax for docs/UI copy:
  `dwca-cloud-geospatial convert <archive> <output> [--format flatgeobuf]
  [--format geoparquet] [--overwrite]` and
  `dwca-cloud-geospatial validate [--json] <bundle>`.
- Prompt 08 bundle metadata writer APIs used by core conversion:
  `dwca_cloud_geospatial.bundle.write_bundle_metadata`,
  `BundleWriterOptions` and `BundleMetadataWriteResult`. GUI code should use
  the core conversion API that calls these writers rather than writing
  manifests, processing metadata or rejected-record reports directly.
- Prompt 08 output behavior: `reports/rejected_records.csv` is written only
  when rejected records exist, and `metadata/processing.json.warnings`
  preserves FlatGeobuf writer warnings such as
  `large_indexed_flatgeobuf_write`.
- Prompt 09 validation API:
  `dwca_cloud_geospatial.validation.validate_output_bundle`,
  `BundleValidationResult`, `BundleValidationIssue` and
  `BundleValidationCheck`. GUI validation status should consume the core
  validator result instead of reimplementing bundle checks.
- Prompt 09 validation result behavior: `BundleValidationResult.status` is
  `passed`, `passed_with_warnings` or `failed`; `.has_errors` determines
  whether validation failed, while dependency-dependent optional-reader skips
  are surfaced through `.warnings`, `.checks` and `.skipped_checks`.
- Prompt 04 normalization result boundaries so GUI status/count displays use
  accepted/rejected counts from the core workflow rather than re-normalizing
  occurrence rows.
- Prompt 05 normalization result additions so GUI status can display
  `warning_count` and optional conversion warnings from the core workflow
  without treating them as conversion failures.
- Prompt 06 FlatGeobuf behavior: default conversion uses
  `data/occurrences.fgb` with `SPATIAL_INDEX=YES`. Large indexed writes
  emit structured warning code `large_indexed_flatgeobuf_write`; GUI status
  should surface that as a warning, not a failure.
- Prompt 06 dependency setup: FlatGeobuf-capable development installs use
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"`. If the core API
  raises `FlatGeobufDependencyError`, GUI errors should preserve its actionable
  dependency message.
- Prompt 10b/10c large-output handoff: GUI options should expose only large-output
  controls implemented by the core API. Implemented controls are GeoParquet
  `large_output_mode`, chunk size and the default `grid` spatial sort through
  `GeoParquetWriterOptions`; partitioned GeoParquet mode is not implemented
  and should preserve the core actionable error if requested. FlatGeobuf
  conversion uses chunked GeoPackage staging at `data/occurrences.gpkg`; show
  non-fatal large-output warnings separately from conversion failures because
  GDAL may still need substantial memory while building the final FlatGeobuf
  spatial index.
- Prompt 10c optimized FlatGeobuf handoff when present: default FlatGeobuf
  conversion may create both `data/occurrences.fgb` and persistent
  `data/occurrences.gpkg`. GUI status should show both artifacts when present
  and preserve actionable dependency errors for missing `.venv` GDAL/OGR,
  Pyogrio or GeoPackage helper tooling.

## Goal

Implement a primitive `tkinter` desktop entry point for non-CLI users while reusing the same core conversion API.

## Tasks

- Add a GUI module or entry point using `tkinter`.
- Let users choose input archive and output directory.
- Provide output format options consistent with the CLI: FlatGeobuf default and explicit GeoParquet when supported.
- If exposing a large-output option, constrain or label it as GeoParquet-only
  according to `docs/converter.md`.
- Add an overwrite checkbox required before replacing an existing output path.
- Show progress/status and actionable errors.
- Show non-fatal conversion warnings, including large FlatGeobuf indexed-write
  warnings, separately from conversion failures.
- Show generated GeoPackage staging artifact paths when core conversion
  returns them.
- When exposing validation in the GUI, display required validation errors
  separately from dependency-dependent skipped checks and warnings.
- Provide a way to open the generated output directory or show viewer instructions.
- Add tests for GUI-adjacent logic where possible without requiring an interactive display.
- Document GUI usage in `docs/converter.md` or another accepted docs path.

## Constraints

- Do not duplicate parsing, normalization, writing or validation logic in the GUI.
- Do not create standalone packaged desktop binaries.
- Do not require GUI availability for headless test runs.

## Acceptance Criteria

- GUI conversion uses the same core API as CLI conversion.
- Existing output paths are guarded by the overwrite checkbox.
- Errors preserve actionable messages from the core workflow.
- Headless-safe tests cover non-visual GUI logic where practical.

## Required Session Log

Write `session_logs/YYYY-MM-DD_13_tkinter_gui.md` with:

- GUI entry point and behavior summary.
- Core API reuse evidence.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- Any manual testing limitations.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompt `14` if GUI command names, docs paths, viewer instructions, test commands or known limitations changed.
