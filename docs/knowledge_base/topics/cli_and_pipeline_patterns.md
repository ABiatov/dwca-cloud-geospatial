---
id: cli-and-pipeline-patterns
status: candidate
applies_to:
  - converter CLI/configuration
  - geospatial conversion
  - validation
sources:
  - examples/code/dwca-tools/README.md
  - examples/code/dwca-tools/.claude/CLAUDE.md
  - examples/code/geoparquet-io/CLAUDE.md
  - examples/code/geoparquet-io/README.md
---

# CLI And Pipeline Patterns

## Use In This Project

The baseline workflow should be reproducible from explicit input and output paths. CLI commands should expose inspection, conversion, validation, and possibly viewer-output generation without requiring a database or network service.

## Implemented Commands

Accepted MVP command shape after Prompt 10:

- `inspect [--json] <archive>`: summarize `meta.xml`, files, row types,
  fields, and coordinate availability without conversion.
- `convert <archive> <output>`: write the default FlatGeobuf output bundle.
- `convert <archive> <output> --format geoparquet`: write explicit
  GeoParquet output.
- Repeated `--format` values select multiple outputs, for example
  `--format flatgeobuf --format geoparquet`.
- `convert <archive> <output> --overwrite`: replace an existing output path.
- `validate [--json] <bundle>`: validate output bundle, GeoParquet,
  FlatGeobuf, manifest, metadata and diagnostics.
- `convert` also copies static viewer files into the output root as
  `index.html`, `styles.css`, `app.js` and `README.md`, then reports the
  copied viewer entry path.

## Implementation Shape

Patterns worth reusing:

- Thin CLI wrappers around core functions.
- Core logic independent of terminal UI.
- Explicit paths and configuration objects.
- Structured result objects with output paths, counts, warnings, elapsed time, and mode.
- Tests around small fixture archives before optimizing for very large datasets.

Implemented Prompt 10 core API:

- `dwca_cloud_geospatial.conversion.convert_dwca_archive`.
- `ConversionOptions` for output formats, overwrite behavior and writer
  options.
- `ConversionResult` for output paths, parser result, normalization result,
  writer results and metadata result.
- `ConversionError` for actionable conversion failures with parser
  diagnostics when available.

Implemented Prompt 10b core-only large-output options:

- `ConversionOptions.chunk_size` controls streaming occurrence batch size.
- `GeoParquetWriterOptions.large_output_mode=True` selects GeoParquet
  large-output optimizations. FlatGeobuf conversion uses chunked GeoPackage
  staging by default when FlatGeobuf is selected.
- The large-output path writes GeoParquet `bbox` covering metadata and uses
  the bounded `grid` spatial sort. It is not exposed as a dedicated CLI flag
  yet; CLI `--format geoparquet` keeps the Prompt 10 syntax.
- Partitioned GeoParquet options are rejected until the manifest and validator
  contract support partitioned datasets.

## Configuration

Keep configuration file-based and optional:

- conversion mode;
- output formats;
- field mappings and type overrides;
- coordinate validation policy;
- compression and row group settings;
- viewer field selection.

Do not hide behavior in working-directory assumptions.

## Dependency Boundaries

- Local processing engines and temporary files are acceptable at build time.
- Published outputs should remain portable files.
- Database engines such as SQLite or DuckDB may be useful for development, inspection, or optional workflows.
- PostgreSQL/PostGIS should not become a required runtime.
- Network downloads and GBIF API integration should remain optional until explicitly accepted.

## Resolved By Accepted Docs

- DuckDB is an accepted optional validation and analytical-reader helper. It
  must not become a required runtime dependency for the baseline converter, per
  `.codex/AGENTS.md` and the accepted GeoParquet validation toolchain in
  `docs/development_plan.md`.
- `geoparquet-io` is the preferred optional spec-aware GeoParquet validator
  when installed. Missing optional validation tools should surface as skipped
  checks or warnings, not baseline validation failures, when PyArrow checks
  pass.
- Output generation has a primary `convert <archive> <output>` workflow with
  explicit format options, plus a separate `validate [--json] <bundle>`
  workflow. `validate` calls `validate_output_bundle` directly and exits
  non-zero only when required validation errors are present.
- The MVP CLI should use the Python standard library `argparse`. Command handlers should remain thin wrappers around core functions and structured configuration/result objects. Click or Typer should not be added unless the CLI grows enough that `argparse` becomes burdensome to maintain.
- `inspect <archive>` should ship in the MVP CLI as a lightweight archive/schema inspection command. It should parse DwC-A structure through `meta.xml`, report core/extension files, row types, declared fields, coordinate field presence and parser warnings, and avoid full occurrence normalization, geospatial conversion or output bundle writing. Human-readable text output is sufficient for MVP; `--json` is useful but optional.
- Checklist/Taxon DwC-A archives should remain valid for `inspect`, but `convert` should fail fast with an actionable non-occurrence input error when no occurrence core or coordinate terms are present.
- FlatGeobuf conversion should preserve indexed output semantics: default
  writes request `SPATIAL_INDEX=YES`, large indexed writes surface non-fatal
  structured warnings such as `large_indexed_flatgeobuf_write`, and conversion
  must not silently auto-disable the index for large files without updating
  `docs/output_format.md`.
- CLI/core errors should surface `FlatGeobufDependencyError` as an actionable
  dependency setup message, pointing users to the documented
  `.[dev,flatgeobuf]` install path.
- Checklist/Taxon archives inspect successfully through `inspect --json` when
  valid, but `convert` rejects them using the occurrence row reader's
  `missing_occurrence_core` diagnostic.

## Open Questions

- None currently.
