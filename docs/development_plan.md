# Development Plan

Status: Accepted MVP plan

Last updated: 2026-06-09

## Purpose

This document records the development plan for the DwC-A to cloud-optimized geospatial conversion prototype.

The plan follows the accepted project boundaries in `README.md`, `.codex/AGENTS.md`, `docs/output_format.md` and `planning/decisions/ADR-001-mvp-boundaries-and-interfaces.md`.

The MVP remains file-based and reproducible: a user provides an already downloaded Darwin Core Archive, the converter writes static geospatial outputs and metadata, and the viewer reads those generated files without a backend service.

## Accepted MVP Scope

The MVP includes:

- A Python core library for parsing DwC-A archives, normalizing occurrence records and writing output bundles.
- A CLI for repeatable local conversion and validation.
- GeoParquet, FlatGeobuf, JSON metadata and CSV rejection reports as the initial output formats.
- A thin static MapLibre viewer that reads `manifest.json`, metadata files and `exports/occurrences.fgb`.
- A primitive `tkinter` GUI that calls the same core conversion API as the CLI.
- Documentation and sample runs using local DwC-A examples.

The MVP excludes:

- Required PostgreSQL/PostGIS, permanent API services, schedulers or cloud-specific runtimes.
- Live GBIF, OBIS or other archive download flows.
- Required taxonomy matching or checklist enrichment.
- PMTiles generation, except as documented MVP+ work.
- Full raw table export for DwC-A core and extension tables.
- Standalone packaged desktop binaries.

## Development Principles

- Keep the core converter independent from CLI, GUI and viewer code.
- Preserve provenance from output rows back to source archive files and source row identifiers.
- Parse archive structure through `meta.xml` where possible.
- Treat GBIF and OBIS fields as nullable provenance fields, not as required inputs.
- Make validation explicit before writing final outputs.
- Prefer small sample archives for early tests before optimizing for large datasets.
- Keep output bundle changes synchronized with `docs/output_format.md`.

## Accepted Implementation Decisions

- Default conversion format: when the user does not choose an explicit output format, the CLI and GUI should generate FlatGeobuf output by default.
- Explicit conversion formats: GeoParquet remains an MVP-supported output format, but it should be selected explicitly unless a later decision changes the default bundle behavior.
- GeoParquet writer library: explicit GeoParquet output should use a streaming PyArrow writer, not GeoPandas.
- Rejected records report: `reports/rejected_records.csv` should be written only when at least one source record is rejected or skipped.
- Overwrite behavior: CLI conversions must not overwrite an existing output path unless the user passes `--overwrite`.
- GUI overwrite behavior: GUI conversions must not overwrite an existing output path unless the user selects an overwrite checkbox.
- MVP CLI framework: use the Python standard library `argparse` for the MVP CLI. Command handlers should remain thin wrappers around core functions and structured configuration/result objects. Do not add Click or Typer unless the CLI grows enough that `argparse` becomes burdensome to maintain.
- MVP inspect command: include `inspect <archive>` in the MVP CLI as a lightweight archive/schema inspection command. It should parse DwC-A structure through `meta.xml`, report core/extension files, row types, declared fields, coordinate field presence and parser warnings. It must not perform full occurrence normalization, geospatial conversion or output bundle writing. Full data-quality validation remains part of conversion and `validate <output-dir>`. Human-readable text output is sufficient for MVP; `--json` is useful but optional.
- Checklist/Taxon DwC-A handling: valid checklist archives with a `Taxon` core
  must remain inspectable through `inspect` and `inspect --json`, but they are
  outside the MVP occurrence geospatial conversion workflow. Occurrence row
  reading and conversion should fail fast when no occurrence core or coordinate
  terms are present, using actionable diagnostics instead of treating
  `taxon.txt` as occurrence data.
- DwC-A defaults and row numbering: apply `meta.xml` field defaults only when the declared field has no source column index or the source column is not present in the row shape. Do not use defaults to replace explicit empty strings or invalid source values in present columns. Store `source_row_number` as the physical 1-based row number in the source data file, including skipped header rows, and store `source_data_row_number` as the logical 1-based data-record number after declared header rows when available.
- Type conversion failure policy: for MVP, type conversion failures should be counted by field and reason in processing metadata. Optional-field conversion failures should set normalized values to null and emit warnings when the failure rate for a field is `>= 5%` of parsed records. Critical-field failures, including coordinate parsing failures, should reject affected records with stable reason codes. The conversion should fail only when no accepted occurrence records remain, required provenance fields cannot be produced, or parser/metadata structure prevents reliable row interpretation. Future releases may add configurable warning/failure thresholds.
- Future raw table export: full Parquet-family export of DwC-A core and extension tables is deferred until after MVP. The MVP parser should preserve the design path for that mode by reading core/extensions through `meta.xml`, retaining field metadata, relationship keys such as `_id` and `_coreid`, source files and row-number provenance.
- Future PMTiles generation: PMTiles remains deferred to MVP+ and should use Tippecanoe as the preferred tiler when available. Tippecanoe is an optional external dependency, not an MVP runtime requirement; requested PMTiles generation should fail gracefully with an actionable message when `tippecanoe` is not installed. PMTiles point attributes should default to the same compact normalized occurrence field set as FlatGeobuf, with a smaller PMTiles-specific attribute profile allowed later for large datasets if tile size or browser performance requires it.

