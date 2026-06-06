# Prompt 01: Project Skeleton

## Required Skills

- `planning-artifact-curator`: record setup decisions, evidence and next actions in `session_logs/`.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `.codex/prompts/dev_flow_description.md`
- Any existing `session_logs/*.md` that mention repository/package setup.

## Goal

Create the minimal Python project skeleton needed for the MVP implementation without adding converter behavior yet.

## Tasks

- Add Python packaging configuration using a conservative modern layout.
- Create the core package namespace for the converter.
- Add an `argparse`-based CLI entry point stub with help text.
- Add test framework configuration and fixture layout.
- Add or update developer documentation for installing the package locally, running tests and invoking CLI help.
- Keep all paths explicit; do not rely on hidden working-directory assumptions.

## Constraints

- Do not implement DwC-A parsing, normalization, writers, viewer or GUI in this prompt.
- Do not introduce Click or Typer.
- Do not add required database, backend service, scheduler, cloud runtime, live GBIF/OBIS integration, taxonomy matching, PMTiles, or packaged desktop binary scope.

## Acceptance Criteria

- `python -m pytest` runs.
- The CLI exposes help text.
- Sample fixtures are addressable through explicit paths.
- Repository documentation shows the minimal development commands.

## Required Session Log

Write `session_logs/YYYY-MM-DD_01_project_skeleton.md` with:

- Files created or updated.
- Package and CLI decisions.
- Verification commands and results.
- Open questions or risks.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

After implementation, update prompts `02` through `14` if package names, CLI command names, test commands, fixture paths or documentation paths differ from the assumptions in this sequence.
