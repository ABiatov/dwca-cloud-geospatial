# Prompt 03: Occurrence Parser

## Required Skills

- `dwca-archive-parser`: occurrence core reading, row numbering, defaults and Darwin Core field access.
- `planning-artifact-curator`: session log and downstream prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/dwca_parser.md` if it exists.
- `.codex/prompts/dev_flow_description.md`
- Prompts `01` and `02`
- Latest session logs for prompts `01` and `02`
- Current parser/inspection implementation and tests.

## Goal

Read occurrence core rows from inspected DwC-A archives into structured source records suitable for later normalization.

## Tasks

- Implement a streaming or chunked row reader for the occurrence core.
- Use `meta.xml` field mappings for term access.
- Honor declared delimiters, quote characters, encodings and header row counts where available.
- Apply `meta.xml` defaults only when the field has no source column index or the source column is not present in the row shape.
- Preserve `source_file`, physical 1-based `source_row_number`, and logical `source_data_row_number` when available.
- Preserve source row identifiers where available, without inventing GBIF/OBIS IDs.
- Emit row-level diagnostics for parse failures.
- Update `docs/dwca_parser.md` with row-reading behavior.

## Constraints

- Do not normalize coordinates, dates or Darwin Core fields into the final occurrence schema yet.
- Do not write output bundles.
- Keep future raw table export possible by retaining field metadata and relationship keys such as `_id` and `_coreid` when present.

## Acceptance Criteria

- Sample occurrence rows are read through the schema model, not hard-coded positions.
- Physical and data row numbers match the documented semantics.
- Row parse failures are counted and reported with source context.
- Tests cover headers, defaults and at least one malformed row case where practical.

## Required Session Log

Write `session_logs/YYYY-MM-DD_03_occurrence_parser.md` with:

- Source-record model summary.
- Row-numbering and default-handling decisions.
- Tests and sample evidence.
- Open issues affecting normalization.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `04` through `10` and `14` if source-record model names, parser iteration API, diagnostics shape or docs paths changed.
