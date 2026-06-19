# Prompt 10c: Optimized FlatGeobuf Via GeoPackage Staging

Date: 2026-06-18

## Public API And Internal Handoff Summary

- Added `DEFAULT_GEOPACKAGE_RELATIVE_PATH` for `data/occurrences.gpkg`.
- Added `GeoPackageWriteResult`.
- Added `GeoPackageStagedFlatGeobufWriter` for incremental accepted-batch
  writes into persistent GeoPackage staging followed by final FlatGeobuf
  export.
- Added `write_flatgeobuf_occurrences_via_geopackage`.
- Extended `FlatGeobufWriteResult` with:
  - `staging_result`;
  - `generated_from_geopackage`;
  - `helper_strategy`.
- Extended `FlatGeobufWriterOptions` with:
  - `geopackage_relative_path`;
  - `geopackage_layer`;
  - `export_batch_size`.
- Exported the new public staging path/result/writer helpers from
  `dwca_cloud_geospatial`.

Core conversion now selects the streaming conversion path whenever FlatGeobuf
is requested and no dependency-isolated legacy test backend is injected.
Accepted normalized batches are appended to `data/occurrences.gpkg`. If
GeoParquet is also selected, the same accepted records are yielded onward to
the GeoParquet writer without requiring a second normalization pass.

## Chosen GeoPackage Writer And GDAL/OGR Helper Strategy

Selected strategy: Pyogrio/GDAL through Arrow, not GeoPandas and not `ogr2ogr`.

- GeoPackage batch writer: `pyogrio.write_arrow` with driver `GPKG`, layer
  `occurrences`, point geometry and `OGC:CRS84`.
- Final FlatGeobuf helper: `pyogrio.open_arrow(..., use_pyarrow=True)` on the
  GeoPackage layer passed to `pyogrio.write_arrow` with driver `FlatGeobuf`.
- Final FlatGeobuf layer options: `SPATIAL_INDEX=YES`.
- `.venv` `ogr2ogr` executable was not present; no install was needed because
  the Pyogrio/GDAL route was available and verified.

## Dependency And Tool Versions

No dependency installation was performed in this session.

Verification command:

```bash
.venv/bin/python -c "import shutil, pyogrio, pyarrow; print('pyogrio', pyogrio.__version__); print('gdal', pyogrio.__gdal_version_string__); print('pyarrow', pyarrow.__version__); print('GPKG', pyogrio.list_drivers().get('GPKG')); print('FlatGeobuf', pyogrio.list_drivers().get('FlatGeobuf')); print('ogr2ogr', shutil.which('ogr2ogr'))"
```

Result:

```text
pyogrio 0.12.1
gdal 3.11.4
pyarrow 24.0.0
GPKG rw
FlatGeobuf rw
ogr2ogr None
```

The command emitted PyArrow CPU feature `sysctlbyname` warnings under the
sandbox, but imports and driver checks completed successfully.

## Retained And Inventoried GeoPackage

`data/occurrences.gpkg` is retained after conversion whenever FlatGeobuf is
generated. It is added to `manifest.files` with:

- role `geopackage`;
- media type `application/geopackage+sqlite3`;
- byte size;
- SHA-256;
- accepted record count.

It is not added as the default viewer map layer. `data/occurrences.fgb`
remains the preferred MVP viewer layer when present.

## FlatGeobuf Spatial Index Behavior And Remaining Risks

The optimized path requires `FlatGeobufWriterOptions.spatial_index=True`.
If a staged FlatGeobuf conversion requests `spatial_index=False`, conversion
fails with an actionable `ValueError` instead of silently producing an
unindexed FlatGeobuf fallback.

Large indexed writes still emit the non-fatal structured warning
`large_indexed_flatgeobuf_write`.

Remaining scale risk: Python-side full accepted-record materialization is
removed from the FlatGeobuf writer handoff, but GDAL still builds the final
FlatGeobuf packed spatial index. Very large accepted record counts can still
consume substantial memory or fail during final `SPATIAL_INDEX=YES` export.

## Metadata And Validation Changes

Processing metadata now includes:

- `counts.geopackage_records`;
- `configuration.geopackage_staging`;
- `configuration.flatgeobuf.generated_from_geopackage`;
- `configuration.flatgeobuf.helper_strategy`;
- `output_decisions.geopackage_staging_enabled`;
- `output_decisions.geopackage_staging_relative_path`;
- `output_decisions.geopackage_staging_writer_backend`;
- `output_decisions.flatgeobuf_generated_from_geopackage`;
- `output_decisions.gdal_ogr_helper_strategy`;
- `output_decisions.flatgeobuf_spatial_index`.

Bundle validation now checks declared GeoPackage artifacts:

- manifest existence, byte size and checksum through the existing inventory
  checks;
- SQLite openability;
- `gpkg_contents` and `gpkg_geometry_columns` metadata tables;
- occurrence layer row count;
- required projection columns through SQLite `PRAGMA table_info`;
- optional Pyogrio/GDAL inspection when available;
- GeoPackage, FlatGeobuf and accepted-record count reconciliation.

## Test Strategy And Results

Added small deterministic tests using existing minimal fixtures and small
chunk sizes:

- real GeoPackage-staged FlatGeobuf writer integration test;
- default FlatGeobuf conversion with `chunk_size=2`;
- retained `data/occurrences.gpkg`;
- `data/occurrences.fgb` generated with spatial index requested;
- both files inventoried in `manifest.files`;
- GeoPackage and FlatGeobuf counts reconcile;
- streamed rejected records are counted and written;
- `quality_flags` and `has_quality_flags` are preserved;
- same accepted record set across readable GeoPackage and FlatGeobuf;
- validator accepts the staged FlatGeobuf bundle.

## Verification Commands And Results

Focused verification:

```bash
.venv/bin/python -m pytest tests/test_flatgeobuf_writer.py tests/test_conversion.py tests/test_bundle_validation.py -q
```

Result:

```text
25 passed in 1.76s
```

Full verification:

```bash
.venv/bin/python -m pytest tests -q
```

Result:

```text
63 passed, 1 skipped in 2.74s
```

Verification used the documented in-repository `.venv/` workflow.

## Documentation Updated

- `README.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/converter.md`
- `docs/knowledge_base/topics/flatgeobuf_output.md`
- `docs/knowledge_base/topics/validation_and_quality.md`
- `docs/knowledge_base/topics/cli_and_pipeline_patterns.md`
- `docs/knowledge_base/playbooks/validate_output_bundle.md`
- `.codex/prompts/dev_flow_description.md`

## Known Limitations And Remaining Risks

- GDAL spatial-index construction remains the primary large-output memory
  risk for FlatGeobuf.
- GeoPackage validation falls back to SQLite metadata checks when optional
  Pyogrio/GDAL inspection is unavailable.
- The legacy `write_flatgeobuf_occurrences` API remains available for small
  callers and dependency-isolated tests; core default conversion now uses the
  staged writer path.
- Partitioned GeoParquet remains deferred.
- GeoPackage is not accepted as the MVP default browser map source; viewer
  work should treat it as a retained artifact unless the viewer contract
  changes.

## Prompt Updates

Changed later prompt files:

- `.codex/prompts/11_viewer_contract.md`
- `.codex/prompts/12_static_viewer.md`
- `.codex/prompts/13_tkinter_gui.md`
- `.codex/prompts/14_demo_docs_hardening.md`
- `.codex/prompts/dev_flow_description.md`

The prompt-flow next work item was advanced to `11_viewer_contract.md`.
