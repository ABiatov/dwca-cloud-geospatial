# Prompt 15: Demo, Documentation And MVP Hardening

## Required Skills

- `planning-artifact-curator`: consolidate accepted decisions, evidence, open questions and next actions.
- `data-package-spec`: final output bundle docs and validation evidence.
- `dwca-archive-parser`: parser documentation accuracy.
- `geospatial-pipeline`: end-to-end converter behavior and tests.
- `static-viewer-contract`: viewer documentation and static hosting behavior.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md` if it exists.
- `docs/converter.md` if it exists.
- `docs/viewer_contract.md` if it exists.
- `docs/deployment.md` if it exists.
- All prompts `01` through `14`, including `10b` and `10c`
- Latest session logs for prompts `01` through `14`, including `10b` and
  `10c` when present
- Current tests, examples and generated sample bundle instructions.
- Prompt 02 inspection API and docs:
  `dwca_cloud_geospatial.inspection.inspect_dwca`,
  `docs/dwca_parser.md`, the CLI command
  `dwca-cloud-geospatial inspect [--json] <archive>`, and fixtures under
  `tests/fixtures/dwca/minimal_occurrence/`.
- Prompt 03 occurrence row reader API and docs:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `iter_occurrence_rows`, `OccurrenceReadResult`,
  `OccurrenceSourceRecord`, `docs/dwca_parser.md`, and occurrence parser
  fixtures under `tests/fixtures/dwca/minimal_occurrence/`.
- Prompt 04 occurrence normalization API and docs:
  `dwca_cloud_geospatial.normalization.normalize_occurrence_records`,
  `normalize_occurrence_record`, `OccurrenceNormalizationResult`,
  `OccurrenceNormalizationCounts`, `NormalizedOccurrenceRecord`,
  `RejectedOccurrenceRecord`, `docs/dwca_parser.md`, and normalization
  fixtures under `tests/fixtures/dwca/minimal_occurrence/normalization/`.
- Prompt 14 GBIF citation workflow:
  `.codex/prompts/14_gbif_doi_citation.md`, including its source metadata,
  viewer citation and optional GBIF DOI enrichment decisions.
- Prompt 05 quality-rule API additions:
  `TypeConversionFailure`, `OccurrenceNormalizationWarning`, `warning_count`,
  `type_conversion_failures`, `warnings`, nullable exact-token
  `quality_flags`, `has_quality_flags`, and quality-rule fixtures under
  `tests/fixtures/dwca/minimal_occurrence/quality_rules/`.
- Prompt 06 FlatGeobuf writer API:
  `dwca_cloud_geospatial.flatgeobuf.write_flatgeobuf_occurrences`,
  `FlatGeobufWriteResult`, `FlatGeobufWriterOptions`,
  `FlatGeobufWriterWarning`, `FlatGeobufDependencyError`,
  `DEFAULT_FLATGEOBUF_RELATIVE_PATH`, `FLATGEOBUF_PROJECTION_COLUMNS`, and
  tests in `tests/test_flatgeobuf_writer.py`. The writer produces
  `data/occurrences.fgb`, uses an optional Pyogrio/PyArrow/GDAL production
  backend, requests `SPATIAL_INDEX=YES` by default, emits structured
  `large_indexed_flatgeobuf_write` warnings for risky indexed writes, and has
  dependency-specific real FlatGeobuf checks that skip explicitly when local
  geospatial writer dependencies are absent.
- Prompt 06 dependency follow-up: `pyproject.toml` includes the `flatgeobuf`
  optional extra and `docs/developer_setup.md` documents
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"`. The local `.venv/`
  verified Pyogrio `0.12.1`, GDAL `3.11.4`, PyArrow `24.0.0`, `GPKG rw`,
  FlatGeobuf driver `rw`, and no `.venv` `ogr2ogr` executable.
- Prompt 10c large-data limitation to preserve in final docs: FlatGeobuf
  conversion avoids Python-side full accepted-record materialization by
  writing accepted chunks to persistent `data/occurrences.gpkg`, then creating
  indexed `data/occurrences.fgb` through Pyogrio/GDAL with
  `SPATIAL_INDEX=YES`. For very large DwC-A inputs, GDAL may still need
  substantial memory while building the final FlatGeobuf spatial index; 5
  million accepted records estimate about 320,000,000 bytes for
  spatial-index construction and emit `large_indexed_flatgeobuf_write`.
