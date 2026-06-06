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
- `docs/dwca_parser.md` if it exists.
- Prompts `01` through `09`
- Latest session logs for prompts `01` through `09`
- Current parser, normalization, writer and validator APIs.

## Goal

Expose repeatable conversion, inspection and validation workflows through a thin public core API and `argparse` CLI.

## Tasks

- Create or refine a core conversion API with explicit input path, output path and options.
- Support default FlatGeobuf conversion.
- Support explicit GeoParquet output selection.
- Enforce overwrite guardrails: existing output paths are rejected unless `--overwrite` is passed.
- Add CLI commands for `convert`, `inspect` and `validate`.
- Keep CLI command handlers thin wrappers around core functions and structured configuration/result objects.
- Return human-readable errors and non-zero exit codes for failed conversions/validations.
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
- `validate` reports structured validation results.

## Required Session Log

Write `session_logs/YYYY-MM-DD_10_core_api_cli.md` with:

- Public API and CLI command summary.
- Overwrite behavior evidence.
- Sample commands tested.
- Verification commands and results.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `11` through `14` if output command syntax, bundle paths, public API names, docs paths or validation invocation changed.
