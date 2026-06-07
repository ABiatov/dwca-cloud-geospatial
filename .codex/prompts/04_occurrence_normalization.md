# Prompt 04: Occurrence Normalization

## Required Skills

- `geospatial-pipeline`: occurrence normalization, coordinate parsing, field mapping and rejection model.
- `dwca-archive-parser`: Darwin Core term semantics and source provenance.
- `planning-artifact-curator`: record decisions and update downstream prompts.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md` if it exists.
- Prompts `01` through `03`
- Latest session logs for prompts `01` through `03`
- Current parser/source-record implementation and tests.
- Prompt 03 occurrence row reader API:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `iter_occurrence_rows`, `OccurrenceReadResult` and
  `OccurrenceSourceRecord`.
- Post-Prompt-03 handoff clarification: there are no parser blockers that
  must be resolved before starting Prompt 04. The `Open Issues Affecting
  Normalization` in `session_logs/2026-06-07_03_occurrence_parser.md` are
  scope boundaries: normalization belongs here, quality thresholds belong to
  Prompt 05, multi-file occurrence-core streaming remains deferred, and EML
  extraction belongs to Prompt 08.

## Goal

Convert parsed source records into the normalized occurrence schema and rejected-record model accepted by the MVP output contract.

## Tasks

- Define normalized occurrence data structures or schema using stable snake_case field names.
- Consume `OccurrenceSourceRecord` values through `value_for_term(term)` or
  `values_by_term`; do not hard-code source positions.
- Map Darwin Core terms into the canonical fields documented in `docs/output_format.md`.
- Reuse existing test fixture roots from Prompt 01; add normalization fixtures
  under `tests/fixtures/` only with explicit paths.
- Parse longitude and latitude into numeric `decimal_longitude` and `decimal_latitude`.
- Validate coordinate ranges and prepare rejection reason codes for coordinate failures.
- Normalize `event_date` and derive `event_year` where practical.
- Preserve required provenance fields: `source_record_id`, `source_file`, `source_row_number`, and `source_data_row_number` when available.
- Preserve nullable dataset, GBIF and OBIS provenance fields only when present in source metadata or records.
- Create the rejected-record model aligned with `reports/rejected_records.csv`, but do not require writing the CSV in this prompt.
- Add focused tests for accepted and rejected records.
- Do not treat Prompt 03 deferred multi-file occurrence-core streaming or EML
  extraction as prerequisites for normalization.

## Constraints

- Do not write FlatGeobuf, GeoParquet, manifest or metadata files yet.
- Do not add taxonomy matching or enrichment.
- Do not expose source camelCase terms as normalized output fields.

## Acceptance Criteria

- Valid coordinate records become normalized accepted occurrence records.
- Missing or invalid coordinate records become rejected records with stable reason codes.
- Accepted and rejected counts reconcile for sample records.
- Tests cover field mapping, coordinate parsing, date/year handling and provenance preservation.

## Required Session Log

Write `session_logs/YYYY-MM-DD_04_occurrence_normalization.md` with:

- Normalized schema/model summary.
- Rejection model summary.
- Mapping decisions and any deviations from `docs/output_format.md`.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `05` through `14` if normalized model names, field names, reason codes, count structures or API boundaries changed.
