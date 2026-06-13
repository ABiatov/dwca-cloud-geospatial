# Prompt 08: Manifest And Metadata Writers

Date: 2026-06-13

## Scope

Implemented the MVP static output bundle metadata writers. This prompt writes
`manifest.json`, `metadata/source.json`, `metadata/processing.json` and the
conditional `reports/rejected_records.csv` report. It does not implement the
Prompt 09 full bundle validator, Prompt 10 core conversion orchestration or
CLI conversion.

## Metadata Writer APIs

- Added `dwca_cloud_geospatial.bundle.write_bundle_metadata`.
- Added `build_source_metadata` for `metadata/source.json` content.
- Added `build_processing_metadata` for `metadata/processing.json` content.
- Added `write_rejected_records_csv` for conditional rejected-record reports.
- Added `BundleWriterOptions` for bundle id, title, timestamp, generator and
  effective user configuration handoff.
- Added `BundleMetadataWriteResult` with written paths, inventory and counts.
- Added path/version constants:
  - `BUNDLE_SCHEMA_VERSION`
  - `VIEWER_CONTRACT_VERSION`
  - `OCCURRENCE_SCHEMA_VERSION`
  - `MANIFEST_RELATIVE_PATH`
  - `SOURCE_METADATA_RELATIVE_PATH`
  - `PROCESSING_METADATA_RELATIVE_PATH`
  - `REJECTED_RECORDS_RELATIVE_PATH`
- Exported the new metadata writer APIs from `dwca_cloud_geospatial`.

The writer accepts the current Prompt 03 `OccurrenceReadResult`, Prompt 04/05
`OccurrenceNormalizationResult`, and whichever Prompt 06/07 geospatial writer
results were produced: `FlatGeobufWriteResult` and optionally
`GeoParquetWriteResult`.

## File Inventory And Count Behavior

- `manifest.files` inventories generated files only.
- `metadata/source.json` and `metadata/processing.json` are always generated.
- `data/occurrences.parquet` is listed only when a `GeoParquetWriteResult` is
  supplied.
- `exports/occurrences.fgb` is listed only when a `FlatGeobufWriteResult` is
  supplied.
- `reports/rejected_records.csv` is written and listed only when
  `OccurrenceNormalizationResult.rejected_records` is non-empty.
- File inventory entries include relative path, role, media type, byte size,
  SHA-256 checksum and row count where applicable.
- Manifest high-level counts use source, accepted and rejected counts from
  normalization and report `occurrence_records` as accepted records.
- Processing counts include `source_records`, `parsed_records`,
  `accepted_records`, `rejected_records`, `warning_count`,
  `geoparquet_records` and `flatgeobuf_records`.
- Processing `warning_count` is the number of warnings written to
  `metadata/processing.json.warnings`, including normalization warnings and
  any preserved writer warnings.

## Source Metadata Behavior And Limitations

- The writer reads the declared `ArchiveMetadata.metadata_file` when present
  and safely available for unpacked directories and zip archives.
- EML extraction currently captures common dataset and rights fields such as
  title, description, publisher, homepage, DOI, citation, license and rights
  text when those values are present in simple EML structures.
- Missing EML fields remain null.
- GBIF and OBIS values are not invented. GBIF dataset/download keys and OBIS
  dataset/resource ids are populated only from matching declared source terms
  when present in source records; otherwise they remain null.
- Full EML coverage is intentionally limited to the source metadata fields
  needed for the MVP bundle. More specialized EML sections can be added later
  without changing the bundle paths.

## Processing Metadata Behavior

- Processing metadata records generator, input archive summary, effective
  configuration, configuration hash, field mapping, quality rules, counts,
  type conversion failures, warnings, parser diagnostics and a validation
  placeholder with `status: "not_run"`.
- Field mapping preserves normalized output names, including `class` instead
  of Python attribute `class_`.
- Processing metadata records the current large-output GeoParquet declarations
  as disabled/null for `covering_bbox_column`, `spatial_sorting` and
  `partitioned_dataset` until Prompt 10b implements those modes.
- FlatGeobuf writer warning `large_indexed_flatgeobuf_write` is preserved with
  `stage: "flatgeobuf_writer"`, `feature_count` and
  `estimated_spatial_index_bytes`. Conversion-specific warning fields are null
  for that writer warning.

## Tests Added

- Added `tests/test_bundle_metadata.py`.
- Covered FlatGeobuf-only default bundle inventory with no rejected report.
- Covered explicit GeoParquet bundle inventory with a rejected-record report.
- Covered size/checksum inventory entries, count reconciliation, EML title
  extraction, GBIF/OBIS null behavior, viewer field projection filtering and
  FlatGeobuf writer warning preservation in processing metadata.

## Documentation Updates

- Updated `docs/output_format.md` warning metadata fields so processing
  warnings can include both normalization warnings and writer warnings.
- Updated `docs/development_plan.md` to move EML extraction from deferred work
  into the metadata writer stage and to set validation/core API work as the
  next action.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`.

- `.venv/bin/python -m pytest tests/test_bundle_metadata.py -q`
  - Result: passed, `2 passed`.
- `.venv/bin/python -m pytest tests/test_bundle_metadata.py tests/test_flatgeobuf_writer.py tests/test_geoparquet_writer.py -q`
  - Result: passed, `14 passed, 1 skipped`.
  - Skip reason is the existing dependency-dependent GeoParquet-aware
    Pyogrio/GDAL reader check.
- `.venv/bin/python -m pytest tests -q`
  - Result: passed, `35 passed, 1 skipped`.

## Open Questions Or Risks

- The metadata writer currently consumes materialized `OccurrenceReadResult`
  and `OccurrenceNormalizationResult` objects. Prompt 10b should add a
  chunked-compatible metadata summary or adapter before claiming support for
  very large archives.
- Prompt 09 still owns full validation of manifests, checksums, geospatial
  files, rejected reports and count reconciliation.

## Prompt Updates

- Updated `.codex/prompts/09_bundle_validation.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/10b_large_archive_streaming_and_geoparquet_optimization.md`.
- Updated `.codex/prompts/11_viewer_contract.md`.
- Updated `.codex/prompts/12_static_viewer.md`.
- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