- Prompt 07 GeoParquet writer API:
  `dwca_cloud_geospatial.geoparquet.write_geoparquet_occurrences`,
  `GeoParquetWriteResult`, `GeoParquetWriterOptions`,
  `GeoParquetDependencyError`, `DEFAULT_GEOPARQUET_RELATIVE_PATH`,
  `GEOPARQUET_PROJECTION_COLUMNS`, and tests in
  `tests/test_geoparquet_writer.py`. The writer produces
  `data/occurrences.parquet`, uses streaming PyArrow `ParquetWriter` batches,
  stores WKB point geometry in `geometry`, writes GeoParquet `1.1.0` metadata
  with `OGC:CRS84` PROJJSON longitude-latitude axis order, stores file-level
  bbox metadata, uses ZSTD compression, and defaults to
  `row_group_size=100_000`.
- Prompt 07 dependency follow-up: `pyproject.toml` includes the `geoparquet`
  optional extra for `pyarrow>=24`; `docs/developer_setup.md` documents
  `python -m pip install -e "${REPO}[dev,geoparquet]"`, while the full
  writer-capable `.venv/` workflow can continue using
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"` because that extra also
  provides PyArrow. Local verification used PyArrow `24.0.0`; PyArrow
  GeoParquet writer tests passed, and the dependency-dependent
  Pyogrio/GDAL GeoParquet-aware reader check skipped when local GDAL Parquet
  read support was unavailable.
- Post-Prompt-07 validation toolchain decision to preserve in final docs:
  PyArrow is the required baseline GeoParquet validator; `geoparquet-io` and
  DuckDB are preferred optional validation tools; Pyogrio/GDAL remains a
  best-effort reader check. Missing optional validation tools should be
  reported as warnings or skipped checks, not as failures when PyArrow
  validation passes. The full local writer and validation install is
  `python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"`.
- Validation installation evidence to preserve: the local Python 3.13/macOS
  `.venv/` uses `pyproj==3.7.0` in the `validation` extra because newer
  `pyproj` releases may require a source build with system PROJ. The verified
  optional validation stack included `geoparquet-io 1.3.0`, DuckDB `1.5.1`,
  PyProj `3.7.0`, PyArrow `24.0.0`, Pyogrio `0.12.1` and GDAL `3.11.4`.
- Prompt 07 record-set rule to preserve: when FlatGeobuf and GeoParquet are
  both selected, both writers should receive the same accepted
  `NormalizedOccurrenceRecord` set unless processing metadata documents an
  explicit export filter.
- Prompt 08 bundle metadata writer API:
  `dwca_cloud_geospatial.bundle.write_bundle_metadata`,
  `build_source_metadata`, `build_processing_metadata`,
  `write_rejected_records_csv`, `BundleWriterOptions`,
  `BundleMetadataWriteResult`, and path constants for `manifest.json`,
  `metadata/source.json`, `metadata/processing.json` and
  `reports/rejected_records.csv`. Prompt 08 writes the rejected-record report
  only when rejected records exist, inventories only generated files in
  `manifest.files`, includes size and SHA-256 checksums where practical, and
  preserves FlatGeobuf writer warning `large_indexed_flatgeobuf_write` in
  `metadata/processing.json.warnings`.
- Prompt 08 EML/source metadata limitation to preserve: source metadata reads
  the declared `ArchiveMetadata.metadata_file` when safely available and
  extracts common EML dataset/rights values, but missing GBIF/OBIS values stay
  null and are not invented.
- Prompt 09 bundle validation API:
  `dwca_cloud_geospatial.validation.validate_output_bundle`,
  `BundleValidationResult`, `BundleValidationIssue` and
  `BundleValidationCheck`, exported from `dwca_cloud_geospatial`.
- Prompt 09 validation behavior to preserve in final docs and demo evidence:
  status values are `passed`, `passed_with_warnings` and `failed`; required
  failures populate `errors`; optional geospatial reader gaps and other
  dependency-dependent checks populate structured warnings/skipped checks; the
  result exposes `has_errors`, `skipped_checks`, `to_dict()` and `to_json()`.
- Prompt 09 validation coverage to preserve: required bundle JSON files and
  schema versions, manifest inventory paths/sizes/checksums, required PyArrow
  GeoParquet metadata and projection checks, optional `geoparquet-io`,
  DuckDB and Pyogrio/GDAL checks, dependency-dependent FlatGeobuf inspection,
  row-count reconciliation, rejected CSV columns, viewer field presence,
  `quality_flags` exact-token and `has_quality_flags` consistency, processing
  warning/type-conversion failure structure, and nullable GBIF/OBIS provenance
  acceptance.
