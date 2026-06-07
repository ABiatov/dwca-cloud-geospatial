---
id: dwca-archive-parsing
status: candidate
applies_to:
  - DwC-A parsing
  - field mapping and normalization
  - metadata/provenance
sources:
  - examples/code/dwca2parquet/REFERENCE.md
  - examples/code/python-dwca-reader/
  - examples/code/dwca-tools/
---

# DwC-A Archive Parsing

## Use In This Project

Parse Darwin Core Archive inputs from the archive descriptor, not from hard-coded column positions. `meta.xml` should drive file discovery, field names, defaults, delimiters, headers, IDs, core tables, and extensions.

## Parser Responsibilities

- Locate `meta.xml` at the DwC-A archive root.
- Parse the core file declaration: filename, row type, encoding, delimiter, line terminator, quote character, header lines, and ID field.
- Parse extension declarations with their `coreid` field.
- Parse field definitions, including field index, term URI, short name, and optional default value.
- Preserve `eml.xml` or other source metadata when present.
- Stream table rows where possible; do not require full archives to fit in memory.
- Track enough lineage to identify source archive, source file, row number or source ID, row type, and applied parsing rule version.

## Field Naming

Preferred internal model:

- Keep full term URIs in schema metadata.
- Expose short names such as `decimalLatitude`, `decimalLongitude`, `scientificName` only in internal parser/source schema metadata or future raw table exports when unambiguous.
- MVP normalized occurrence outputs must use the accepted snake_case project field names from `docs/output_format.md`, not Darwin Core camelCase source terms.
- Use deterministic fallback names such as `_field_{index}` when a field has no term.
- Keep reserved project columns separate from source Darwin Core fields.

## Core And Extension Relationships

Candidate convention from `dwca2parquet`:

- `_id` in the core table stores the core record identifier from `meta.xml`.
- `_coreid` in extension tables stores the foreign key back to the core `_id`.
- If source fields conflict with reserved names, rename the source columns deterministically and record the rename in metadata.

## Default Values

DwC-A field-level defaults are part of the archive schema and should be applied or explicitly preserved:

- Apply `meta.xml` field defaults only when the declared field has no source column index or the source column is not present in the row shape.
- Do not use defaults to replace explicit empty strings or invalid source values in present columns.
- Normalize explicit empty strings as null for typed/normalized fields.
- Preserve raw source values where raw fields are retained.
- Record default application in processing metadata so downstream users can distinguish source-provided values from descriptor-provided values.

## Archive Safety

- Inspect zip members without unsafe extraction.
- Reject or sanitize paths with traversal segments or absolute paths.
- Keep overwrite behavior explicit.
- Treat encodings and malformed CSV rows as parser concerns with structured
  diagnostics. Occurrence-core row parse failures currently emit
  `occurrence_row_parse_error` diagnostics with source file and row context.

## Resolved By Accepted Docs

- Baseline parsing belongs in the project-owned Python core library layer. `docs/development_plan.md` M1 requires safe archive inspection, a `meta.xml` parser, occurrence core detection, chunked row reading, metadata file discovery and parser diagnostics; full EML content extraction is deferred to metadata/source writer work. ADR-001 requires CLI, GUI and future integrations to call the same core conversion APIs.
- The Prompt 03 row reader API is `dwca_cloud_geospatial.occurrence.read_occurrence_rows(path)`. It returns `OccurrenceReadResult` with `OccurrenceSourceRecord` entries for later normalization.
- Output provenance must include `source_record_id`, `source_file` and `source_row_number`, per `docs/development_plan.md` M2 and `docs/output_format.md`.
- `source_row_number` is the physical 1-based row number in the source data file, including skipped header rows. `source_data_row_number` is the logical 1-based data-record number after declared header rows when available. Diagnostics and rejection reports should include both values where practical.
- `meta.xml` field defaults are applied only when the declared field has no source column index or the source column is not present in the row shape; they are not used to replace explicit empty strings or invalid source values in present columns.
- Occurrence row reading is complete enough to start normalization; deferred multi-file occurrence-core streaming and EML content extraction are not blockers for Prompt 04.

## Open Questions

- None currently.
