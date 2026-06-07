# Prompt 02: DwC-A Inspection

Date: 2026-06-07

## Scope

Implemented safe local Darwin Core Archive inspection for zip archives and
unpacked DwC-A directories. This prompt did not implement row normalization,
coordinate validation, geospatial conversion or output bundle writing.

## Inspection API And Data Model Summary

- Added `dwca_cloud_geospatial.inspection.inspect_dwca(path)`.
- Exported `inspect_dwca` from `dwca_cloud_geospatial`.
- Added structured inspection models:
  - `ArchiveInspection`
  - `ArchiveMetadata`
  - `ArchiveTable`
  - `ArchiveField`
  - `DelimitedTextFormat`
  - `ParserDiagnostic`
- `ArchiveMetadata` exposes declared files, occurrence-core detection and
  coordinate-term presence.
- `ArchiveTable` preserves row type, declared files, `_id` and `_coreid`
  indexes, field declarations and delimited text settings.
- `ArchiveField` preserves Darwin Core term, source index, default value and
  per-field delimiter.
- Field access is term-based through `ArchiveTable.field_for_term(term)`.

## CLI Summary

- Implemented `dwca-cloud-geospatial inspect <archive>` as a thin wrapper
  around `inspect_dwca`.
- Added `dwca-cloud-geospatial inspect --json <archive>` for structured output.
- `inspect` exits `0` when there are no error diagnostics and `1` when parser
  errors are present.
- `convert` and `validate` remain planned-command stubs.

## Safe Archive Behavior

- Zip archives are inspected in place and are not extracted.
- Zip entries are rejected before metadata parsing when they contain absolute
  paths, parent-directory traversal, repeated separators, Windows drive-style
  prefixes or backslash separators.
- Unpacked directories must contain `meta.xml` at the requested directory root.
- Declared metadata/core/extension file paths are checked for traversal before
  existence checks.
- Nested zip `meta.xml` files are supported only when unambiguous; declared
  files are checked relative to the nested metadata directory.

## Diagnostics Behavior

Diagnostics include severity, stable code, message, source and optional
context. Current diagnostics cover missing input paths, unsupported input
paths, missing or malformed `meta.xml`, missing core declarations, missing
declared files, unsafe zip entry paths, unsafe declared file paths, unsupported
multiple table files and invalid integer metadata attributes.

Parser errors include source context. Example: the missing metadata fixture
reports `missing_meta_xml` with source
`tests/fixtures/dwca/minimal_occurrence/missing_meta` and context `meta.xml`.

## Sample Archives Tested

- `examples/dwca/0038004-260519110011954.zip`: inspected successfully.
- `examples/dwca/0037981-260519110011954.zip`: inspected successfully.
- `examples/dwca/0038004-260519110011954`: inspected successfully.
- `examples/dwca/0037981-260519110011954`: inspected successfully.
- `examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`:
  inspected successfully as a `Taxon` core checklist archive with no
  occurrence core and no coordinate terms.
- `examples/dwca/dwca-appendixiibernconventionua-v1.2.zip`: inspected
  successfully as a `Taxon` core checklist archive with no occurrence core and
  no coordinate terms.
- `examples/dwca/dwca-kharkivredliastua-v1.0.zip`: inspected successfully as a
  `Taxon` core checklist archive with no occurrence core and no coordinate
  terms.
- `tests/fixtures/dwca/minimal_occurrence/valid`: inspected successfully.
- `tests/fixtures/dwca/minimal_occurrence/missing_meta`: produced expected
  missing metadata error.
- `tests/fixtures/dwca/minimal_occurrence/malformed_meta`: produced expected
  malformed metadata error.

## Files Created Or Updated

- Created `src/dwca_cloud_geospatial/inspection.py`.
- Updated `src/dwca_cloud_geospatial/__init__.py`.
- Updated `src/dwca_cloud_geospatial/cli.py`.
- Created `docs/dwca_parser.md`.
- Updated `README.md`.
- Updated `docs/developer_setup.md`.
- Created minimal DwC-A inspection fixtures under
  `tests/fixtures/dwca/minimal_occurrence/`.
- Created `tests/test_dwca_inspection.py`.
- Updated `tests/test_cli.py`.
- Updated `.codex/prompts/03_occurrence_parser.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`.

- `.venv/bin/python -m pytest tests`
  - Result: passed, `11 passed`.
- `.venv/bin/dwca-cloud-geospatial inspect examples/dwca/0038004-260519110011954.zip`
  - Result: exit `0`; occurrence core and coordinate fields reported; no
    diagnostics.
- `.venv/bin/dwca-cloud-geospatial inspect examples/dwca/0037981-260519110011954.zip`
  - Result: exit `0`; occurrence core and coordinate fields reported; no
    diagnostics.
- `.venv/bin/dwca-cloud-geospatial inspect examples/dwca/0038004-260519110011954`
  - Result: exit `0`; occurrence core and coordinate fields reported; no
    diagnostics.
- `.venv/bin/dwca-cloud-geospatial inspect examples/dwca/0037981-260519110011954`
  - Result: exit `0`; occurrence core and coordinate fields reported; no
    diagnostics.
- `.venv/bin/dwca-cloud-geospatial inspect --json examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`
  - Result: exit `0`; `Taxon` core reported; no occurrence core, no coordinate
    terms and no diagnostics.
- `.venv/bin/dwca-cloud-geospatial inspect --json examples/dwca/dwca-appendixiibernconventionua-v1.2.zip`
  - Result: exit `0`; `Taxon` core reported; no occurrence core, no coordinate
    terms and no diagnostics.
- `.venv/bin/dwca-cloud-geospatial inspect --json examples/dwca/dwca-kharkivredliastua-v1.0.zip`
  - Result: exit `0`; `Taxon` core reported; no occurrence core, no coordinate
    terms and no diagnostics.
- `.venv/bin/dwca-cloud-geospatial inspect --json tests/fixtures/dwca/minimal_occurrence/valid`
  - Result: exit `0`; structured JSON included core fields, defaults,
    indexes and text settings.
- `.venv/bin/dwca-cloud-geospatial inspect tests/fixtures/dwca/minimal_occurrence/missing_meta`
  - Result: exit `1`; `missing_meta_xml` diagnostic included source path and
    `meta.xml` context.

## Open Questions Or Risks

- Resolved follow-up decision: row iteration is the only item that must be
  addressed immediately, and it belongs in Prompt 03.
- Resolved follow-up decision: multiple file locations for one core or
  extension table remain diagnostic-only for now. Prompt 03 should return a
  clear parser diagnostic rather than attempting multi-file table streaming.
- Resolved follow-up decision: EML content extraction is deferred to the
  metadata/source writer work. Inspection preserves the declared metadata file
  path until then.
- Resolved follow-up decision: checklist archives with `Taxon` cores remain
  valid inputs for inspection, but they are not occurrence geospatial
  conversion inputs for the MVP. Occurrence row reading and conversion should
  reject them with actionable non-occurrence diagnostics.

## Prompt Updates

- Updated `.codex/prompts/03_occurrence_parser.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