- Prompt 10 core conversion API:
  `dwca_cloud_geospatial.conversion.convert_dwca_archive`,
  `ConversionOptions`, `ConversionResult`, `ConversionError`,
  `FLATGEOBUF_FORMAT`, `GEOPARQUET_FORMAT` and
  `SUPPORTED_OUTPUT_FORMATS`, exported from `dwca_cloud_geospatial`.
- Prompt 10 CLI behavior to preserve in final docs and demo evidence:
  `dwca-cloud-geospatial convert <archive> <output>` writes default
  FlatGeobuf output, `--format geoparquet` selects explicit GeoParquet,
  repeated `--format` selects both outputs, existing output paths are rejected
  unless `--overwrite` is passed, `inspect --json` succeeds for valid
  checklist/Taxon DwC-A archives, `convert` rejects checklist/Taxon archives
  with a clear non-occurrence input error, and
  `dwca-cloud-geospatial validate [--json] <bundle>` returns non-zero only
  when `BundleValidationResult.has_errors` is true.
- Prompt 10 docs path: converter command syntax, public API names, output
  paths, overwrite behavior and failure behavior are documented in
  `docs/converter.md`.
- Prompt 10b large-archive implementation to preserve in final docs:
  `stream_occurrence_row_batches`, `OccurrenceRowBatch`,
  `OccurrenceRowStream`, `normalize_occurrence_record_batch`,
  `ConversionOptions.chunk_size`, GeoParquet-only
  `GeoParquetWriterOptions.large_output_mode`, default-on `bbox` covering,
  default-on bounded `grid` spatial sorting, streaming rejected-report
  writing, bounded count/warning aggregation and PyArrow validation of bbox
  schema/content. Partitioned GeoParquet dataset output remains deferred and
  is rejected when requested. Combined FlatGeobuf+GeoParquet conversion uses
  the Prompt 10c GeoPackage-staged FlatGeobuf handoff.
- Prompt 10/10b viewer/docs implication to preserve: valid GeoParquet-only
  bundles, including large-output bundles, may omit `data/occurrences.fgb`.
  Viewer and final docs should describe the accepted no-FlatGeobuf behavior
  from `docs/viewer_contract.md` instead of assuming every valid bundle has a
  FlatGeobuf map layer.
- Prompt 10c optimized FlatGeobuf implementation when present: preserve the
  persistent GeoPackage staging artifact at `data/occurrences.gpkg`,
  indexed FlatGeobuf output at `data/occurrences.fgb`, manifest inventory
  role/media type/checksum/record count for GeoPackage, processing metadata
  describing the GeoPackage staging and GDAL/OGR helper strategy, validation
  checks for GeoPackage and FlatGeobuf count reconciliation, and dependency
  setup for required helper tooling installed into `.venv`.
- Prompt 11 viewer contract to preserve in final docs:
  `docs/viewer_contract.md` is the accepted MVP static viewer contract.
  The MVP browser map source is declared FlatGeobuf point layer
  `data/occurrences.fgb`; `data/occurrences.gpkg` is shown as a retained
  artifact/download metadata item, not as a browser map layer; explicit
  GeoParquet-only bundles remain valid and should show metadata/provenance
  plus the no-FlatGeobuf/no-map-layer state rather than failing; browser
  GeoParquet loading and PMTiles are not accepted MVP viewer requirements.
- Prompt 11 filter semantics to preserve: MVP filters are
  `scientific_name`, `kingdom`, `event_year`, `basis_of_record`,
  `iucn_red_list_category` and `quality_flags` when present. `quality_flags`
  must be split on `|` and matched as exact tokens, with `has_quality_flags`
  used for flagged/unflagged controls when available. Optional absent fields
  are omitted from viewer UI without errors.
- Prompt 12 static viewer implementation to preserve in final docs:
  `viewer/` contains the source `index.html`, `styles.css`, `app.js` and
  `README.md`, and `dwca-cloud-geospatial convert` copies those files into
  each generated output bundle root. Local launch serves the output parent and
  opens the copied viewer directly, for example
  `python -m http.server 8000 --directory "${REPO}"` and
  `http://localhost:8000/scratch/sample-bundle/index.html`. The shared source
  viewer still accepts `?bundle=<bundle-root-url>` and
  `?manifest=<manifest-json-url>`.
- Prompt 12 frontend dependency behavior to preserve: copied `index.html`
  references MapLibre GL JS and FlatGeobuf JavaScript from public CDN URLs,
  and uses OpenStreetMap raster tiles as the default basemap. These are
  frontend static assets, not a backend service or live biodiversity-data API.
  Fully offline hosting should mirror those assets or replace the basemap URL
  and update the source/copy viewer files.
