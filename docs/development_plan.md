# Development Plan

Status: Accepted MVP plan

Last updated: 2026-06-19

## Purpose

This document records the development plan for the DwC-A to cloud-optimized geospatial conversion prototype.

The plan follows the accepted project boundaries in `README.md`, `.codex/AGENTS.md`, `docs/output_format.md` and `planning/decisions/ADR-001-mvp-boundaries-and-interfaces.md`.

The large-archive GeoParquet strategy is documented in
`planning/decisions/ADR-002-large-archive-geoparquet-strategy.md`.

The GeoParquet validation toolchain is documented in
`planning/decisions/ADR-003-geoparquet-validation-toolchain.md`.

The MVP remains file-based and reproducible: a user provides an already downloaded Darwin Core Archive, the converter writes static geospatial outputs and metadata, and the viewer reads those generated files without a backend service.

## Accepted MVP Scope

The MVP includes:

- A Python core library for parsing DwC-A archives, normalizing occurrence records and writing output bundles.
- A CLI for repeatable local conversion and validation.
- GeoParquet, FlatGeobuf, JSON metadata and CSV rejection reports as the initial output formats.
- A thin static MapLibre viewer that reads `manifest.json`, metadata files and
  `data/occurrences.fgb` when a FlatGeobuf layer is generated.
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
- Core conversion API: the public conversion entry point is
  `dwca_cloud_geospatial.conversion.convert_dwca_archive`, configured with
  `ConversionOptions` and returning `ConversionResult`. Conversion failures
  use `ConversionError` with actionable messages and parser diagnostics when
  available. CLI and future GUI code should call this API rather than
  duplicating parser, normalization, writer, manifest or rejected-report
  logic.
- MVP conversion CLI: default FlatGeobuf conversion is
  `dwca-cloud-geospatial convert <archive> <output>`. Explicit GeoParquet is
  selected with `--format geoparquet`, both formats are selected by repeating
  `--format`, and existing output paths require `--overwrite`.
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
- Bundle validation API: the core bundle validator is
  `dwca_cloud_geospatial.validation.validate_output_bundle`. It returns
  `BundleValidationResult` with status `passed`, `passed_with_warnings` or
  `failed`, required validation failures in `errors`, dependency-dependent
  optional-reader issues in `warnings` and structured per-check details in
  `checks`. The CLI command
  `dwca-cloud-geospatial validate [--json] <bundle>` consumes this core
  result directly and exits non-zero only when `.has_errors` is true. GUI
  validation surfaces should consume the same core result instead of
  reimplementing bundle checks.
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
- Development install: use the optional `geoparquet` extra from
  `pyproject.toml`, normally `python -m pip install -e
  "${REPO}[dev,geoparquet]"`. The full writer-capable development install can
  also use `python -m pip install -e "${REPO}[dev,flatgeobuf]"` because the
  FlatGeobuf production backend also depends on PyArrow.
- Geometry encoding: WKB point geometry in a binary `geometry` column.
- GeoParquet version: `1.1.0` for broad reader compatibility.
- GeoParquet 2.0: deferred to post-MVP; may be added later only as an explicit opt-in output option after target downstream readers and validation tools demonstrate reliable support. Adding 2.0 must not change the default GeoParquet version without a separate accepted decision.
- CRS: `OGC:CRS84`, matching the accepted output contract.
- Compression: ZSTD.
- Row group size: configurable, with an initial default around 100,000 rows.
- Statistics: enabled.
- Bbox: include file-level bbox in GeoParquet metadata. For large
  GeoParquet 1.1 outputs, write a covering bbox column by default so spatial
  readers can use Parquet statistics for row-group pruning.
- Spatial layout: for large GeoParquet outputs, spatial sorting is default-on
  and strategy-configurable. The implemented MVP strategy streams records into
  temporary coarse longitude/latitude grid buckets and writes buckets in stable
  spatial order without calling `sorted(records)` on the full archive.
- Validation: required baseline validation uses PyArrow. Optional
  GeoParquet-aware validation uses `geoparquet-io`, DuckDB and Pyogrio/GDAL
  when available. Missing optional validation tools should be reported as
  warnings or skipped checks, not as failures, when PyArrow validation passes.

Accepted large-archive pipeline direction:

