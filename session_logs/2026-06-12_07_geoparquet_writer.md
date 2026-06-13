# Prompt 07: GeoParquet Writer

Date: 2026-06-12

## Scope

Implemented the explicit analytical GeoParquet writer for accepted normalized
occurrence records at `data/occurrences.parquet`. This prompt did not change
the default conversion format from FlatGeobuf and did not implement manifest,
metadata, rejected CSV, validator, CLI conversion or viewer behavior.

## Writer API And Dependency Behavior

- Added `dwca_cloud_geospatial.geoparquet.write_geoparquet_occurrences`.
- Default output path is `data/occurrences.parquet` through
  `DEFAULT_GEOPARQUET_RELATIVE_PATH`.
- Added `GeoParquetWriterOptions` with:
  - `relative_path`
  - `row_group_size`, default `100_000`
  - `compression`, default `zstd`
- Added `GeoParquetWriteResult` with path, relative path, record count,
  columns, geometry metadata, CRS, coordinate order, file bounds, row group
  size, compression and GeoParquet version.
- Added `GeoParquetDependencyError` for missing PyArrow.
- The production writer imports PyArrow inside the write function so package
  import still works without optional writer dependencies.
- The writer uses PyArrow `ParquetWriter` and writes projected records in
  batches capped by `row_group_size`.
- The writer does not use GeoPandas.
- Added the `geoparquet` optional extra in `pyproject.toml` with
  `pyarrow>=24`.
- The existing `flatgeobuf` optional extra still includes PyArrow, so the
  documented full writer-capable `.venv/` install
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"` verifies both
  FlatGeobuf and GeoParquet writer tests.
- Verified local PyArrow version: `24.0.0`.

## GeoParquet Metadata Decisions

- GeoParquet metadata version: `1.1.0`.
- Geometry column: `geometry`.
- Geometry encoding: WKB in a binary Parquet column.
- Geometry type: `Point`.
- CRS: `OGC:CRS84`, encoded as the GeoParquet-spec PROJJSON object with
  longitude then latitude axes.
- Coordinate order surfaced by the writer result: `longitude_latitude`.
- Edges: `planar`.
- Compression: ZSTD.
- Row group sizing: configurable, default `100_000`.
- File-level bounds are accumulated while streaming records and written into
  the GeoParquet `geo` footer metadata as `bbox`.
- GeoParquet 2.0 was not added.
- A GeoParquet 1.1 covering bbox column was not added in the initial Prompt 07
  implementation; the follow-up large-archive decision below makes it
  default-on for future large GeoParquet 1.1 outputs.

## Projection Fields Implemented

Implemented the analytical GeoParquet projection from
`NormalizedOccurrenceRecord.to_dict()` plus WKB geometry:

- `source_record_id`
- `source_file`
- `source_row_number`
- `source_data_row_number`
- `occurrence_id`
- `scientific_name`
- `verbatim_scientific_name`
- `kingdom`
- `phylum`
- `class`
- `order`
- `family`
- `genus`
- `taxon_id`
- `taxon_rank`
- `identified_by`
- `basis_of_record`
- `degree_of_establishment`
- `event_date`
- `event_year`
- `recorded_by`
- `decimal_longitude`
- `decimal_latitude`
- `coordinate_uncertainty_in_meters`
- `geodetic_datum`
- `country_code`
- `locality`
- `dataset_name`
- `dataset_key`
- `publisher`
- `license`
- `rights_holder`
- `references`
- `quality_flags`
- `has_quality_flags`
- `iucn_red_list_category`
- `catalog_number`
- `collection_code`
- `institution_code`
- `record_number`
- `organism_id`
- `gbif_id`
- `obis_id`
- `raw_decimal_longitude`
- `raw_decimal_latitude`
- `raw_event_date`
- `geometry`

Projection uses `NormalizedOccurrenceRecord.to_dict()`, so the Python
attribute `class_` is emitted as output column `class`. Source camelCase
Darwin Core terms are not emitted as normalized output columns.

`quality_flags` is preserved as the accepted nullable `|`-delimited string,
and `has_quality_flags` is written as a boolean consistent with
`quality_flags is not None`.

Tests confirm the GeoParquet and FlatGeobuf projections start from the same
accepted `NormalizedOccurrenceRecord` set.

## Files Created Or Updated

- Created `src/dwca_cloud_geospatial/geoparquet.py`.
- Updated `src/dwca_cloud_geospatial/__init__.py`.
- Created `tests/test_geoparquet_writer.py`.
- Updated `pyproject.toml` with the `geoparquet` optional dependency extra.
- Updated `docs/developer_setup.md` with GeoParquet writer dependency
  installation and verification commands.
- Updated `docs/development_plan.md` with GeoParquet dependency install
  behavior and the current upstream materialization limitation.
