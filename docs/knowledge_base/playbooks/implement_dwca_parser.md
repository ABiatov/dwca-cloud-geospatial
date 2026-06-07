---
id: implement-dwca-parser-playbook
status: candidate
applies_to:
  - DwC-A parsing
  - field mapping and normalization
  - metadata/provenance
sources:
  - docs/knowledge_base/topics/dwca_archive_parsing.md
  - examples/code/dwca2parquet/REFERENCE.md
  - examples/code/dwca-tools/
---

# Implement DwC-A Parser

## Goal

Build a safe parser that reads a DwC-A archive descriptor and streams declared core and extension rows into structured table batches.

## Steps

1. Inspect the archive without extracting files.
2. Reject unsafe member paths.
3. Locate and parse root `meta.xml`.
4. Build schema objects for core and extension files.
5. Resolve full term URIs and short column names.
6. Read CSV rows using delimiter, quote, encoding, and header settings from `meta.xml`.
7. Apply or preserve default values according to accepted policy.
8. Add source lineage fields or metadata.
9. Emit `OccurrenceSourceRecord` entries through a structured result object
   and report row parse failures as diagnostics with source context.
10. Add fixture tests for small archives, missing files, defaults, extensions, malformed rows and non-occurrence checklist archives.

## Acceptance Evidence

- Parser handles a small valid DwC-A fixture.
- Parser reports missing declared files.
- Parser preserves core-extension relationships.
- Parser refuses unsafe archive paths.
- Tests cover at least one archive with defaults and one archive with an extension.

## Related Topics

- `../topics/dwca_archive_parsing.md`
- `../topics/validation_and_quality.md`
