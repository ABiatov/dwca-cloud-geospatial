# Prompt 06: FlatGeobuf Writer

Date: 2026-06-09

## Scope

Implemented the MVP FlatGeobuf writer for accepted normalized occurrence
records. This prompt did not implement GeoParquet, manifest, metadata,
rejected CSV, validation, CLI conversion or viewer behavior.

## Writer Stack And Dependency Behavior

- Added `dwca_cloud_geospatial.flatgeobuf.write_flatgeobuf_occurrences`.
- Default output path is `exports/occurrences.fgb` through
  `DEFAULT_FLATGEOBUF_RELATIVE_PATH`.
- The production backend is isolated behind an injectable backend boundary.
- When optional dependencies are installed, the production backend writes an
  Arrow table through `pyogrio.write_arrow` with GDAL driver `FlatGeobuf`.
- The production path does not use GeoPandas.
- The writer imports Pyogrio and PyArrow only inside the production backend.
  If they are unavailable, it raises `FlatGeobufDependencyError` with an
  actionable message instead of making the package import fail.
- Tests cover projection and writer behavior without Pyogrio/GDAL by injecting
  a capturing backend. The dependency-specific real FlatGeobuf test skips with
  an explicit reason when Pyogrio/PyArrow/GDAL are unavailable.
- Follow-up dependency verification installed the Prompt 06 writer stack into
  `.venv/` using the documented optional extra:
  `.venv/bin/python -m pip install -e '.[dev,flatgeobuf]'`.
- Verified installed writer stack:
  - `pyogrio 0.12.1`
  - `GDAL 3.11.4` as reported by Pyogrio
  - `pyarrow 24.0.0`
  - FlatGeobuf driver support: `rw`

## Projection Fields Implemented

Implemented `FLATGEOBUF_PROJECTION_COLUMNS` from `docs/output_format.md`:

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
- `taxon_rank`
- `basis_of_record`
- `degree_of_establishment`
- `iucn_red_list_category`
- `event_date`
- `event_year`
- `decimal_longitude`
- `decimal_latitude`
- `coordinate_uncertainty_in_meters`
- `country_code`
- `locality`
- `identified_by`
- `license`
- `references`
- `rights_holder`
- `dataset_name`
- `quality_flags`
- `has_quality_flags`

Projection uses `NormalizedOccurrenceRecord.to_dict()`, so the Python
attribute `class_` is emitted as output column `class`. Source camelCase
Darwin Core terms are not emitted as normalized output columns.

Geometry is written as 2D point WKB in longitude/latitude order. The writer
records the CRS assumption as `OGC:CRS84`.

## Large Dataset Guardrail Behavior

- Spatial index creation is requested by default with layer option
  `SPATIAL_INDEX=YES`.
- `FlatGeobufWriterOptions(spatial_index=False)` requests
  `SPATIAL_INDEX=NO` and suppresses spatial-index memory warnings.
- For indexed writes, the writer estimates spatial-index construction memory
  with `estimate_spatial_index_memory_bytes`.
- The default warning thresholds are:
  - feature count: `1_000_000`
  - estimated spatial-index bytes: `268_435_456`
  - per-feature estimate: `64` bytes
- Risky indexed writes emit Python `FlatGeobufLargeOutputWarning` before the
  backend write and return a structured `FlatGeobufWriterWarning` with code
  `large_indexed_flatgeobuf_write`.

## Files Created Or Updated

- Created `src/dwca_cloud_geospatial/flatgeobuf.py`.
- Updated `src/dwca_cloud_geospatial/__init__.py`.
- Created `tests/test_flatgeobuf_writer.py`.
- Updated `pyproject.toml` with the `flatgeobuf` optional dependency extra.
- Updated `docs/developer_setup.md` with FlatGeobuf writer dependency
  installation, stack verification and Prompt 06 test commands.
- Updated `docs/development_plan.md`.
- Follow-up documentation audit updated `docs/output_format.md`,
  `docs/knowledge_base/topics/flatgeobuf_output.md`,
  `docs/knowledge_base/topics/cli_and_pipeline_patterns.md` and
  `docs/knowledge_base/playbooks/validate_output_bundle.md` so project docs
  preserve the Prompt 06 dependency setup, real writer verification,
  `SPATIAL_INDEX=YES` default, `SPATIAL_INDEX=NO` explicit opt-out,
  `large_indexed_flatgeobuf_write` warning behavior and current large-data
  materialization limitation.
- Follow-up documentation consistency audit updated `docs/output_format.md`
  `Last updated`, aligned `docs/development_plan.md` with the implemented
  `pyogrio.write_arrow`/PyArrow production backend instead of a GeoDataFrame
  production path, and changed
  `docs/knowledge_base/topics/flatgeobuf_output.md` from candidate wording to
  accepted MVP output wording.
- Updated downstream prompts:
  - `.codex/prompts/08_manifest_metadata_writers.md`
  - `.codex/prompts/09_bundle_validation.md`
  - `.codex/prompts/10_core_api_cli.md`
  - `.codex/prompts/11_viewer_contract.md`
  - `.codex/prompts/12_static_viewer.md`
  - `.codex/prompts/14_demo_docs_hardening.md`
  - `.codex/prompts/dev_flow_description.md`

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`.

- `.venv/bin/python -m pytest tests/test_flatgeobuf_writer.py -q`
  - Result: passed, `5 passed, 1 skipped`.
  - Skip reason: real FlatGeobuf validation requires optional
    Pyogrio/GDAL/PyArrow dependencies, which are not installed in the local
    `.venv/`.
- `.venv/bin/python -m pytest tests -q`
  - Result: passed, `26 passed, 1 skipped`.
- Follow-up after installing Pyogrio/PyArrow/GDAL-capable Pyogrio wheel into
  `.venv/`:
  - `.venv/bin/python -c "import pyogrio, pyarrow; print('pyogrio', pyogrio.__version__); print('gdal', pyogrio.__gdal_version_string__); print('pyarrow', pyarrow.__version__); print('FlatGeobuf', pyogrio.list_drivers().get('FlatGeobuf'))"`
    - Result: `pyogrio 0.12.1`, `gdal 3.11.4`, `pyarrow 24.0.0`,
      `FlatGeobuf rw`.
  - `.venv/bin/python -m pytest tests/test_flatgeobuf_writer.py -q`
    - Result: passed, `6 passed`.
  - `.venv/bin/python -m pytest tests -q`
    - Result: passed, `27 passed`.

## Open Questions Or Risks

- Resolved follow-up: the real FlatGeobuf file path is now exercised locally
  with Pyogrio/PyArrow installed and GDAL available through Pyogrio.
- Prompt 08 or Prompt 10 should decide how conversion results surface
  `FlatGeobufDependencyError` when a user requests default conversion without
  installed writer dependencies.
- Full bundle validation of FlatGeobuf files remains dependency-dependent and
  belongs to Prompt 09.

## Prompt Updates

- Updated `pyproject.toml`.
- Updated `docs/developer_setup.md`.
- Updated `docs/development_plan.md`.
- Updated `docs/output_format.md`.
- Updated `docs/knowledge_base/topics/flatgeobuf_output.md`.
- Updated `docs/knowledge_base/topics/cli_and_pipeline_patterns.md`.
- Updated `docs/knowledge_base/playbooks/validate_output_bundle.md`.
- Updated `.codex/prompts/08_manifest_metadata_writers.md`.
- Updated `.codex/prompts/09_bundle_validation.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/11_viewer_contract.md`.
- Updated `.codex/prompts/12_static_viewer.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md` to set
  `07_geoparquet_writer.md` as the current next work item.
