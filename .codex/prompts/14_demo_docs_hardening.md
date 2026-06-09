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
- All prompts `01` through `13`
- Latest session logs for prompts `01` through `13`
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
- Add regression tests for parser behavior, normalization, output writing and bundle validation where gaps remain.
- Add known limitations and MVP+ roadmap, including PMTiles as deferred.
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
