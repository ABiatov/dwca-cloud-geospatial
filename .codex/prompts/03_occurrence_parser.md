# Prompt 03: Occurrence Parser

## Required Skills

- `dwca-archive-parser`: occurrence core reading, row numbering, defaults and Darwin Core field access.
- `planning-artifact-curator`: session log and downstream prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md` if it exists.
- `.codex/prompts/dev_flow_description.md`
- Prompts `01` and `02`
- Latest session logs for prompts `01` and `02`
- Current parser/inspection implementation and tests.
- Inspection API from Prompt 02:
  `dwca_cloud_geospatial.inspection.inspect_dwca`,
  `ArchiveInspection`, `ArchiveMetadata`, `ArchiveTable`, `ArchiveField` and
  `ParserDiagnostic`.
- Checklist archives inspected after Prompt 02:
  `examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`,
  `examples/dwca/dwca-appendixiibernconventionua-v1.2.zip` and
  `examples/dwca/dwca-kharkivredliastua-v1.0.zip`. These inspect
  successfully as `Taxon` core archives, not occurrence archives.

## Goal

Read occurrence core rows from inspected DwC-A archives into structured source records suitable for later normalization.

## Tasks

- Implement a streaming or chunked row reader for the occurrence core.
- Treat row iteration as the immediate follow-up to Prompt 02 inspection; this
  is the Prompt 02 open question that should be resolved now.
- Use `meta.xml` field mappings for term access.
- Start row reading from `inspect_dwca(path).metadata.occurrence_core`; field
  access should use `ArchiveTable.field_for_term(term)` and declared
  `ArchiveField.index` values.
- Reuse the fixture path contract from Prompt 01:
  `tests/fixtures/dwca/minimal_occurrence/` for small local parser fixtures.
- Honor declared delimiters, quote characters, encodings and header row counts where available.
- Apply `meta.xml` defaults only when the field has no source column index or the source column is not present in the row shape.
- Preserve `source_file`, physical 1-based `source_row_number`, and logical `source_data_row_number` when available.
- Preserve source row identifiers where available, without inventing GBIF/OBIS IDs.
- Emit row-level diagnostics for parse failures.
- If inspection metadata has no occurrence core, do not attempt to read
  `taxon.txt` or other non-occurrence core files as occurrence rows. Return a
  clear parser diagnostic such as `missing_occurrence_core` with archive and
  `meta.xml` context.
- If an occurrence core declares more than one file location, do not stream it
  yet; return a clear parser diagnostic with source metadata context. Multi-file
  table streaming remains deferred until a real sample or user need requires it.
- Update `docs/dwca_parser.md` with row-reading behavior.

## Constraints

- Do not normalize coordinates, dates or Darwin Core fields into the final occurrence schema yet.
- Do not write output bundles.
- Do not implement EML content extraction in this prompt. Inspection already
  preserves the declared metadata file path; full EML extraction is deferred to
  the metadata/source writer work.
- Keep future raw table export possible by retaining field metadata and relationship keys such as `_id` and `_coreid` when present.

## Acceptance Criteria

- Sample occurrence rows are read through the schema model, not hard-coded positions.
- Taxon-core/checklist archives are rejected by the occurrence row reader with
  actionable diagnostics, while remaining valid inputs for `inspect`.
- Physical and data row numbers match the documented semantics.
- Row parse failures are counted and reported with source context.
- Tests cover headers, defaults and at least one malformed row case where practical.

## Required Session Log

Write `session_logs/YYYY-MM-DD_03_occurrence_parser.md` with:

- Source-record model summary.
- Row-numbering and default-handling decisions.
- Tests and sample evidence.
- Open issues affecting normalization.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `04` through `10` and `14` if source-record model names, parser iteration API, diagnostics shape or docs paths changed.