- Prompt 12 static viewer interaction behavior to preserve: FlatGeobuf is
  loaded from fetched bytes/`Uint8Array`; hidden no-map or empty-state
  overlays must not cover an active map; selected features are highlighted on
  the map; point color styling follows `kingdom`; and selected-record details
  derive a clickable `source record URL` after `source_record_id` using
  `https://www.gbif.org/occurrence/{source_record_id}` with `target="_blank"`.
- Current static viewer no-FlatGeobuf message to preserve in final docs and
  tests: when a valid bundle has no FlatGeobuf layer, the viewer says
  `No FlatGeobuf map layer is available for this bundle. To display occurrence
  points on the map, generate the bundle with the FlatGeobuf output format
  selected.` This prevents GUI users who uncheck FlatGeobuf from interpreting
  a GeoParquet-only bundle as a broken viewer.
- Prompt 12 verification to preserve:
  `.venv/bin/python -m pytest tests/test_static_viewer.py -q` covers static
  viewer smoke inputs for generated FlatGeobuf-with-GeoPackage and
  GeoParquet-only bundles, no-map-layer behavior, artifact-only GeoPackage and
  GeoParquet handling, exact-token `quality_flags` filtering, copied viewer
  files, OpenStreetMap basemap wiring, derived source-record links, kingdom
  colors, selected-feature highlighting, hidden empty-state behavior and
  FlatGeobuf `Uint8Array` loading.
- Prompt 13 Tkinter GUI implementation to preserve:
  `src/dwca_cloud_geospatial/gui.py` provides the primitive desktop GUI and
  the console script `dwca-cloud-geospatial-gui`. The module entry point is
  `python -m dwca_cloud_geospatial.gui`. The GUI collects an input archive or
  unpacked DwC-A directory, an output bundle directory, FlatGeobuf and
  GeoParquet format checkboxes, an overwrite checkbox, optional validation
  after conversion, GeoParquet large-output mode and chunk size.
- Prompt 13 GUI launch behavior to preserve:
  `dwca-cloud-geospatial-gui` is created by refreshing the editable install.
  A bare `dwca-cloud-geospatial-gui` shell command requires `.venv/bin` on
  `PATH`, normally after `source "${REPO}/.venv/bin/activate"`. Users can also
  run `"${REPO}/.venv/bin/dwca-cloud-geospatial-gui"` directly. If the script
  is missing after `pyproject.toml` changes, refresh the editable install from
  the documented `.venv/`; this local session used
  `.venv/bin/python -m pip install -e . --no-deps --no-build-isolation` after
  ensuring the `.venv` had `setuptools` and `wheel`.
- Prompt 13 core API reuse to preserve:
  GUI conversion calls `dwca_cloud_geospatial.conversion.convert_dwca_archive`
  with `ConversionOptions` built by GUI helper functions. GUI validation calls
  `dwca_cloud_geospatial.validation.validate_output_bundle`. The GUI does not
  duplicate DwC-A parsing, normalization, geospatial writing, metadata writing
  or bundle validation logic.
- Prompt 13 GUI behavior to preserve:
  existing output paths are rejected before conversion unless the overwrite
  checkbox is selected; core `ConversionError` messages and diagnostics are
  shown as actionable errors; non-fatal normalization and FlatGeobuf writer
  warnings, including `large_indexed_flatgeobuf_write`, are displayed
  separately from failures; retained `data/occurrences.gpkg` staging artifact
  paths are shown when present; validation display separates required errors,
  warnings and dependency-dependent skipped checks.
- Prompt 13 GUI viewer guidance to preserve:
  generated bundles should point users at the copied `<output>/index.html`
  viewer entry. FlatGeobuf bundles should be described as having an MVP map
  layer at `data/occurrences.fgb`; retained `data/occurrences.gpkg` remains
  artifact/download metadata only. GeoParquet-only bundles remain valid and
  open in the copied viewer as a metadata/provenance/artifact inventory state
  with no MVP map layer. The viewer no-map state now explicitly tells users to
  generate with FlatGeobuf selected if they want occurrence points on the map.
  The GUI must not imply that Python starts a backend service or bundles
  offline frontend assets.
- Prompt 13 GUI copy behavior and limitation to preserve:
  context-menu copy works in the status/viewer-instructions text area and the
  GUI also exposes a `Copy Text` button for copying the full current status
  panel. `Ctrl+C`/`Cmd+C` remained unreliable in manual Tk/macOS testing and
  is accepted as an MVP limitation because context-menu copy and `Copy Text`
  satisfy the workflow. Final docs should not promise keyboard-copy behavior
  until it is verified interactively.
