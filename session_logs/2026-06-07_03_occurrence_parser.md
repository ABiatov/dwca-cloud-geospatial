# Prompt 03: Occurrence Parser

Date: 2026-06-07

## Scope

Implemented occurrence-core row reading as the immediate follow-up to Prompt
02 inspection. This prompt did not normalize coordinates, dates or Darwin Core
fields into the final occurrence schema, did not write output bundles and did
not implement EML content extraction.

## Source-Record Model Summary

- Added `dwca_cloud_geospatial.occurrence.read_occurrence_rows(path)`.
- Added `dwca_cloud_geospatial.occurrence.iter_occurrence_rows(path)` as a
  convenience iterator over successful read results.
- Added `OccurrenceReadResult` with `inspection`, `records`, `diagnostics`,
  `source_file`, `rows_read` and `parse_failures`.
- Added `OccurrenceSourceRecord` with `source_file`, physical
  `source_row_number`, logical `source_data_row_number`, `source_record_id`,
  `values_by_term`, `raw_values`, `field_metadata` and `relationship_keys`.
- `OccurrenceSourceRecord.value_for_term(term)` provides term-based Darwin
  Core access for Prompt 04 normalization.
- Exported the new occurrence reader API from `dwca_cloud_geospatial`.

## Row-Numbering And Default Decisions

- Row reading starts from `inspect_dwca(path).metadata.occurrence_core`.
- Field values are populated from declared `ArchiveField.index` values and
  keyed by Darwin Core term.
- `source_row_number` is the physical 1-based row number in the source data
  file, including skipped headers.
- `source_data_row_number` is the logical 1-based data-record number after
  declared `ignoreHeaderLines`.
- `meta.xml` defaults are applied only when a field has no source column index
  or when the declared source index is outside the row shape.
- Defaults do not replace explicit empty strings or invalid values in present
  source columns.
- `source_record_id` is preserved from the declared core `<id index="...">`
  value when available; no GBIF, OBIS or synthetic identifiers are invented.
- Relationship keys preserve `_id` and `_coreid` when declared.

## Diagnostics Behavior

- Archives with inspection errors return those diagnostics and read no rows.
- Archives without an occurrence core return `missing_occurrence_core`; the
  reader does not attempt to read `taxon.txt` or other non-occurrence core
  files as occurrence rows.
- Occurrence cores declaring more than one file return
  `unsupported_multiple_occurrence_core_files`; multi-file row streaming
  remains deferred.
- CSV parse failures return `occurrence_row_parse_error` with archive, source
  file and best available physical row context, increment `parse_failures` and
  stop reading the affected occurrence core file.
- Source file open/read failures return `occurrence_core_read_error`.

## Tests And Sample Evidence

- Added `tests/test_occurrence_parser.py`.
- Added parser fixtures:
  - `tests/fixtures/dwca/minimal_occurrence/malformed_row/`
  - `tests/fixtures/dwca/minimal_occurrence/multi_file_core/`
- Tests cover term-based field access, header-aware row numbering, defaults,
  source record identifiers, relationship keys, malformed row diagnostics,
  checklist archive rejection and deferred multi-file occurrence cores.
- Real occurrence zip smoke checks:
  - `examples/dwca/0038004-260519110011954.zip` read `1168` occurrence rows
    with `0` parse failures.
  - `examples/dwca/0037981-260519110011954.zip` read `34250` occurrence rows
    with `0` parse failures.
- Checklist example
  `examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`
  remains inspectable but is rejected by row reading with
  `missing_occurrence_core`.

## Files Created Or Updated

- Created `src/dwca_cloud_geospatial/occurrence.py`.
- Updated `src/dwca_cloud_geospatial/__init__.py`.
- Created `tests/test_occurrence_parser.py`.
- Created malformed-row and multi-file occurrence fixtures under
  `tests/fixtures/dwca/minimal_occurrence/`.
- Updated `docs/dwca_parser.md` with occurrence row-reader behavior.
- Updated prompts `04` through `10` and `14` with the Prompt 03 API/model
  handoff.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`.

- `.venv/bin/python -m pytest tests/test_occurrence_parser.py`
  - Result: passed, `4 passed`.
- `.venv/bin/python -m pytest tests`
  - Result: passed, `15 passed`.
- `.venv/bin/python -c "from dwca_cloud_geospatial.occurrence import read_occurrence_rows; from pathlib import Path; p=Path('examples/dwca/0038004-260519110011954.zip'); r=read_occurrence_rows(p); print(r.rows_read, r.parse_failures, [d.code for d in r.diagnostics[-5:]])"`
  - Result: `1168 0 []`.
- `.venv/bin/python -c "from dwca_cloud_geospatial.occurrence import read_occurrence_rows; from pathlib import Path; p=Path('examples/dwca/0037981-260519110011954.zip'); r=read_occurrence_rows(p); print(r.rows_read, r.parse_failures, [d.code for d in r.diagnostics[-5:]])"`
  - Result: `34250 0 []`.

## Open Issues Affecting Normalization

Follow-up clarification: these items are scope boundaries, not blockers before
Prompt 04. Occurrence normalization can start from `OccurrenceSourceRecord`
values produced by the row reader.

- Occurrence rows are source records only; coordinate parsing, coordinate
  validation, date parsing, normalized field naming and rejected-record models
  remain Prompt 04 work.
- Optional field conversion warning thresholds and critical-field rejection
  policy remain Prompt 05 work.
- Multi-file occurrence-core streaming remains deferred until a real sample or
  user need requires it.
- EML content extraction remains deferred to the metadata/source writer work.

## Follow-Up Documentation Consistency Updates

- Updated `docs/dwca_parser.md` to mark parser behavior as accepted for
  inspection and occurrence row reading, and to record the parser-to-
  normalization handoff.
- Updated `docs/development_plan.md` so `Immediate Next Actions` starts with
  Prompt 04 normalization instead of the completed occurrence row iteration.
- Updated `docs/knowledge_base/topics/dwca_archive_parsing.md` and
  `docs/knowledge_base/playbooks/implement_dwca_parser.md` so agent-facing
  parser guidance matches the implemented `OccurrenceSourceRecord` and parser
  diagnostics behavior.
- Confirmed `README.md`, `docs/developer_setup.md`, `docs/output_format.md`
  and ADR-001 did not need changes for this handoff clarification.

## Prompt Updates

- Updated `.codex/prompts/04_occurrence_normalization.md`.
- Updated `.codex/prompts/05_quality_rules.md`.
- Updated `.codex/prompts/06_flatgeobuf_writer.md`.
- Updated `.codex/prompts/07_geoparquet_writer.md`.
- Updated `.codex/prompts/08_manifest_metadata_writers.md`.
- Updated `.codex/prompts/09_bundle_validation.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md` to set
  `04_occurrence_normalization.md` as the canonical current next work item and
  require this pointer to be updated after each prompt.