- The converter must support an end-to-end bounded-memory path before it is
  considered ready for very large DwC-A archives with tens of millions of
  occurrence records.
- Required pipeline shape:
  - streaming/chunked occurrence reader;
  - chunked normalization result handoff;
  - streaming GeoParquet accepted-record writer;
  - streaming rejected-record/report writer;
  - bounded-memory counts and warning aggregation.
- The public writer and core conversion APIs should avoid requiring fully
  materialized accepted or rejected record tuples when a streaming iterator or
  chunked result object can preserve the same semantics.
- Counts, conversion failures, warnings, file bounds, checksums and output
  record counts must still reconcile in metadata after chunked processing.
- This large-archive path remains file-based and must not introduce a required
  permanent database, API service, scheduler or cloud-specific runtime.

Current implementation:

- `stream_occurrence_row_batches` provides bounded occurrence row batches.
- `normalize_occurrence_record_batch` normalizes each bounded batch.
- GeoParquet large-output conversion streams accepted records through parser,
  normalization, GeoParquet writing and rejected-report writing without
  retaining full accepted or rejected tuples in `ConversionResult`.
- The default FlatGeobuf path and combined FlatGeobuf+GeoParquet conversions
  stream accepted batches into persistent GeoPackage staging at
  `data/occurrences.gpkg`, then create indexed FlatGeobuf from that
  GeoPackage.

Accepted large-output GeoParquet requirements:

- GeoParquet 1.1 covering bbox column: implemented and default-on when
  `GeoParquetWriterOptions.large_output_mode=True`. The `bbox` struct has
  numeric `xmin`, `ymin`, `xmax` and `ymax` fields equal to point coordinates.
- Spatial sorting: default-on for large GeoParquet outputs, with a
  configurable strategy. Sorting should be chosen to tighten row-group bboxes
  for spatial predicate pushdown.
- Partitioned GeoParquet dataset output: deferred. The writer exposes
  partitioned-output configuration fields and rejects enabled partitioned mode
  with an actionable error until manifest and validator contracts are added.
- Optional `geoparquet-io` or DuckDB as development/validation helpers, without making either a required runtime dependency for the baseline converter.

## Accepted GeoParquet Validation Toolchain

Status: Accepted

GeoParquet validation is layered so the baseline converter remains portable
while development and bundle validation can use stronger reader checks when
available.

Required baseline:

- PyArrow must validate declared GeoParquet files as Parquet.
- PyArrow validation must check schema, row counts, required projection
  columns, GeoParquet `geo` metadata, geometry column, geometry type, encoding,
  CRS, file bounds where present and `quality_flags`/`has_quality_flags`
  consistency.

Preferred optional checks:

- `geoparquet-io` is the preferred optional spec-aware validator when
  installed.
- DuckDB is the preferred optional analytical reader for query access, row
  groups, metadata inspection and future bbox/spatial-pruning validation.
- Pyogrio/GDAL remains a best-effort geospatial reader check, but local GDAL
  Parquet support is dependency- and build-dependent.

Development install:

- `pyproject.toml` provides a `validation` optional extra with PyArrow, DuckDB,
  `geoparquet-io` and the verified `pyproj==3.7.0` binary-wheel constraint
  needed by the local Python 3.13/macOS `.venv/` workflow.
- The full local writer and validation workflow should use
  `python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"`.

Validation results should separate required errors from optional checks that
were skipped because a local tool or driver is unavailable.

## Accepted Bundle Validator API

Status: Accepted

The bundle validator validates generated static output bundles through the
core Python API `dwca_cloud_geospatial.validation.validate_output_bundle`.

Structured result objects:

- `BundleValidationResult`
- `BundleValidationIssue`
- `BundleValidationCheck`

Result behavior:

- `status` is `passed`, `passed_with_warnings` or `failed`.
- Required failures populate `errors` and make `has_errors` true.
- Optional dependency-dependent checks, such as missing optional readers or
  unavailable GDAL GeoParquet support, populate `warnings`, `checks` and
  `skipped_checks` without failing the bundle when required checks pass.
- `to_dict()` and `to_json()` provide portable output for CLI and future GUI
  consumers.

Implemented validation coverage:

- required bundle JSON files and supported schema versions;
- manifest file inventory, safe relative paths, byte sizes and SHA-256
  checksums;