## Accepted GeoParquet Writer Stack

Status: Accepted

The GeoParquet writer for large datasets is a streaming PyArrow-based writer, not a GeoPandas `GeoDataFrame.to_parquet()` writer.

Rationale:

- The parser and normalization pipeline should already operate in batches, so the writer should accept Arrow `RecordBatch` or `Table` chunks instead of materializing the full dataset in memory.
- PyArrow `ParquetWriter` supports incremental writes, explicit compression, dictionary encoding, file metadata and row group sizing.
- The project only needs point geometry from normalized longitude/latitude columns, so WKB point encoding and GeoParquet metadata can be generated directly without constructing Shapely geometry objects for every row.
- GeoPandas remains useful for small exploratory outputs, but its in-memory dataframe model is not appropriate as the primary path for tens or hundreds of millions of records.

Accepted defaults:

- Library: `pyarrow` as the required GeoParquet writer dependency.
- Geometry encoding: WKB point geometry in a binary `geometry` column.
- GeoParquet version: `1.1.0` for broad reader compatibility.
- GeoParquet 2.0: deferred to post-MVP; may be added later only as an explicit opt-in output option after target downstream readers and validation tools demonstrate reliable support. Adding 2.0 must not change the default GeoParquet version without a separate accepted decision.
- CRS: `OGC:CRS84`, matching the accepted output contract.
- Compression: ZSTD.
- Row group size: configurable, with an initial default around 100,000 rows.
- Statistics: enabled.
- Bbox: include file-level bbox in GeoParquet metadata, and evaluate a GeoParquet 1.1 covering bbox column for large outputs.
- Validation: validate with PyArrow plus one GeoParquet-aware tool when available.

Large-data extensions to evaluate after the first writer works:

- Partitioned GeoParquet datasets with `pyarrow.dataset.write_dataset` when a single `data/occurrences.parquet` file becomes impractical.
- Spatial sorting before write, using a simple lon/lat sort first or an optional DuckDB/geoparquet-io Hilbert-sort workflow for large analytical outputs.
- Optional `geoparquet-io` or DuckDB as development/validation helpers, without making either a required runtime dependency for the baseline converter.

## Accepted FlatGeobuf Writer Stack

Status: Accepted

The default FlatGeobuf writer stack is Pyogrio/GDAL.

The previously considered GeoPandas FlatGeobuf writer is rejected as the default implementation path for the same reason as GeoParquet: GeoPandas is convenient, but it is an in-memory dataframe API and should not be the core writer abstraction for very large occurrence outputs.

Rationale:

- GeoPandas `to_file()` delegates file writing to Pyogrio when available, so Pyogrio/GDAL is the actual writer layer.
- Pyogrio has full read/write support for FlatGeobuf through GDAL and can use Arrow for faster writing.
- Pyogrio still writes an entire GeoDataFrame at once, so the MVP implementation must validate memory limits before writing very large FlatGeobuf outputs.
- GDAL's FlatGeobuf driver creates a spatial index by default, which is useful for static viewer and remote bbox reads, but its packed Hilbert R-tree requires memory proportional to feature count.

Accepted defaults:

- Library: `pyogrio` with GDAL FlatGeobuf support.
- Engine settings: use Arrow-accelerated writes when `pyarrow` is installed.
- Layer options: `SPATIAL_INDEX=YES`.
- Spatial index: enabled by default for FlatGeobuf output.
- Large-output guardrail: estimate spatial-index memory before writing; emit a required large dataset warning when projected memory or feature count is high enough to make the indexed write risky.
- Geometry policy: write only accepted records with non-null point geometry.
- Field policy: write a compact normalized occurrence field set optimized for viewer and lightweight exchange, not the full source/raw Darwin Core field set. Include geometry, required provenance fields, accepted viewer display/filter fields, coordinates, `quality_flags` and the additional accepted Darwin Core fields documented in `docs/output_format.md`.
- GeoPandas role: allowed only for tests, examples and notebooks during early development. Production writer code should call Pyogrio/GDAL directly where practical.

## Accepted MVP Viewer Filters

Status: Accepted

