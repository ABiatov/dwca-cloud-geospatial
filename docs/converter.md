# Converter API And CLI

Status: Accepted MVP behavior

Last updated: 2026-06-19

## Purpose

This document describes the repeatable local conversion, inspection and
validation workflows for the DwC-A to cloud-optimized geospatial converter.

The converter is file-based: it reads an already downloaded local Darwin Core
Archive and writes a static output bundle. It does not download archives,
contact GBIF or OBIS APIs, require a database, or start a backend service.

## Dependency Setup

Default FlatGeobuf conversion requires the optional FlatGeobuf writer stack
with writable GDAL `GPKG` and `FlatGeobuf` drivers:

```bash
python -m pip install -e "${REPO}[dev,flatgeobuf]"
```

Explicit GeoParquet-only conversion requires PyArrow, available through either
the `geoparquet` extra or the full FlatGeobuf extra:

```bash
python -m pip install -e "${REPO}[dev,geoparquet]"
```

For writer and validation work together, use:

```bash
python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"
```

## Core API

Use `dwca_cloud_geospatial.conversion.convert_dwca_archive` for conversion.
CLI and tests use this same API.

```python
from dwca_cloud_geospatial.conversion import ConversionOptions, convert_dwca_archive

result = convert_dwca_archive(
    "/path/to/archive.zip",
    "/path/to/output-bundle",
    options=ConversionOptions(output_formats=("flatgeobuf",)),
)
```

Public conversion objects:

- `ConversionOptions`: output formats, overwrite behavior and writer options.
- `ConversionResult`: input/output paths, parser result, normalization result,
  writer results and metadata writer result.
- `ConversionError`: actionable conversion failure with parser diagnostics
  when available.

Supported output format names:

- `flatgeobuf`: default output at `data/occurrences.fgb`.
- `geoparquet`: explicit analytical output at `data/occurrences.parquet`.

Pass both names to write both geospatial outputs from the same accepted
normalized occurrence record set:

```python
ConversionOptions(output_formats=("flatgeobuf", "geoparquet"))
```

Default FlatGeobuf conversion streams occurrence batches through normalization
into `data/occurrences.gpkg`, then creates `data/occurrences.fgb` from the
GeoPackage with `SPATIAL_INDEX=YES`. The GeoPackage remains in the bundle and
is inventoried in `manifest.files`.

Large GeoParquet output is enabled through `GeoParquetWriterOptions` on the
core API. It keeps the CLI default unchanged and writes single-file
GeoParquet with a `bbox` covering column, grid-based spatial ordering,
streamed rejected reports and bounded count/warning aggregation:

```python
from dwca_cloud_geospatial.geoparquet import GeoParquetWriterOptions

ConversionOptions(
    output_formats=("geoparquet",),
    geoparquet=GeoParquetWriterOptions(large_output_mode=True),
    chunk_size=10_000,
)
```

FlatGeobuf conversion no longer requires Python-side full accepted-record
materialization for its writer handoff. Combined FlatGeobuf+GeoParquet
conversion appends each accepted batch to GeoPackage and passes the same
accepted records onward to the GeoParquet writer.

Partitioned GeoParquet configuration fields exist on `GeoParquetWriterOptions`
for forward compatibility, but `partitioned_dataset=True` is rejected until the
manifest and validator contracts support partition file inventories.

## CLI Commands

Inspect an archive without conversion:

```bash
dwca-cloud-geospatial inspect /path/to/archive.zip
dwca-cloud-geospatial inspect --json /path/to/archive.zip
```

Convert with the default FlatGeobuf output:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle
```

Convert with explicit GeoParquet output:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle --format geoparquet
```

Convert with both FlatGeobuf and GeoParquet:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle --format flatgeobuf --format geoparquet
```

Validate an existing output bundle:

```bash
dwca-cloud-geospatial validate /path/to/output-bundle
dwca-cloud-geospatial validate --json /path/to/output-bundle
```

`validate` calls `dwca_cloud_geospatial.validation.validate_output_bundle`
directly. It exits non-zero only when required validation errors are present.
Dependency-dependent optional reader skips are reported as warnings or skipped
checks, not as failures.

## Overwrite Behavior

Conversion rejects any existing output path by default, including an existing
empty directory:

```text
Conversion failed: Output path already exists: /path/to/output-bundle. Pass --overwrite to replace it.
```

Pass `--overwrite` to replace an existing output path:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle --overwrite
```

The core API equivalent is:

```python
ConversionOptions(overwrite=True)
```

## Failure Behavior

Conversion fails fast when parser metadata prevents reliable occurrence row
interpretation. The core API reuses occurrence row-reader diagnostics for
missing occurrence cores and unsupported multi-file occurrence cores.

Checklist DwC-A archives with `Taxon` cores remain valid inputs for
`inspect` and `inspect --json`, but they are outside the MVP occurrence
geospatial conversion workflow. `convert` rejects them with a clear
non-occurrence input error.

Conversion also fails when:

- the Occurrence core lacks `decimalLatitude` or `decimalLongitude` terms;
- no accepted normalized occurrence records remain after quality rules;
- required writer dependencies are unavailable for the selected output format;
- metadata or output files cannot be written reliably.
- partitioned GeoParquet output is requested before the partitioned dataset
  contract is implemented.

Non-fatal warnings do not fail conversion by themselves. FlatGeobuf
`large_indexed_flatgeobuf_write` warnings are preserved in
`metadata/processing.json.warnings` with `stage="flatgeobuf_writer"`.

## Output Bundle

Default FlatGeobuf conversion writes:

```text
output-bundle/
  manifest.json
  metadata/
    source.json
    processing.json
  data/
    occurrences.gpkg
    occurrences.fgb
```

When GeoParquet is selected, `data/occurrences.parquet` is added. When one or
more records are rejected, `reports/rejected_records.csv` is written and
inventoried in `manifest.json`.

`metadata/processing.json` records GeoPackage staging enablement, staging path,
writer backend, GDAL/OGR helper strategy, whether FlatGeobuf was generated
from GeoPackage and FlatGeobuf spatial-index status.

The bundle metadata is written only through
`dwca_cloud_geospatial.bundle.write_bundle_metadata`; CLI handlers do not
duplicate manifest, processing metadata or rejected-report logic.