- required PyArrow checks for declared single-file GeoParquet outputs,
  including large-output `bbox` covering schema/content when present;
- optional `geoparquet-io`, DuckDB and Pyogrio/GDAL checks when available;
- dependency-dependent FlatGeobuf inspection through Pyogrio/GDAL;
- GeoPackage artifact validation through SQLite metadata checks and optional
  Pyogrio/GDAL inspection;
- row-count reconciliation across manifest, processing metadata, geospatial
  outputs, GeoPackage staging and rejected-record reports;
- rejected CSV required columns;
- viewer field presence in inspected generated data;
- `quality_flags` exact-token representation and `has_quality_flags`
  consistency where row-level data are readable;
- processing warning counts and type conversion failure structures;
- nullable GBIF and OBIS provenance values.

Current limitations:

- The validator covers the implemented single-file GeoParquet output
  `data/occurrences.parquet`. Partitioned GeoParquet dataset validation
  remains future work because partitioned output is deferred and rejected when
  requested.
- FlatGeobuf attribute-level `quality_flags` validation depends on readable
  geospatial table support. The current validator checks FlatGeobuf projection
  fields and counts through Pyogrio/GDAL when available.
- The CLI `validate` command calls `validate_output_bundle` directly and
  exits non-zero only when required validation errors are present.

## Accepted FlatGeobuf Writer Stack

Status: Accepted

The default FlatGeobuf writer stack is Pyogrio/GDAL.

The previously considered GeoPandas FlatGeobuf writer is rejected as the default implementation path for the same reason as GeoParquet: GeoPandas is convenient, but it is an in-memory dataframe API and should not be the core writer abstraction for very large occurrence outputs.

Rationale:

- GeoPandas `to_file()` delegates file writing to Pyogrio when available, so Pyogrio/GDAL is the actual writer layer.
- Pyogrio has full read/write support for FlatGeobuf through GDAL and can use Arrow for faster writing.
- The default production implementation writes accepted chunks into a
  persistent GeoPackage at `data/occurrences.gpkg` with `pyogrio.write_arrow`,
  then streams that GeoPackage through Pyogrio/GDAL into indexed FlatGeobuf.
- GDAL's FlatGeobuf driver creates a spatial index by default, which is useful for static viewer and remote bbox reads, but its packed Hilbert R-tree requires memory proportional to feature count.

Accepted defaults:

- Library: `pyogrio` with GDAL FlatGeobuf support.
- Engine settings: use `pyogrio.write_arrow` for bounded GeoPackage chunk
  appends and Pyogrio/GDAL `open_arrow` to `write_arrow` for the final
  GeoPackage-to-FlatGeobuf export. PyArrow is required for the current
  production backend.
- Development install: use the optional `flatgeobuf` extra from
  `pyproject.toml`, normally `python -m pip install -e "${REPO}[dev,flatgeobuf]"`.
  The verified local `.venv/` stack is Pyogrio `0.12.1`, GDAL `3.11.4` as
  reported by Pyogrio, PyArrow `24.0.0`, and `GPKG`/FlatGeobuf driver support
  `rw`.
- Layer options: `SPATIAL_INDEX=YES`.
- Spatial index: enabled by default for FlatGeobuf output.
- Large-output guardrail: estimate spatial-index memory before writing; emit a required large dataset warning when projected memory or feature count is high enough to make the indexed write risky.
- Initial guardrail thresholds: warn for indexed writes at `>= 1,000,000`
  accepted features or estimated spatial-index construction memory
  `>= 256 MiB`, using an initial estimate of `64` bytes per feature.
- Persistent staging artifact: retain `data/occurrences.gpkg` in the output
  bundle, inventory it with role `geopackage` and record counts/checksums.
- Large-output warning behavior: emit structured warning code
  `large_indexed_flatgeobuf_write` before the final indexed FlatGeobuf export.
  The warning does not fail conversion and does not automatically switch to
  `SPATIAL_INDEX=NO`.
- Geometry policy: write only accepted records with non-null point geometry.
- Field policy: write a compact normalized occurrence field set optimized for viewer and lightweight exchange, not the full source/raw Darwin Core field set. Include geometry, required provenance fields, accepted viewer display/filter fields, coordinates, `quality_flags`, `has_quality_flags` and the additional accepted Darwin Core fields documented in `docs/output_format.md`.
- GeoPandas role: allowed only for tests, examples and notebooks during early development. Production writer code should call Pyogrio/GDAL directly where practical.

