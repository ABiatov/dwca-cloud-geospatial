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
- Expose short names such as `decimalLatitude`, `decimalLongitude`, `scientificName` as output column names when unambiguous.
- Use deterministic fallback names such as `_field_{index}` when a field has no term.
- Keep reserved project columns separate from source Darwin Core fields.

## Core And Extension Relationships

Candidate convention from `dwca2parquet`:

- `_id` in the core table stores the core record identifier from `meta.xml`.
- `_coreid` in extension tables stores the foreign key back to the core `_id`.
- If source fields conflict with reserved names, rename the source columns deterministically and record the rename in metadata.

## Default Values

DwC-A field-level defaults are part of the archive schema and should be applied or explicitly preserved:

- If a defaulted field is missing from the data file, add the output column filled with the default.
- If the field exists but has null or empty values, fill those values only when that matches accepted parser behavior.
- Record default application in metadata so downstream users can distinguish source-provided values from descriptor-provided values.

## Archive Safety

- Inspect zip members without unsafe extraction.
- Reject or sanitize paths with traversal segments or absolute paths.
- Keep overwrite behavior explicit.
- Treat encodings and malformed CSV rows as validation concerns with reported warnings.

## Open Questions

- Whether baseline conversion should depend on an existing DwC-A reader or implement a small project-owned parser.
- Exact semantics for empty strings versus nulls when applying `meta.xml` defaults.
- Whether row numbers should be physical CSV row numbers, logical data row numbers after skipped headers, or both.

