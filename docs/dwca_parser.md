# DwC-A Parser

Status: Accepted parser behavior for inspection and occurrence row reading

## Scope

The current parser implementation supports safe inspection of local Darwin
Core Archives and occurrence-core row reading. It parses `meta.xml`, reports
archive structure and reads occurrence source rows into parser-level source
records. It does not normalize coordinates, normalize dates, validate Darwin
Core values into the final occurrence schema or write geospatial output
bundles.

Supported inputs:

- `.zip` Darwin Core Archives.
- Unpacked DwC-A directories with `meta.xml` at the directory root.

## Inspection API

Use `dwca_cloud_geospatial.inspection.inspect_dwca(path)` to inspect an
archive. It returns an `ArchiveInspection` dataclass with:

- `source_path`, `archive_kind`, optional source size and archive SHA-256.
- `meta_path` for the located `meta.xml`.
- `metadata`, an `ArchiveMetadata` model when `meta.xml` can be parsed.
- `diagnostics`, a tuple of `ParserDiagnostic` entries.

`ArchiveMetadata` models the declared metadata file, core table, extension
tables, declared file inventory, occurrence-core detection and coordinate-term
presence.

`ArchiveTable` models each core or extension table with row type, declared
files, `_id` or `_coreid` indexes, field declarations and delimited text
settings. `ArchiveField` preserves the Darwin Core term, source index, default
value and per-field delimiter.

## Occurrence Row Reader API

Use `dwca_cloud_geospatial.occurrence.read_occurrence_rows(path)` to read the
declared occurrence core. It returns an `OccurrenceReadResult` with:

- `inspection`, the `ArchiveInspection` produced by `inspect_dwca`.
- `records`, a tuple of `OccurrenceSourceRecord` entries.
- `diagnostics`, including inspection diagnostics and row-reader diagnostics.
- `source_file`, the single occurrence core file location when row reading
  starts.
- `rows_read` and `parse_failures` counts.

`OccurrenceSourceRecord` preserves parser-level source evidence for later
normalization:

- `source_file`.
- physical 1-based `source_row_number`, including skipped header rows.
- logical 1-based `source_data_row_number`, counted after declared header
  rows.
- `source_record_id` from the declared core `<id index="...">` when present
  in the row.
- `values_by_term`, keyed by declared Darwin Core term.
- `raw_values`, the unnormalized source row cells.
- `field_metadata`, the declared `ArchiveField` entries used to build
  `values_by_term`.
- `relationship_keys`, including `_id` and `_coreid` when declared and
  available.

`OccurrenceSourceRecord.value_for_term(term)` returns the term value from
`values_by_term`. Later normalization code should use this method or the
mapping instead of hard-coded source positions.

## Accepted Behavior

`meta.xml` is the source of truth for core and extension table structure.
Field access must use declared terms and indexes from `ArchiveField`; row
reading and normalization code must not hard-code source columns outside this
schema model.

Zip archives are inspected in place. The parser does not extract zip contents.
Before reading `meta.xml`, every zip entry path is checked for absolute paths,
parent-directory traversal and unsafe path separators. Archives with unsafe
entries return an error diagnostic and are not parsed further.

Unpacked directories are read directly from the requested directory. Declared
file paths in `meta.xml` are also checked for traversal before existence
checks.

The MVP row reader supports one file location for the occurrence core.
Inspection records every declared location and emits an
`unsupported_multiple_table_files` warning when a table declares more than one
file. Occurrence row reading returns an
`unsupported_multiple_occurrence_core_files` error for multi-file occurrence
cores and does not stream them yet.

Occurrence-core detection is based on the core row type
`http://rs.tdwg.org/dwc/terms/Occurrence`. Coordinate-field presence is based
on declared Darwin Core terms:

- `http://rs.tdwg.org/dwc/terms/decimalLatitude`
- `http://rs.tdwg.org/dwc/terms/decimalLongitude`

## Checklist And Non-Occurrence Archives

Valid DwC-A archives may declare a `Taxon` core instead of an `Occurrence`
core. These archives are valid inputs for `inspect`, but they are not valid
inputs for the MVP occurrence geospatial conversion workflow unless a future
feature adds checklist/taxon-specific processing.

Current local checklist examples:

- `examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`
- `examples/dwca/dwca-appendixiibernconventionua-v1.2.zip`
- `examples/dwca/dwca-kharkivredliastua-v1.0.zip`