The first static viewer should provide only simple browser-side filters over fields present in the generated bundle. This is enough for MVP inspection without adding a backend, query service or required tiled aggregate layer.

Accepted filters:

- `scientific_name`: simple text search using contains matching.
- `kingdom`: select/dropdown when the field is present.
- `event_year`: min/max controls or a list of available years.
- `basis_of_record`: select/dropdown.
- `iucn_red_list_category`: select/dropdown when the field is present.
- `quality_flags`: show/hide records with quality flags when the field is present.

Fields absent from the generated bundle must be omitted from the viewer UI without error.

## Accepted Quality Flags Representation

Status: Accepted

The first GeoParquet writer and FlatGeobuf output should store `quality_flags` as a nullable delimiter-separated string.

Accepted defaults:

- Field name: `quality_flags`.
- Field type: nullable string.
- Delimiter: `|`.
- No flags: represent as null.
- Flag code format: stable lowercase snake_case tokens.
- Delimiter rule: flag codes must not contain `|`.
- Matching rule: viewers and downstream consumers must split the string on `|` and perform exact token matching, not substring matching.

Rationale:

This keeps the MVP output schema simple and consistent across GeoParquet, FlatGeobuf, CSV-style exports and the static viewer. A repeated string representation is semantically cleaner for GeoParquet, but it introduces nested-field compatibility concerns and format divergence too early.

## Milestones

### M0: Repository And Package Skeleton

Goal: make the repository ready for implementation and tests.

Deliverables:

- Python packaging configuration.
- Core package namespace.
- CLI entry point stub.
- Test framework and fixture layout.
- Basic developer documentation for running tests and commands.

Acceptance criteria:

- `python -m pytest` runs.
- The CLI exposes help text.
- Sample fixtures are addressable without hidden working-directory assumptions.

### M1: DwC-A Inspection And Parser

Goal: read local DwC-A archives safely and produce structured source records.

Deliverables:

- Safe archive inspection for `.zip` archives and unpacked DwC-A directories.
- `meta.xml` parser for core files, field mappings, delimiters, headers and row types.
- Occurrence core detection.
- Streaming or chunked row reader for occurrence records.
- Source metadata file discovery from `meta.xml`; full EML content extraction
  is deferred to the metadata/source writer work.
- Parser diagnostics for missing files, malformed metadata and row parse failures.

Acceptance criteria:

- The parser reads the local sample DwC-A archives in `examples/dwca/`.
- Checklist/Taxon-core archives are inspectable but rejected by occurrence row
  reading with actionable non-occurrence diagnostics.
- Field access is based on declared DwC-A terms instead of hard-coded column positions.
- Parser errors are reported with source file and row context.

### M2: Occurrence Normalization And Quality Rules

Goal: convert parsed records into the normalized occurrence schema accepted by the output contract.

Deliverables:

- Mapping from Darwin Core terms into normalized occurrence fields.
- Coordinate parsing and validation for longitude, latitude, ranges and `0,0` policy.
- Event date and event year normalization where practical.
- Required provenance fields: `source_record_id`, `source_file` and physical `source_row_number`; include `source_data_row_number` when available.
- Quality flag assignment using stable lowercase snake_case tokens that do not contain `|`.
- Rejection reason model aligned with `reports/rejected_records.csv`.

Acceptance criteria:

- Valid coordinate records become accepted occurrence records.
- Invalid or incomplete coordinate records are rejected with stable reason codes.
- Records with quality flags expose `quality_flags` as a `|`-delimited string, and records without flags expose null.
- Accepted and rejected counts reconcile for sample archives.

### M3: Output Bundle Writer

Goal: write the accepted MVP output bundle described in `docs/output_format.md`.

Deliverables:

- FlatGeobuf writer for default `exports/occurrences.fgb` output.
- GeoParquet writer for explicit `data/occurrences.parquet` output.
- `manifest.json` writer.
- `metadata/source.json` writer, including EML content extraction from the
  declared DwC-A metadata file where available.
- `metadata/processing.json` writer.
- Conditional `reports/rejected_records.csv` writer for rejected or skipped records.
- Bundle validation command or API.

Acceptance criteria:

- Generated bundles match the documented layout.
- When GeoParquet is generated, its metadata declares point geometry, CRS `OGC:CRS84` and longitude-latitude order.
- FlatGeobuf contains the viewer-required fields and is written with a spatial index by default.
- GeoParquet and FlatGeobuf outputs use the accepted nullable `|`-delimited `quality_flags` representation.
- Large FlatGeobuf outputs emit the documented large dataset warning before indexed writes that may require substantial memory.
- Manifest file inventory, counts and layer paths reconcile with generated files.
- `reports/rejected_records.csv` is absent when no records are rejected and present when one or more records are rejected.

