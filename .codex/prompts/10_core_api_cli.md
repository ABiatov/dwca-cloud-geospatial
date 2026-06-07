# Prompt 10: Core API And CLI

## Required Skills

- `geospatial-pipeline`: conversion workflow orchestration and CLI/core API boundaries.
- `dwca-archive-parser`: CLI inspection behavior.
- `data-package-spec`: validation and bundle output options.
- `planning-artifact-curator`: session log and prompt maintenance.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md` if it exists.
- Prompts `01` through `09`
- Latest session logs for prompts `01` through `09`
- Current parser, normalization, writer and validator APIs.
- Prompt 03 occurrence row reader API:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `iter_occurrence_rows`, `OccurrenceReadResult` and
  `OccurrenceSourceRecord`.

## Goal

Expose repeatable conversion, inspection and validation workflows through a thin public core API and `argparse` CLI.

## Tasks

- Create or refine a core conversion API with explicit input path, output path and options.
- Support default FlatGeobuf conversion.
- Support explicit GeoParquet output selection.
- Enforce overwrite guardrails: existing output paths are rejected unless `--overwrite` is passed.
- Preserve the existing `inspect <archive>` implementation as a thin wrapper
  around `dwca_cloud_geospatial.inspection.inspect_dwca`, including `--json`
  output and error diagnostics.
- Preserve successful `inspect --json` behavior for valid non-occurrence
  checklist DwC-A archives with `Taxon` cores, including the local examples
  `dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`,
  `dwca-appendixiibernconventionua-v1.2.zip` and
  `dwca-kharkivredliastua-v1.0.zip`.
- Refine the existing `argparse` CLI commands `convert`, `inspect` and
  `validate` exposed by `dwca-cloud-geospatial` without duplicating parser
  logic in CLI handlers.
- Keep CLI command handlers thin wrappers around core functions and structured configuration/result objects.
- Return human-readable errors and non-zero exit codes for failed conversions/validations.
- Make conversion fail fast with an actionable error when the inspected archive
  has no occurrence core or lacks coordinate terms. Checklist/Taxon archives are
  inspectable but outside the MVP occurrence geospatial conversion workflow.
- Reuse the occurrence row reader diagnostics for missing occurrence cores and
  unsupported multi-file occurrence cores instead of duplicating row-reader
  logic in CLI handlers.
- Add or update `docs/converter.md`.
- Add integration tests for CLI success, CLI failure and overwrite behavior.

## Constraints

- Use Python standard library `argparse`.
- Do not add Click or Typer.
- Do not duplicate parser or writer logic in CLI handlers.
- Do not add live download flows.

## Acceptance Criteria

- A user can convert a local sample archive with one CLI command.
- CLI and tests call the same core conversion API.
- Existing output paths are rejected unless `--overwrite` is set.
- `inspect` reports archive/schema information without doing full conversion.
- `inspect --json` succeeds for valid checklist/Taxon DwC-A archives, while
  `convert` rejects them with a clear non-occurrence input error.
- `validate` reports structured validation results.

## Required Session Log

Write `session_logs/YYYY-MM-DD_10_core_api_cli.md` with:

- Public API and CLI command summary.
- Overwrite behavior evidence.
- Sample commands tested.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `11` through `14` if output command syntax, bundle paths, public API names, docs paths or validation invocation changed.
