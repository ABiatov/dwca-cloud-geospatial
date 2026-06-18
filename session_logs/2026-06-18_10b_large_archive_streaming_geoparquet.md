# Prompt 10b: Large Archive Streaming And GeoParquet Optimization

Date: 2026-06-18

## Public API And Internal Handoff Summary

- Added `dwca_cloud_geospatial.occurrence.stream_occurrence_row_batches`.
- Added `OccurrenceRowStream` and `OccurrenceRowBatch`.
- Added `dwca_cloud_geospatial.normalization.normalize_occurrence_record_batch`.
- Added `ConversionOptions.chunk_size`.
- Extended `GeoParquetWriterOptions` with:
  - `large_output_mode`
  - `covering_bbox_column`
  - `spatial_sorting`
  - `spatial_sort_strategy`
  - `spatial_sort_grid_degrees`
  - partitioned-output configuration fields.
- Extended `GeoParquetWriteResult` with large-output, covering bbox, spatial
  sorting and partitioned-output declaration fields.
- Added exported GeoParquet constants `BBOX_COLUMN` and
  `GEOPARQUET_LARGE_PROJECTION_COLUMNS`.
- Added `RejectedRecordsCsvWriter` for lazy rejected-record CSV writing.

The Prompt 10 conversion API remains the main entry point. Default conversion
still writes FlatGeobuf. The bounded-memory conversion route is selected for
GeoParquet-only conversion when
`GeoParquetWriterOptions(large_output_mode=True)` is used.

## Chunking And Bounded-Memory Decisions

- `read_occurrence_rows` remains available and collected for existing tests and
  compatibility callers.
- `stream_occurrence_row_batches` performs the same inspection and occurrence
  core validation, then yields bounded source-record batches.
- Chunked conversion normalizes each batch, writes rejected rows immediately,
  yields accepted rows into the GeoParquet writer and aggregates counts,
  conversion failures, warning rates and first metadata values without
  retaining full accepted/rejected tuples.
- `ConversionResult` for the streaming large-output path returns empty
  `occurrence_result.records`, `normalization_result.accepted_records` and
  `normalization_result.rejected_records`; counts and metadata fields remain
  reconciled.
- Combined FlatGeobuf+GeoParquet conversion still uses the existing FlatGeobuf
  writer handoff, which materializes accepted rows for the current
  GDAL/Pyogrio backend.

## GeoParquet Bbox Covering And Spatial Sorting

- Large-output GeoParquet writes GeoParquet `1.1.0`, WKB point geometry,
  `OGC:CRS84`, ZSTD compression and default row groups of `100_000`.
- Large-output mode writes a default-on `bbox` struct column with `xmin`,
  `ymin`, `xmax` and `ymax`. For point geometry, all bbox fields equal the row
  longitude/latitude point bounds.
- GeoParquet footer metadata declares the `bbox` covering under the geometry
  column.
- Large-output spatial sorting is default-on with the implemented `grid`
  strategy. The strategy streams projected rows into temporary coarse lon/lat
  bucket files, then emits buckets in sorted spatial order. It does not call
  `sorted(records)` on the full archive.

## Partitioned Output Decision

Partitioned GeoParquet dataset output remains deferred. The writer exposes
configuration fields for forward compatibility, but
`partitioned_dataset=True` raises an actionable `ValueError` until the manifest
and validator contract can represent partition inventories, aggregate row
counts and per-partition GeoParquet metadata cleanly.

## Metadata And Validation Changes

- `metadata/processing.json.configuration.geoparquet` now records:
  - `large_output_mode`
  - `covering_bbox_column.enabled`
  - `covering_bbox_column.strategy`
  - `spatial_sorting.enabled`
  - `spatial_sorting.strategy`
  - `partitioned_dataset.enabled`
  - `partitioned_dataset.partition_key`
  - `partitioned_dataset.threshold`
- Metadata writers can consume summary first-source and first-accepted values
  when full source/accepted tuples are not retained.
- The rejected-record report can be written through `RejectedRecordsCsvWriter`
  before metadata inventory/checksum writing.
- Required PyArrow validation now checks GeoParquet `bbox` struct schema,
  covering metadata declaration and point bbox values when the column is
  present.

## Synthetic Large-Output Test Strategy And Results

No large generated datasets were committed. Tests use small fixtures with
small `chunk_size` and `row_group_size` values to force the same API handoff:

- occurrence rows streamed in bounded batches;
- conversion streamed GeoParquet-only large-output mode with `chunk_size=2`;
- rejected rows were written through the streaming report path;
- large GeoParquet output included the `bbox` struct column;
- grid spatial order was verified using computed bucket keys;
- validation caught deliberately corrupted bbox values;
- counts reconciled across processing metadata, manifest and generated files.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow.

```bash
.venv/bin/python -m compileall -q src tests
```

Result: passed.

```bash
.venv/bin/python -m pytest
```

Result: 61 passed, 1 skipped.

The skipped test is the existing dependency-dependent Pyogrio/GDAL
GeoParquet-aware reader check.

## Known Limitations And Remaining Large-Output Risks

- Large-output bounded-memory claims apply to GeoParquet-only conversion.
  FlatGeobuf and combined FlatGeobuf+GeoParquet conversion still use the
  current materialized FlatGeobuf writer handoff.
- The `grid` spatial sort avoids full-record sorting but can still create a
  large temporary bucket file for highly concentrated data. It bounds Python
  record retention, not disk usage.
- Partitioned GeoParquet datasets are deferred and rejected when requested.
- Multi-file occurrence core streaming remains deferred.
- Optional reader validation still depends on local `geoparquet-io`, DuckDB
  and Pyogrio/GDAL availability.

## Prompt Updates

- `.codex/prompts/11_viewer_contract.md`
- `.codex/prompts/12_static_viewer.md`
- `.codex/prompts/13_tkinter_gui.md`
- `.codex/prompts/14_demo_docs_hardening.md`
- `.codex/prompts/dev_flow_description.md`