### M4: Core API And CLI

Goal: provide repeatable command-line workflows while keeping conversion behavior in the core library.

Deliverables:

- Core conversion API with explicit input path, output path and options.
- CLI command for conversion.
- CLI `--overwrite` flag for explicitly replacing an existing output path.
- CLI command for validating an existing output bundle.
- CLI command for lightweight DwC-A archive/schema inspection.
- Human-readable errors and non-zero exit codes for failed conversions.

Acceptance criteria:

- A user can convert a local sample archive with one CLI command.
- CLI and tests call the same core conversion API.
- Existing output paths are rejected unless `--overwrite` is set.
- Non-occurrence checklist archives fail conversion with a clear error while
  remaining valid inputs for `inspect`.

### M5: Static Viewer Contract And Implementation

Goal: make generated bundles inspectable in a browser without a backend.

Deliverables:

- `docs/viewer_contract.md`.
- Static viewer files.
- Manifest-driven dataset loading.
- FlatGeobuf point layer display.
- Dataset provenance panel.
- Feature details panel for viewer-required fields.
- MVP browser-side filters for `scientific_name`, `kingdom`, `event_year`, `basis_of_record`, `iucn_red_list_category` and `quality_flags` where those fields are present.

Acceptance criteria:

- The viewer opens a generated sample bundle from static files.
- Missing optional metadata is handled gracefully.
- Missing filter fields are omitted from the viewer UI without error.
- The viewer supports text contains search for `scientific_name`, select/dropdown filters for categorical fields, year filtering and a show/hide control for records with quality flags where supported by the bundle.
- No live GBIF or OBIS API access is required.

### M6: Primitive GUI

Goal: provide a simple desktop entry point for non-CLI users.

Deliverables:

- `tkinter` GUI that lets a user choose input archive and output directory.
- Overwrite checkbox that must be selected before replacing an existing output path.
- Progress and status reporting.
- Error display that preserves actionable messages.
- Link or button to open generated output directory or viewer instructions.

Acceptance criteria:

- GUI conversion uses the same core API as the CLI.
- GUI does not implement separate parsing or writing logic.

### M7: Demo, Documentation And MVP Hardening

Goal: make the prototype understandable, repeatable and ready for external review.

Deliverables:

- End-to-end sample conversion notes.
- Converter documentation.
- Parser documentation.
- Deployment/static hosting documentation.
- Updated README with installation and usage.
- Regression tests for sample bundles.
- Known limitations and MVP+ roadmap.

Acceptance criteria:

- A fresh user can install the package, convert a sample archive and inspect the result using documented steps.
- Test coverage protects parser behavior, normalization, output writing and bundle validation.
- Remaining deferred work is documented rather than hidden in code comments.

## Documentation Roadmap

Documents to create or update during the milestones:

| Document | Owner Milestone | Purpose |
| --- | --- | --- |
| `docs/development_plan.md` | M0 | Accepted implementation plan and milestone sequence. |
| `docs/dwca_parser.md` | M1 | Parser behavior, `meta.xml` handling, metadata file discovery and diagnostics. |
| `docs/output_format.md` | M2-M3 | Output bundle schema and validation rules. |
| `docs/converter.md` | M4 | CLI, Python API, configuration and overwrite behavior. |
| `docs/viewer_contract.md` | M5 | Static viewer inputs, fields, filters and failure handling. |
| `docs/deployment.md` | M7 | Static hosting and sample publishing workflow. |
| `planning/decisions/` | As needed | Long-lived tradeoffs and accepted architecture decisions. |

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| DwC-A archives vary in delimiters, headers, extensions and metadata completeness. | Drive parsing through `meta.xml`, test against local examples and preserve diagnostics. |
| Geospatial writer dependencies may behave differently across platforms. | Keep writer APIs isolated, add validation commands and document supported environments. |
| Viewer requirements may expand before the converter contract is stable. | Keep the viewer manifest-driven and update `docs/output_format.md` before changing generated files. |
| Large archives may expose memory or performance limits. | Start with chunked parsing and avoid loading full archives into memory where practical. |
| Provenance can be lost during normalization. | Carry source file, row number, row identifier and source metadata through every stage. |

## Open Questions

No open questions remain for the accepted MVP plan.

## Immediate Next Actions

1. Implement quality rules and conversion failure accounting on top of the
   Prompt 04 `OccurrenceNormalizationResult`, including
   optional-field warning thresholds and critical-field rejection policy.
2. Implement the FlatGeobuf and GeoParquet writers, then bundle metadata and
   validation checks.
3. Implement EML content extraction during the metadata/source writer work.
4. Keep multi-file occurrence-core streaming deferred until a real sample or
   user need requires it.
