# ADR-003: GeoParquet Validation Toolchain

Status: Accepted

Date: 2026-06-12

## Context

Prompt 07 added a PyArrow-based GeoParquet writer and tests that validate the
written file as normal Parquet with GeoParquet metadata. An optional
Pyogrio/GDAL reader-aware check skipped locally because the installed
Pyogrio/GDAL stack could write and inspect FlatGeobuf but did not recognize
GeoParquet/Parquet as a supported vector read format.

GeoParquet-aware validation is still useful, but GDAL Parquet support depends
on the local GDAL build, Arrow/Parquet support, wheels and platform packaging.
Failing validation solely because one optional reader is unavailable would make
developer and CI behavior fragile.

## Decision

GeoParquet validation uses a layered toolchain.

Required baseline validation:

- PyArrow is the required GeoParquet validation layer.
- PyArrow checks must validate that the file opens as Parquet, row counts
  reconcile, required projection columns are present, GeoParquet `geo`
  metadata is present, geometry metadata declares the expected geometry column,
  geometry type, encoding and CRS, and quality fields are consistent.

Preferred optional GeoParquet-aware validation:

- `geoparquet-io` is the preferred optional spec-aware validator when
  installed.
- DuckDB is the preferred optional analytical reader for validating normal
  query access, row groups, metadata inspection and future bbox/spatial-pruning
  behavior.
- Pyogrio/GDAL remains a useful best-effort geospatial reader check, but it is
  not the sole GeoParquet-aware validation dependency.

Dependency policy:

- The converter runtime must not require `geoparquet-io`, DuckDB or GDAL just
  to write baseline GeoParquet.
- The project provides a `validation` optional extra for development and
  validator work. It includes PyArrow, DuckDB, `geoparquet-io` and the
  verified `pyproj==3.7.0` binary-wheel constraint used by `geoparquet-io`.
- Validation reports should distinguish errors from dependency-dependent
  skipped checks or warnings.

## Consequences

Prompt 09 bundle validation should require PyArrow checks for declared
GeoParquet files, then run `geoparquet-io`, DuckDB and Pyogrio/GDAL checks
only when those tools are available.

Unavailable optional tools should be reported as warnings or skipped checks,
not as failures, when required PyArrow validation succeeds.

Documentation and developer setup should prefer:

```bash
python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"
```

for full local writer and validation work.

The local Python 3.13/macOS `.venv/` installation initially failed when
`geoparquet-io` pulled a newer `pyproj` source distribution that required a
system PROJ executable. Installing the verified binary wheel
`pyproj==3.7.0` first resolved the issue, and the `validation` extra now pins
that version to keep the documented workflow reproducible.

## Deferred

- Choosing exact `geoparquet-io` CLI/API commands for Prompt 09.
- Choosing exact DuckDB validation queries for Prompt 09.
- Adding CI matrix entries for optional validation tools.
