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

## Candidate Commands

Possible command shape:

- `inspect <archive>`: summarize `meta.xml`, files, row types, fields, and coordinate availability.
- `convert <archive> --output <dir>`: write Parquet/GeoParquet outputs and metadata.
- `validate <output-dir>`: validate output bundle, GeoParquet, manifest, and diagnostics.
- `viewer <output-dir>` or `build-viewer <output-dir>`: generate static viewer assets if not included in `convert`.

## Implementation Shape

Patterns worth reusing:

- Thin CLI wrappers around core functions.
- Core logic independent of terminal UI.
- Explicit paths and configuration objects.
- Structured result objects with output paths, counts, warnings, elapsed time, and mode.
- Tests around small fixture archives before optimizing for very large datasets.

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

## Open Questions

- Which Python CLI framework to use, if any.
- Whether DuckDB should be an optional dependency for validation/query convenience.
- Whether output generation should be one command with flags or separate staged commands.

