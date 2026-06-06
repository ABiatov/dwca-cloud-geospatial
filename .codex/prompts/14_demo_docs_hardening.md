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
- `docs/dwca_parser.md` if it exists.
- `docs/converter.md` if it exists.
- `docs/viewer_contract.md` if it exists.
- `docs/deployment.md` if it exists.
- All prompts `01` through `13`
- Latest session logs for prompts `01` through `13`
- Current tests, examples and generated sample bundle instructions.

## Goal

Make the MVP understandable, repeatable and ready for external review.

## Tasks

- Run or refresh an end-to-end sample conversion note using local DwC-A examples.
- Update README with current installation, CLI, GUI and viewer usage.
- Complete or update `docs/dwca_parser.md`, `docs/converter.md`, `docs/viewer_contract.md` and `docs/deployment.md`.
- Confirm `docs/output_format.md` matches implemented bundle behavior.
- Add regression tests for parser behavior, normalization, output writing and bundle validation where gaps remain.
- Add known limitations and MVP+ roadmap, including PMTiles as deferred.
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
- Known remaining limitations.
- Suggested next MVP+ prompts or ADRs.
- `Prompt Updates`: list prompt files changed, or `None`.

## Prompt Maintenance

If this session changes accepted decisions, update canonical docs and this prompt flow description. If it identifies new MVP+ work, create new numbered prompts only after the MVP prompt sequence remains internally consistent.
