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
- Prompts `01` through `12`
- Latest session logs for prompts `01` through `12`
- Current core conversion API, CLI and viewer launch instructions.
- Prompt 04 normalization result boundaries so GUI status/count displays use
  accepted/rejected counts from the core workflow rather than re-normalizing
  occurrence rows.
- Prompt 05 normalization result additions so GUI status can display
  `warning_count` and optional conversion warnings from the core workflow
  without treating them as conversion failures.

## Goal

Implement a primitive `tkinter` desktop entry point for non-CLI users while reusing the same core conversion API.

## Tasks

- Add a GUI module or entry point using `tkinter`.
- Let users choose input archive and output directory.
- Provide output format options consistent with the CLI: FlatGeobuf default and explicit GeoParquet when supported.
- Add an overwrite checkbox required before replacing an existing output path.
- Show progress/status and actionable errors.
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
