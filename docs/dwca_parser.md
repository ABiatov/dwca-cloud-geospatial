# DwC-A Parser

Status: Draft accepted parser behavior

## Scope

The current parser implementation supports safe inspection of local Darwin
Core Archives. It parses `meta.xml` and reports archive structure, but it does
not normalize rows, validate coordinates or write geospatial output bundles.
Occurrence row iteration is the next parser milestone and is in scope for the
Prompt 03 occurrence parser work.

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

## Accepted Behavior

`meta.xml` is the source of truth for core and extension table structure.
Field access must use declared terms and indexes from `ArchiveField`; later
row-reading and normalization code must not hard-code source columns outside
this schema model.

Zip archives are inspected in place. The parser does not extract zip contents.
Before reading `meta.xml`, every zip entry path is checked for absolute paths,
parent-directory traversal and unsafe path separators. Archives with unsafe
entries return an error diagnostic and are not parsed further.

Unpacked directories are read directly from the requested directory. Declared
file paths in `meta.xml` are also checked for traversal before existence
checks.

The MVP row reader should support one file location per core or extension
table. Inspection records every declared location, but emits an
`unsupported_multiple_table_files` warning when a table declares more than one
file. Prompt 03 should preserve that behavior for row iteration: do not
attempt to stream multi-file tables yet; return a parser diagnostic with
source context instead.

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

The occurrence row reader should fail fast for these archives with a clear
parser diagnostic such as `missing_occurrence_core`. Later conversion commands
should preserve the same boundary: checklist archives remain inspectable, but
conversion should reject them with an actionable non-occurrence input error.

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

The CLI command `dwca-cloud-geospatial inspect <archive>` is a thin wrapper
around `inspect_dwca`. It returns exit code `0` for inspections without error
diagnostics and exit code `1` when parser errors are present. `--json` prints
the structured inspection model.

## Deferred Parser Scope

These decisions are accepted for the current MVP sequence:

- Row iteration is the immediate parser priority and belongs in Prompt 03.
- Multiple file locations for one core or extension table remain unsupported
  for row streaming until a real sample or user need requires them. The parser
  should keep reporting a clear diagnostic instead of guessing behavior.
- EML content extraction is not required for row iteration. Inspection
  preserves the declared metadata file path, and source metadata extraction
  should be implemented with the output metadata/source writer work.
