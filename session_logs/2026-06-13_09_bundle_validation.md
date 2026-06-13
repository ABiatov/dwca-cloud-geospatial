# Prompt 09: Bundle Validation

Date: 2026-06-13

## Scope

Implemented core validation for generated static output bundles. This prompt
did not change the accepted output format and did not implement the CLI
`validate` command; Prompt 10 should wire the CLI to the core validator.

## Validator API Summary

- Added `dwca_cloud_geospatial.validation.validate_output_bundle(bundle_root)`.
- Added structured result objects:
  - `BundleValidationResult`
  - `BundleValidationIssue`
  - `BundleValidationCheck`
- Exported the validator API from `dwca_cloud_geospatial`.
- `BundleValidationResult.status` is `passed`, `passed_with_warnings` or
  `failed`.
- Required failures are reported in `BundleValidationResult.errors`.
- Dependency-dependent skips and optional-reader issues are reported in
  `BundleValidationResult.warnings` and structured `checks`.
- Result helpers include `has_errors`, `skipped_checks`, `to_dict()` and
  `to_json()` for future CLI and GUI consumers.

## Checks Implemented

Implemented validation for:

- required `manifest.json`, `metadata/source.json` and
  `metadata/processing.json` existence and JSON parsing;
- supported `bundle_schema_version`, `viewer_contract_version` and
  `occurrence_schema_version`;
- safe relative paths in `manifest.files`;
- existence of every declared `manifest.files[].path`;
- manifest byte-size and SHA-256 checksum reconciliation when declared;
- required metadata files being included in `manifest.files`;
- required PyArrow validation for declared GeoParquet files;
- GeoParquet required projection columns, binary WKB `geometry`, `geo`
  metadata, version `1.1.0`, primary geometry column, point geometry type,
  WKB encoding, `OGC:CRS84` CRS and bbox shape when present;
- nullable string `quality_flags`, `|` exact-token splitting and lowercase
  snake_case token validation;
- `has_quality_flags` consistency where present;
- optional GeoParquet-aware checks through `geoparquet-io`, DuckDB and
  Pyogrio/GDAL when available;
- dependency-dependent FlatGeobuf inspection through Pyogrio/GDAL when
  available, including required projection fields, point geometry and feature
  count reconciliation;
- row-count reconciliation across manifest counts, processing counts,
  geospatial outputs and rejected-record reports;
- `reports/rejected_records.csv` required columns and report row counts;
- viewer display/filter fields being present in inspected generated data;
- processing `warning_count`, processing warning structure,
  `large_indexed_flatgeobuf_write` warning fields, and
  `type_conversion_failures` structure/rates;
- nullable GBIF and OBIS source provenance fields as valid nulls.

## Dependency-Dependent Checks

- PyArrow is required for declared GeoParquet validation. Missing PyArrow is a
  validation error when a GeoParquet file is declared.
- `geoparquet-io` is optional. When import/read succeeds, the validator records
  row count, geometry column and GeoParquet version; unavailable or unreadable
  optional checks are warnings/skipped checks, not required failures.
- DuckDB is optional. When available, the validator reads the declared
  GeoParquet file with `read_parquet` and reconciles row counts.
- Pyogrio/GDAL GeoParquet validation is optional and may skip when the local
  GDAL build cannot read Parquet/GeoParquet.
- FlatGeobuf inspection is dependency-dependent. If Pyogrio/GDAL or the
  FlatGeobuf driver is unavailable, the validator records a skipped check. If
  the dependency is available and a declared FlatGeobuf file cannot be opened
  or lacks required fields, validation fails.

## Optional Validation Tool Versions

Verified local `.venv/` validation stack:

- PyArrow `24.0.0`
- DuckDB `1.5.1`
- geoparquet-io `1.3.0`
- pyproj `3.7.0`
- Pyogrio `0.12.1`
- GDAL `3.11.4`
- FlatGeobuf driver `rw`

The version-check command emitted PyArrow sandbox-related CPU-feature warnings
from Arrow's `sysctlbyname` probes, but imports and validation completed.

## Failure Cases Tested

Added `tests/test_bundle_validation.py` covering:

- valid GeoParquet bundle validation;
- valid rejected-record report reconciliation;
- missing declared inventory file;
- checksum mismatch when `sha256` is present;
- missing required GeoParquet projection column;
- manifest/processing count mismatch;
- rejected CSV missing required columns;
- viewer field declared but absent from inspected data;
- invalid `quality_flags` token splitting and `has_quality_flags` mismatch;
- nullable GBIF and OBIS source fields accepted as null;
- real FlatGeobuf declaration validation when Pyogrio/PyArrow/GDAL are
  available.

## Files Created Or Updated

- Created `src/dwca_cloud_geospatial/validation.py`.
- Updated `src/dwca_cloud_geospatial/__init__.py`.
- Created `tests/test_bundle_validation.py`.
- Updated `docs/development_plan.md`.
- Updated `docs/output_format.md`.
- Updated `docs/developer_setup.md`.
- Updated `docs/knowledge_base/topics/validation_and_quality.md`.
- Updated `docs/knowledge_base/topics/geoparquet_output.md`.
- Updated `docs/knowledge_base/playbooks/validate_output_bundle.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/10b_large_archive_streaming_and_geoparquet_optimization.md`.
- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md`.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`, equivalent to the documented full writer and
validation install `python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"`.

- `.venv/bin/python -m py_compile src/dwca_cloud_geospatial/validation.py`
  - Result: passed.
- `.venv/bin/python -m pytest tests/test_bundle_validation.py -q`
  - Result: passed, `11 passed`.
- `.venv/bin/python -m pytest tests/test_bundle_validation.py -q -rs`
  - Result: passed, `11 passed`.
- `.venv/bin/python -m pytest tests -q`
  - Result: passed, `46 passed, 1 skipped`.
  - The remaining skip is the existing dependency-dependent Prompt 07
    Pyogrio/GDAL GeoParquet-aware reader test, where local GDAL Parquet read
    support is unavailable.
- `.venv/bin/python -c "import importlib.metadata as m, pyarrow, duckdb, pyogrio; ..."`
  - Result: printed the validation stack versions listed above.

## Open Questions Or Risks

- The CLI `validate` command is still a stub until Prompt 10 wires it to
  `validate_output_bundle`.
- The validator currently validates single-file GeoParquet outputs and
  checks large-output declarations when present, but partitioned GeoParquet
  dataset validation remains future work with Prompt 10b.
- FlatGeobuf attribute-level `quality_flags` validation depends on readable
  geospatial table support; current validation checks FlatGeobuf projection
  fields and counts through Pyogrio/GDAL when available.

## Prompt Updates

- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/10b_large_archive_streaming_and_geoparquet_optimization.md`.
- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md` to set
  `10_core_api_cli.md` as the current next work item.