- Prompt 13 verification to preserve:
  `.venv/bin/python -m pytest tests/test_gui.py -q` covers headless-safe
  GUI-adjacent logic: format selection, overwrite guard, core
  `ConversionOptions` construction, GeoParquet large-output option gating,
  chunk-size validation, warning summaries, validation summary grouping and
  viewer instruction copy.
- Prompt 11 viewer-contract fixtures:
  `tests/fixtures/output_bundles/viewer_contract/flatgeobuf_with_geopackage_manifest.json`
  and
  `tests/fixtures/output_bundles/viewer_contract/geoparquet_only_manifest.json`
  are hand-authored manifest-semantics fixtures for viewer contract tests, not
  complete generated output bundles.
- Post-Prompt-03 handoff clarification: the Prompt 03 `Open Issues Affecting
  Normalization` were confirmed to be scope boundaries, not blockers before
  Prompt 04. Final docs should preserve that split: source row reading in
  Prompt 03, normalization in Prompt 04, quality thresholds in Prompt 05,
  metadata/EML extraction in Prompt 08, and multi-file occurrence-core
  streaming as deferred work unless implemented later.
- Checklist DwC-A examples inspected after Prompt 02:
  `examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip`,
  `examples/dwca/dwca-appendixiibernconventionua-v1.2.zip` and
  `examples/dwca/dwca-kharkivredliastua-v1.0.zip`. They are valid
  inspectable `Taxon` core archives, but they are not occurrence geospatial
  conversion inputs for the MVP workflow.

## Goal

Make the MVP understandable, repeatable and ready for external review.

## Tasks

- Run or refresh an end-to-end sample conversion note using local DwC-A examples.
- Update README and `docs/developer_setup.md` with current `.venv/`
  installation, CLI, GUI and viewer usage.
- Complete or update `docs/dwca_parser.md`, `docs/converter.md`, `docs/viewer_contract.md` and `docs/deployment.md`.
- Confirm `docs/output_format.md` matches implemented bundle behavior.
- Confirm GUI docs mention `dwca-cloud-geospatial-gui`, explicit
  `.venv/bin/dwca-cloud-geospatial-gui` fallback, context-menu/`Copy Text`
  copy behavior and the current `Ctrl+C`/`Cmd+C` limitation.
- Confirm docs and viewer guidance distinguish default FlatGeobuf bundles,
  explicit GeoParquet-only bundles and GeoParquet-only large-output bundles.
- If Prompt 10c has been completed, confirm docs describe
  `data/occurrences.gpkg` as a retained bundle artifact and not a temporary
  file.
- Confirm `docs/developer_setup.md` still documents the FlatGeobuf optional
  dependency stack and real writer verification command.
- Add regression tests for parser behavior, normalization, output writing and bundle validation where gaps remain.
- Add known limitations and MVP+ roadmap, including PMTiles as deferred.
- Document the current large-DwC-A limitation clearly: Prompt 10b/10c provide
  chunked parser/normalizer/writer handoff for GeoParquet large-output mode and
  FlatGeobuf GeoPackage staging, but GDAL FlatGeobuf spatial-index creation
  may still need substantial memory.
- Document the checklist limitation clearly: checklist/Taxon DwC-A archives can
  be inspected, but the MVP converter only produces geospatial outputs from
  occurrence archives with coordinate terms.
- Include the three local checklist archives in final demo evidence as
  non-occurrence inspection examples and, when conversion exists, negative
  conversion examples with actionable errors.
- Record demo evidence and validation results.
- Remove stale prompt assumptions only if they contradict final accepted docs; otherwise leave historical prompts intact.

## Constraints

- Do not expand MVP scope to live downloads, taxonomy enrichment, PMTiles, backend services or cloud-specific deployment.
- Do not hide known limitations in code comments only; document them.
- Do not make broad refactors unrelated to hardening or docs consistency.

## Acceptance Criteria

- A fresh user can install the package, convert a sample archive and inspect the result using documented steps.
- Tests protect parser behavior, normalization, output writing and bundle validation.
- Docs clearly state what is MVP versus MVP+.
- Remaining risks and deferred work are visible.

## Required Session Log

Write `session_logs/YYYY-MM-DD_15_demo_docs_hardening.md` with:

- Final files updated.
- End-to-end demo commands and results.
- Test and validation evidence.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- Known remaining limitations.
- Suggested next MVP+ prompts or ADRs.
- `Prompt Updates`: list prompt files changed, or `None`.

## Prompt Maintenance

If this session changes accepted decisions, update canonical docs and this prompt flow description. If it identifies new MVP+ work, create new numbered prompts only after the MVP prompt sequence remains internally consistent.