- Updated `docs/knowledge_base/topics/geoparquet_output.md`.
- Updated `docs/knowledge_base/playbooks/implement_geoparquet_writer.md`.
- Updated downstream prompts:
  - `.codex/prompts/08_manifest_metadata_writers.md`
  - `.codex/prompts/09_bundle_validation.md`
  - `.codex/prompts/10_core_api_cli.md`
  - `.codex/prompts/14_demo_docs_hardening.md`
  - `.codex/prompts/dev_flow_description.md`

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`. The local `.venv/` already had the full writer
stack from the documented `.[dev,flatgeobuf]` workflow, which includes
PyArrow.

- `.venv/bin/python -m pytest tests/test_geoparquet_writer.py -q`
  - Result: passed, `6 passed, 1 skipped`.
  - Skip reason: dependency-dependent Pyogrio/GDAL GeoParquet-aware reader
    check skipped because local GDAL did not recognize the Parquet file format.
- `.venv/bin/python -m pytest tests -q`
  - Result: passed, `33 passed, 1 skipped`.
- `.venv/bin/python -m pytest tests/test_geoparquet_writer.py -q -rs`
  - Result: passed, `6 passed, 1 skipped`.
  - Confirmed skip reason: GDAL GeoParquet read support unavailable locally.
- `.venv/bin/python -m pytest tests/test_flatgeobuf_writer.py -q -rs`
  - Result: passed, `6 passed`.
- `.venv/bin/python -c "import pyarrow; print('pyarrow', pyarrow.__version__)"`
  - Result: `pyarrow 24.0.0`.
- `git diff --check`
  - Result: passed with no output.

## Open Questions Or Risks

- The GeoParquet writer streams records into Parquet row groups, but current
  parser and normalizer APIs still materialize records before writer handoff in
  tests and future core conversion orchestration. End-to-end chunked
  parser/normalizer/writer handoff remains future work.
- The local Pyogrio/GDAL stack can write FlatGeobuf but did not provide
  GeoParquet read support for the optional reader-aware test. Prompt 09 should
  keep GeoParquet-aware reader checks dependency-dependent and treat unavailable
  local support as a warning or skip, not as a failure of PyArrow validation.

## Follow-Up Accepted Large-Archive Decision

After reviewing the local Geomermaids GeoParquet writing and reading
cookbooks, the project documented a large-archive decision in
`planning/decisions/ADR-002-large-archive-geoparquet-strategy.md`,
`docs/development_plan.md`, `docs/output_format.md` and the GeoParquet
knowledge-base docs:

- The converter must implement an end-to-end chunked large-archive pipeline
  before claiming support for tens of millions of occurrence records.
- Required pipeline shape: streaming/chunked occurrence reader, chunked
  normalization result handoff, streaming GeoParquet accepted-record writer,
  streaming rejected-record/report writer and bounded-memory counts/warnings
  aggregation.
- For large GeoParquet 1.1 outputs, a covering bbox column is default-on.
- For large GeoParquet outputs, spatial sorting is default-on and
  strategy-configurable.
- Partitioned GeoParquet dataset output remains an optional large-dataset mode
  enabled by configuration or threshold.
- Created
  `.codex/prompts/10b_large_archive_streaming_and_geoparquet_optimization.md`
  to implement the accepted chunked large-archive pipeline and large-output
  GeoParquet optimization decisions before later MVP hardening.

## Follow-Up Accepted Validation Toolchain Decision

After discussing the dependency-dependent Pyogrio/GDAL GeoParquet reader skip,
the project documented a layered GeoParquet validation decision in
`planning/decisions/ADR-003-geoparquet-validation-toolchain.md`,
`docs/development_plan.md`, `docs/output_format.md` and
`docs/developer_setup.md`:

- PyArrow is the required baseline GeoParquet validation layer.
- `geoparquet-io` is the preferred optional spec-aware validator when
  installed.
- DuckDB is the preferred optional analytical reader for Parquet query access,
  row groups, metadata inspection and future bbox/spatial-pruning checks.
- Pyogrio/GDAL remains a best-effort geospatial reader check because local
  Parquet/GeoParquet support depends on the GDAL build.
- Missing optional validation tools should be reported as warnings or skipped
  checks, not as failures, when required PyArrow validation passes.
- `pyproject.toml` now provides a `validation` optional extra. The full local
  writer and validation install is
  `python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"`.

Validation install follow-up in the local `.venv/`:

- Initial full-extra install failed when `geoparquet-io` pulled a newer
  `pyproj` source distribution that required a system PROJ executable.
- Installing the verified binary wheel first resolved the issue:
  `.venv/bin/python -m pip install --only-binary=:all: "pyproj==3.7.0"`.
- The full install then succeeded:
  `.venv/bin/python -m pip install -e '.[dev,flatgeobuf,validation]'`.
- Verified optional validation stack:
  `geoparquet-io 1.3.0`, DuckDB `1.5.1`, PyProj `3.7.0`, PyArrow `24.0.0`,
  Pyogrio `0.12.1` and GDAL `3.11.4`.
- `gpio --version` returned `geoparquet-io, version 1.3.0`.
- `.venv/bin/python -m pip check` reported no broken requirements.

## Prompt Updates

- Updated `.codex/prompts/08_manifest_metadata_writers.md`.
- Updated `.codex/prompts/09_bundle_validation.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Created
  `.codex/prompts/10b_large_archive_streaming_and_geoparquet_optimization.md`.
- Updated `.codex/prompts/11_viewer_contract.md`.
- Updated `.codex/prompts/12_static_viewer.md`.
- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md` to set
  `08_manifest_metadata_writers.md` as the current next work item and include
  Prompt 10b in the later prompt sequence.
