# Prompt Flow Creation

Date: 2026-06-06

## Scope

Created the ordered MVP implementation prompt flow requested by the user.

## Files Created Or Updated

- Updated `.codex/prompts/dev_flow_description.md` with operating rules, prompt sequence, artifact handoff map and prompt maintenance protocol.
- Created `.codex/prompts/01_project_skeleton.md`.
- Created `.codex/prompts/02_dwca_inspection.md`.
- Created `.codex/prompts/03_occurrence_parser.md`.
- Created `.codex/prompts/04_occurrence_normalization.md`.
- Created `.codex/prompts/05_quality_rules.md`.
- Created `.codex/prompts/06_flatgeobuf_writer.md`.
- Created `.codex/prompts/07_geoparquet_writer.md`.
- Created `.codex/prompts/08_manifest_metadata_writers.md`.
- Created `.codex/prompts/09_bundle_validation.md`.
- Created `.codex/prompts/10_core_api_cli.md`.
- Created `.codex/prompts/11_viewer_contract.md`.
- Created `.codex/prompts/12_static_viewer.md`.
- Created `.codex/prompts/13_tkinter_gui.md`.
- Created `.codex/prompts/14_demo_docs_hardening.md`.

## Decisions Recorded

- The MVP prompt flow follows the accepted milestone sequence from `docs/development_plan.md`.
- Each prompt explicitly names required skills.
- Each prompt requires reading earlier prompt/session artifacts before implementation.
- Each prompt requires writing a `session_logs/YYYY-MM-DD_<prompt-number>_<short-name>.md` handoff.
- Each prompt requires updating later prompt files when implementation changes downstream assumptions.
- The flow keeps the accepted MVP scope: local file-based conversion, static outputs and static viewer; no required backend, database, live GBIF/OBIS download, taxonomy matching, PMTiles or packaged desktop binary.

## Verification

- Listed `.codex/prompts/` and confirmed numbered prompt files `01` through `14` plus `dev_flow_description.md`.
- Searched prompt files for required sections: `Required Skills`, `Context To Read First`, `Required Session Log`, `Prompt Maintenance` and `session_logs`.

## Open Questions

- None for the prompt-flow artifact itself.

## Prompt Updates

- None. This session created the initial prompt sequence.
