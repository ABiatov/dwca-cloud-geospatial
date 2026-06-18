# Prompt 10c: Optimized FlatGeobuf Via GeoPackage Staging

## Required Skills

- `geospatial-pipeline`: bounded-memory FlatGeobuf writer handoff, GDAL/OGR
  helper strategy and large-output behavior.
- `data-package-spec`: persistent GeoPackage staging artifact, manifest,
  metadata, validation and bundle contract updates.
- `dwca-archive-parser`: chunked occurrence row reading and parser
  diagnostics for large FlatGeobuf conversion.
- `planning-artifact-curator`: record accepted implementation decisions,
  evidence and downstream prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md`
- `docs/converter.md` if it exists.
- `planning/decisions/ADR-001-mvp-boundaries-and-interfaces.md`
- `planning/decisions/ADR-002-large-archive-geoparquet-strategy.md`
- `planning/decisions/ADR-003-geoparquet-validation-toolchain.md`
- Prompts `01` through `10b`
- Latest session logs for prompts `01` through `10b`
- Current parser, normalization, rejected-record, FlatGeobuf, GeoParquet,
  metadata, validator, core API and CLI implementations.
- Prompt 10 core conversion API:
  `dwca_cloud_geospatial.conversion.convert_dwca_archive`,
  `ConversionOptions`, `ConversionResult`, `ConversionError`,
  `FLATGEOBUF_FORMAT`, `GEOPARQUET_FORMAT` and
  `SUPPORTED_OUTPUT_FORMATS`, exported from `dwca_cloud_geospatial`.
- Prompt 10 CLI syntax: default FlatGeobuf conversion is
  `dwca-cloud-geospatial convert <archive> <output>`, explicit GeoParquet is
  `dwca-cloud-geospatial convert <archive> <output> --format geoparquet`,
  both outputs are selected by repeating `--format`, replacement requires
  `--overwrite`, and validation is
  `dwca-cloud-geospatial validate [--json] <bundle>`.
- Prompt 10b chunked APIs:
  `stream_occurrence_row_batches`, `OccurrenceRowStream`,
  `OccurrenceRowBatch`, `normalize_occurrence_record_batch`,
  `ConversionOptions.chunk_size` and `RejectedRecordsCsvWriter`.
- Prompt 10b large-output limitation: bounded-memory claims currently apply
  to GeoParquet-only `GeoParquetWriterOptions.large_output_mode=True`;
  default FlatGeobuf and combined FlatGeobuf+GeoParquet still use the current
  materialized FlatGeobuf writer handoff.
- Current FlatGeobuf writer API:
  `write_flatgeobuf_occurrences`, `FlatGeobufWriterOptions`,
  `FlatGeobufWriteResult`, `FlatGeobufWriterWarning`,
  `FlatGeobufDependencyError`, `DEFAULT_FLATGEOBUF_RELATIVE_PATH`,
  `FLATGEOBUF_PROJECTION_COLUMNS` and `large_indexed_flatgeobuf_write`.
- Current FlatGeobuf behavior to fix: `write_flatgeobuf_occurrences`
  materializes projected rows and WKB geometries into tuples before one
  Pyogrio/GDAL write call.
- Current FlatGeobuf large-output warning policy:
  `SPATIAL_INDEX=YES` is default, large indexed writes emit
  `large_indexed_flatgeobuf_write`, and warnings do not fail conversion.
- Current GeoParquet writer behavior and large-output path from Prompt 10b.
- Prompt 08 bundle metadata writer APIs:
  `write_bundle_metadata`, `build_source_metadata`,
  `build_processing_metadata`, `write_rejected_records_csv`,
  `BundleWriterOptions` and `BundleMetadataWriteResult`.
- Prompt 09 bundle validator API:
  `validate_output_bundle`, `BundleValidationResult`,
  `BundleValidationIssue` and `BundleValidationCheck`.
- Current dependency setup in `docs/developer_setup.md`, especially the
  in-repository `.venv/`, `flatgeobuf` and `validation` extras.
- Local installed driver evidence may vary. Check the current `.venv` with
  Pyogrio/GDAL before implementation. GeoPackage (`GPKG`) and FlatGeobuf must
  be writable for the optimized path.

## Goal

Implement an optimized FlatGeobuf creation path that avoids Python-side full
accepted-record materialization by writing accepted chunks into a persistent
GeoPackage staging file at `data/occurrences.gpkg`, then creating the indexed
FlatGeobuf output from that GeoPackage with GDAL/OGR tooling.

The intermediate GeoPackage is not temporary: it must remain in the output
bundle at `data/occurrences.gpkg` after conversion and be listed in
`manifest.files`.

## Dependency And Tooling Requirements

- Use the documented in-repository `.venv/` workflow.
- The implementation may install required Python packages or GDAL/OGR helper
  tools into `.venv` when they are missing.
- Do not install tools into Conda `base`, the system Python or global system
  locations.
- Prefer project extras first, for example:

```bash
"${REPO}/.venv/bin/python" -m pip install -e "${REPO}[dev,flatgeobuf,validation]"
```

- If a required tool is still missing, install the narrowest needed package
  into `.venv` and document it in `docs/developer_setup.md`.
- If dependency installation requires network access or sandbox escalation,
  request approval and keep the install scoped to `.venv`.
- If an `ogr2ogr` CLI is not available in `.venv`, investigate Python-accessible
  GDAL/OGR alternatives before declaring a blocker. Acceptable routes include:
  - an `.venv`-scoped `ogr2ogr` executable;
  - GDAL Python bindings with `VectorTranslate`;
  - a Pyogrio/GDAL route that demonstrably creates an indexed FlatGeobuf from
    the GeoPackage without materializing all rows in Python.
- Record the selected helper strategy and exact local tool versions in the
  session log.

## Required Output Contract

- Keep default conversion format as FlatGeobuf.
- Preserve the indexed FlatGeobuf output at:
  `exports/occurrences.fgb`.
- Add a persistent GeoPackage artifact at:
  `data/occurrences.gpkg`.
- Do not delete `data/occurrences.gpkg` after FlatGeobuf generation.
- Include `data/occurrences.gpkg` in `manifest.files` with role
  `geopackage`, media type `application/geopackage+sqlite3`, byte size,
  SHA-256 and accepted record count.
- Include `data/occurrences.gpkg` in processing metadata output decisions,
  including:
  - whether GeoPackage staging was enabled;
  - staging relative path;
  - staging writer backend;
  - whether FlatGeobuf was generated from GeoPackage;
  - GDAL/OGR helper strategy;
  - FlatGeobuf spatial index status.
- Do not add `data/occurrences.gpkg` as the default viewer map layer unless
  the viewer contract explicitly accepts it. The MVP viewer should continue
  to prefer `exports/occurrences.fgb` when FlatGeobuf exists.

## Implementation Tasks

- Design the optimized FlatGeobuf writer handoff using chunked parser and
  normalization APIs from Prompt 10b.
- Add or adapt a GeoPackage writer that writes accepted normalized records in
  bounded chunks to `data/occurrences.gpkg`.
- Preserve the current FlatGeobuf projection contract:
  `FLATGEOBUF_PROJECTION_COLUMNS`, point geometry, `OGC:CRS84`,
  longitude/latitude order, `quality_flags` and `has_quality_flags`.
- Ensure the accepted record set in `data/occurrences.gpkg` and
  `exports/occurrences.fgb` is identical unless processing metadata documents
  an explicit export filter.
- Use `SPATIAL_INDEX=YES` for the final FlatGeobuf. Do not silently switch to
  `SPATIAL_INDEX=NO`.
- If indexed FlatGeobuf creation from GeoPackage cannot be completed with the
  available GDAL/OGR tooling, fail with an actionable `ConversionError` or
  writer dependency error. Do not produce an unindexed FlatGeobuf as a silent
  fallback.
- Preserve `large_indexed_flatgeobuf_write` warnings or update them to reflect
  the GeoPackage-staged writer path while keeping them non-fatal.
- Add writer result metadata for the GeoPackage artifact or a combined
  FlatGeobuf result that carries staging artifact metadata.
- Extend `write_bundle_metadata` and related helpers to inventory the
  GeoPackage file without duplicating manifest logic in CLI handlers.
- Extend `validate_output_bundle` to validate declared GeoPackage artifacts:
  - file exists;
  - manifest size/checksum matches;
  - SQLite/GeoPackage metadata tables are present when checkable;
  - occurrence layer row count matches manifest/processing counts;
  - required projection columns are present when readable through Pyogrio/GDAL
    or a documented dependency-independent fallback;
  - FlatGeobuf and GeoPackage record counts reconcile.
- Ensure rejected rows still go through the streaming rejected-report path.
- Ensure conversion failure behavior remains consistent:
  - checklist/Taxon archives remain inspectable but rejected by conversion;
  - missing coordinate terms fail conversion;
  - zero accepted normalized records fail conversion;
  - optional warnings do not fail conversion by themselves.
- Preserve Prompt 10 CLI syntax unless a new CLI flag is necessary. If new
  user-facing options are added, update `docs/converter.md`, prompts `11`
  through `14` and this prompt flow description.
- Update public exports from `dwca_cloud_geospatial` when new result/options
  classes are part of the supported API.

## Tests

- Add small deterministic tests that exercise the optimized path without
  committing large generated datasets.
- Use small chunk sizes in tests to prove chunked handoff at the API level.
- Add tests proving:
  - `data/occurrences.gpkg` is written and retained;
  - `exports/occurrences.fgb` is written with spatial index requested;
  - both files are inventoried in `manifest.files`;
  - GeoPackage and FlatGeobuf record counts reconcile;
  - rejected records are streamed and counted correctly;
  - `quality_flags` and `has_quality_flags` stay consistent;
  - same accepted record set across GeoPackage and FlatGeobuf when both are
    readable;
  - validator accepts valid GeoPackage-staged FlatGeobuf bundles;
  - dependency/tool absence fails or skips according to required vs optional
    validation policy.
- Use dependency-isolated fakes for helper orchestration where practical, but
  include at least one real Pyogrio/GDAL integration test guarded by
  dependency skips when the local environment lacks required drivers/tools.

## Documentation Updates

Update, at minimum:

- `README.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/converter.md`
- `docs/knowledge_base/topics/flatgeobuf_output.md`
- `docs/knowledge_base/topics/validation_and_quality.md`
- `docs/knowledge_base/playbooks/validate_output_bundle.md`
- downstream prompts `11` through `14`
- `.codex/prompts/dev_flow_description.md`

Documentation must clearly state:

- default conversion still produces indexed FlatGeobuf;
- optimized FlatGeobuf generation uses persistent GeoPackage staging;
- `data/occurrences.gpkg` is a bundle artifact, not a temporary file;
- `SPATIAL_INDEX=YES` remains required for FlatGeobuf;
- selected GDAL/OGR helper dependencies and how to install them into `.venv`;
- remaining scale risks, especially GDAL memory use while building the
  FlatGeobuf spatial index.

## Constraints

- Do not use GeoPandas as the primary large-output writer path.
- Do not disable FlatGeobuf spatial indexing.
- Do not switch the default output format away from FlatGeobuf.
- Do not introduce PostgreSQL/PostGIS, a permanent API service, scheduler,
  cloud-specific runtime or required network service.
- Do not delete `data/occurrences.gpkg` after conversion.
- Do not commit large generated datasets.
- Keep small-fixture tests fast and deterministic.

## Acceptance Criteria

- Default FlatGeobuf conversion can write accepted records through a bounded
  GeoPackage staging handoff without Python-side full accepted-record
  materialization.
- `data/occurrences.gpkg` is retained in the output bundle and inventoried.
- `exports/occurrences.fgb` is generated from the GeoPackage with
  `SPATIAL_INDEX=YES`.
- Bundle metadata records the GeoPackage staging strategy, helper backend and
  output counts.
- Validator coverage checks GeoPackage existence, inventory consistency and
  record-count reconciliation with FlatGeobuf when dependencies allow.
- Tests prove count reconciliation, quality flag consistency, rejected-report
  streaming and same accepted record set across staged GeoPackage and
  FlatGeobuf.
- Documentation and downstream prompts reflect the new `data/occurrences.gpkg`
  artifact and optimized FlatGeobuf writer behavior.

## Required Session Log

Write `session_logs/YYYY-MM-DD_10c_flatgeobuf_geopackage_staging.md` with:

- Public API and internal handoff summary.
- Chosen GeoPackage writer and GDAL/OGR helper strategy.
- Dependency/tool installation steps performed in `.venv`, including versions.
- Confirmation that `data/occurrences.gpkg` is retained and inventoried.
- FlatGeobuf spatial index behavior and any remaining GDAL memory risks.
- Metadata and validation changes.
- Synthetic or fixture-based large-output test strategy and results.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- Known limitations and remaining risks.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `11` through `14` if public API names, conversion options,
bundle paths, metadata fields, validation coverage, viewer assumptions, GUI
options or known limitations changed.