Current implementation limitation:

- The parser/normalizer/FlatGeobuf handoff is chunked through GeoPackage
  staging, so Python no longer materializes the full accepted record set for
  FlatGeobuf generation. GDAL still builds the final FlatGeobuf spatial index,
  so very large outputs may consume substantial memory or fail during the
  final indexed export. For very large DwC-A inputs, such as 5 million accepted
  occurrence records, the writer estimates about 320,000,000 bytes for
  spatial-index construction and emits `large_indexed_flatgeobuf_write`, but it
  still attempts the indexed write by default.

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
- Initial flag codes: `missing_scientific_name`, `missing_event_date`,
  `missing_coordinate_uncertainty`, `invalid_coordinate_uncertainty`,
  `missing_geodetic_datum` and `invalid_event_year`.

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
- Source metadata file discovery from `meta.xml`; EML content extraction is
  performed by the output bundle metadata writer when the declared metadata
  file is safely available.
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

- FlatGeobuf writer for default `data/occurrences.fgb` output.
- Persistent GeoPackage staging artifact at `data/occurrences.gpkg` whenever
  FlatGeobuf is generated.
- GeoParquet writer for explicit `data/occurrences.parquet` output.
- `manifest.json` writer.
- `metadata/source.json` writer, including EML content extraction from the
  declared DwC-A metadata file where available.
- `metadata/processing.json` writer, including normalization warnings and
  FlatGeobuf writer warnings.
- Conditional `reports/rejected_records.csv` writer for rejected or skipped records.
- Bundle validation command or API.

Acceptance criteria:

- Generated bundles match the documented layout.
- When GeoParquet is generated, its metadata declares point geometry, CRS `OGC:CRS84` and longitude-latitude order.
- FlatGeobuf contains the viewer-required fields and is written with a spatial index by default.
- `data/occurrences.gpkg` is retained, inventoried and reconciles counts with
  `data/occurrences.fgb`.
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
- Static viewer source files under `viewer/`, copied into each generated
  bundle root by `convert`.
- Manifest-driven dataset loading.
- FlatGeobuf point layer display.
- Graceful no-map-layer handling for valid GeoParquet-only bundles that omit
  `data/occurrences.fgb`.
- GeoPackage artifact display as retained output metadata/download, not as the
  MVP browser map layer.
- Dataset provenance panel.
- Feature details panel for viewer-required fields.
- MVP browser-side filters for `scientific_name`, `kingdom`, `event_year`, `basis_of_record`, `iucn_red_list_category` and `quality_flags` where those fields are present.

Acceptance criteria:

- The viewer opens a generated sample bundle from static files when the
  output parent is served as a static root, for example
  `http://localhost:8000/scratch/sample-bundle/index.html`.
- GeoParquet-only bundles without FlatGeobuf display metadata/provenance and
  a clear no-map-layer state instead of failing.
- Missing optional metadata is handled gracefully.
- Missing filter fields are omitted from the viewer UI without error.
- The viewer supports text contains search for `scientific_name`, select/dropdown filters for categorical fields, year filtering and a show/hide control for records with quality flags where supported by the bundle.
- Quality flag filters split nullable `quality_flags` on `|` and match exact
  tokens, using `has_quality_flags` when present for flagged/unflagged
  controls.
- The selected feature is highlighted on the map, point colors use `kingdom`
  where available, and feature details include a derived GBIF occurrence link
  when `source_record_id` is present.
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
| Large archives may expose memory or performance limits. | Use the implemented chunked GeoPackage staging path for FlatGeobuf and GeoParquet large-output mode for analytical bundles. Keep the remaining GDAL FlatGeobuf spatial-index memory risk visible, and defer partitioned GeoParquet until the manifest and validator contract support it. |
| Provenance can be lost during normalization. | Carry source file, row number, row identifier and source metadata through every stage. |

## Open Questions

No open questions remain for the accepted MVP plan.

## Immediate Next Actions

1. Implement the primitive `tkinter` GUI over the same core conversion API.
2. Preserve the viewer launch guidance from `viewer/README.md` when adding GUI
   instructions for opening or inspecting generated bundles.