All three inspect successfully with `dwca-cloud-geospatial inspect --json`.
They declare `http://rs.tdwg.org/dwc/terms/Taxon` cores, have no occurrence
core and do not declare `decimalLatitude` or `decimalLongitude` terms.

The occurrence row reader fails fast for these archives with the
`missing_occurrence_core` parser diagnostic. Later conversion commands should
preserve the same boundary: checklist archives remain inspectable, but
conversion should reject them with an actionable non-occurrence input error.

## Row Reading Behavior

Occurrence rows are read only from
`inspect_dwca(path).metadata.occurrence_core`. If inspection has parser errors,
or if metadata is unavailable, no rows are read and diagnostics are returned.
If the archive has no occurrence core, the reader returns
`missing_occurrence_core` and does not attempt to read `taxon.txt` or any
other non-occurrence core table as occurrence data.

The row reader opens unpacked archive files directly and zip archive members
in place. It does not extract zip archives. For nested zip `meta.xml` files,
declared occurrence file paths are resolved relative to the located
`meta.xml` directory.

Delimited text reading honors the occurrence core settings declared in
`meta.xml` where supported by Python's CSV reader:

- `encoding`.
- `fieldsTerminatedBy`.
- `fieldsEnclosedBy`, including no quote character when blank.
- `ignoreHeaderLines`.

Rows are streamed from the source file and collected into
`OccurrenceReadResult.records` for the current parser handoff. This keeps the
source-file read bounded to one row at a time while giving Prompt 04
normalization a simple result object to consume.

Defaults from `meta.xml` are applied only when a declared `ArchiveField` has
no source column index or when its source column index is outside the row
shape. Defaults do not replace explicit empty strings or invalid values in
present source columns.

Row numbering follows the accepted provenance semantics:

- `source_row_number` is the physical 1-based row number in the source data
  file, including skipped header rows.
- `source_data_row_number` is the logical 1-based data-record number after
  declared header rows.

CSV parse failures emit `occurrence_row_parse_error` diagnostics with archive,
file and best available row context. They increment `parse_failures` and stop
reading the affected occurrence core file.

## Parser To Normalization Handoff

Occurrence row reading is complete enough to start occurrence normalization.
There are no parser blockers that must be resolved before the normalization
work begins.

`OccurrenceSourceRecord` entries are intentionally source records only. They
preserve term-addressable values, raw row cells, field metadata, source file,
row numbers and relationship keys, but they do not parse or validate
coordinates, normalize dates, assign project field names or build rejected
records. Those responsibilities belong to the normalization and quality-rule
stages.

Deferred parser-adjacent work should not block normalization:

- Multi-file occurrence-core streaming remains deferred until a real sample or
  user need requires it.
- EML content extraction remains deferred to the source metadata writer, which
  will read the declared `ArchiveMetadata.metadata_file` when available.
- Optional-field warning thresholds and critical-field rejection policy belong
  to the quality-rule stage, not the row reader.

## Diagnostics

Diagnostics include severity, stable code, message, source and optional
context. Current parser diagnostics cover:

- Missing input paths.
- Unsupported input paths.
- Missing, ambiguous or malformed `meta.xml`.
- Missing core table declarations.
- Missing declared files.
- Unsafe zip entry paths.
- Unsafe declared file paths.
- Unsupported multiple table files.
- Invalid integer metadata attributes.
- Missing occurrence core for occurrence row reading.
- Unsupported multi-file occurrence cores for row reading.
- Occurrence core row parse failures.
- Occurrence core file read failures.

The CLI command `dwca-cloud-geospatial inspect <archive>` is a thin wrapper
around `inspect_dwca`. It returns exit code `0` for inspections without error
diagnostics and exit code `1` when parser errors are present. `--json` prints
the structured inspection model.

## Deferred Parser Scope

These decisions are accepted for the current MVP sequence:

- Multiple file locations for one core or extension table remain unsupported
  for row streaming until a real sample or user need requires them. The parser
  should keep reporting a clear diagnostic instead of guessing behavior.
- EML content extraction is not required for row iteration. Inspection
  preserves the declared metadata file path, and source metadata extraction
  should be implemented with the output metadata/source writer work.
- Occurrence row reading intentionally does not normalize coordinates, dates
  or Darwin Core terms into the final occurrence schema. That belongs to
  Prompt 04 and later conversion stages.
