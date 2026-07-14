# Converter API And CLI

Status: Accepted MVP behavior

Last updated: 2026-07-09

## Purpose

This document describes the repeatable local conversion, inspection and
validation workflows for the DwC-A to cloud-optimized geospatial converter.

The converter is file-based: it reads an already downloaded local Darwin Core
Archive and writes a static output bundle. It does not download archives,
contact GBIF or OBIS APIs by default, require a database, or start a backend
service. Optional GBIF occurrence download DOI/citation enrichment is an
explicit conversion-time action only.

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

Conversion also copies the static viewer runtime files into the output
directory and writes a generated bundle README:

```text
index.html
styles.css
app.js
README.md
```

These publishing convenience files are not listed in `manifest.files`; that
inventory remains reserved for generated data, metadata and report artifacts.
Opening `index.html` from a static HTTP server reads the neighboring
`manifest.json`. `README.md` describes the generated bundle and should not be
confused with the source `viewer/README.md`; both include the publisher-facing
visibility-control instructions relevant to their context.

The viewer-facing map Header title and App Description popup are configured
independently from dataset metadata and bundle provenance. New generated
manifests default `manifest.viewer.map_title` to
`Custom map title, edit it in manifest.json` and
`manifest.viewer.appDescription` to editable publisher-facing HTML that shows
the popup feature immediately. Python callers can override or omit either
value through `BundleWriterOptions`:

```python
from dwca_cloud_geospatial.bundle import BundleWriterOptions
from dwca_cloud_geospatial.conversion import ConversionOptions

ConversionOptions(
    bundle=BundleWriterOptions(
        viewer_map_title="Publisher-facing map title",
        viewer_app_description=(
            "<center><h2>About this map</h2></center>"
            "<p>Publisher-authored HTML.</p>"
            "<p>Supported HTML Tags: p, b, i, h2, h3, h4, a, img, br, "
            "ol, ul, li, table, tr, td, iframe, center, small</p>"
        ),
    )
)
```

Blank or whitespace-only `viewer_map_title` values are omitted from generated
manifests, and the static viewer hides the map Header without reserving layout
space. This does not change `manifest.title`,
`metadata/source.json.dataset.title` or the Dataset Info provenance title
fallback.

Blank or whitespace-only `viewer_app_description` values are also omitted from
generated manifests. The CLI does not expose a long-HTML flag; publishers can
set `BundleWriterOptions.viewer_app_description` through Python or manually
edit the generated default at `manifest.viewer.appDescription` after
conversion. The static viewer sanitizes this HTML before rendering it in the
Header App Description popup.

New generated manifests also include the complete all-visible
`manifest.viewer.visibility` tree. To hide a supported viewer element during
conversion, pass only the nested override that differs; the writer merges it
with the documented defaults without changing map title, app description,
file inventory, layers or provenance:

```python
ConversionOptions(
    bundle=BundleWriterOptions(
        viewer_visibility={
            "panel-info": {"provenance": {"doi": {"is_visible": False}}},
            "panel-download": {
                "artifacts": {"occurrences.gpkg": {"is_visible": False}}
            },
            "popup": {"is_visible": False},
        }
    )
)
```

Only the boolean value `False` hides an element in the browser. Publishers can
also edit `manifest.viewer.visibility` after conversion; omitted and partial
trees keep all unspecified elements visible.

Large GeoParquet output is enabled through `GeoParquetWriterOptions` on the
core API and through explicit CLI flags. It keeps the default conversion
behavior unchanged and writes single-file GeoParquet with a `bbox` covering
column, grid-based spatial ordering, streamed rejected reports and bounded
count/warning aggregation:

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

GBIF occurrence download citation metadata is optional and belongs in
`metadata/source.json.gbif`. Ordinary local conversion does not contact GBIF.
For reproducible no-network conversion, pass explicit values through
`GbifDownloadOptions`:

```python
from dwca_cloud_geospatial.gbif import GbifDownloadOptions

ConversionOptions(
    gbif=GbifDownloadOptions(
        download_key="0038004-260519110011954",
        doi="10.15468/dl.3xbk5b",
        citation=(
            "GBIF.org (4 June 2026) GBIF Occurrence Download "
            "https://doi.org/10.15468/dl.3xbk5b"
        ),
        license="CC_BY_NC_4_0",
    )
)
```

The converter can infer a GBIF download key from declared
`http://rs.gbif.org/terms/1.0/downloadKey` values, EML/additional metadata
containing GBIF download citations or URLs, and input archive filenames or
directory names that exactly match the GBIF download-key pattern. If
`GbifDownloadOptions(enrich=True)` is set, the converter performs a read-only
request to `GET https://api.gbif.org/v1/occurrence/download/{download_key}`.
When DOI/citation fields are missing from that JSON response, enrichment also
requests
`GET https://api.gbif.org/v1/occurrence/download/{download_key}/citation` and
extracts the DOI from the returned citation text. The lookup uses an explicit
User-Agent, JSON or text Accept headers as appropriate, connect/read timeouts,
bounded retries, exponential backoff with jitter, and `Retry-After` handling
for HTTP 429. Lookup failures are written as structured non-fatal warnings in
`metadata/processing.json.warnings`.

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

Set a viewer-facing map Header title during conversion:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle \
  --viewer-map-title "Publisher-facing map title"
```

If `--viewer-map-title` is omitted, the generated manifest uses the editable
default `Custom map title, edit it in manifest.json`. Passing a blank or
whitespace-only value omits `manifest.viewer.map_title`.

Generated manifests include an editable `manifest.viewer.appDescription`
placeholder by default. For publisher-authored app description popup content,
edit that field after conversion or configure
`BundleWriterOptions.viewer_app_description` from Python. The viewer shows the
Header button only when the value is non-blank after trimming.

Convert with explicit GeoParquet output:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle --format geoparquet
```

This writes the normal non-large GeoParquet output. Large-output mode is a
separate GeoParquet-specific option:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle \
  --format geoparquet \
  --geoparquet-large-output \
  --chunk-size 10000
```

`--geoparquet-large-output` maps to:

```python
ConversionOptions(
    output_formats=("geoparquet",),
    geoparquet=GeoParquetWriterOptions(large_output_mode=True),
    chunk_size=10_000,
)
```

`--chunk-size` controls the number of source occurrence rows handed through
each streaming parser/normalizer chunk. It must be a positive integer. When
omitted, conversion uses the core API default `ConversionOptions.chunk_size`
of `10_000`. Passing `--geoparquet-large-output` without selecting
GeoParquet output fails before conversion starts; add `--format geoparquet`
instead of expecting the CLI to silently add a new output.

Convert with both FlatGeobuf and GeoParquet:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle --format flatgeobuf --format geoparquet
```

Large-output GeoParquet can also be enabled when both outputs are selected:

```bash
dwca-cloud-geospatial convert /path/to/archive.zip /path/to/output-bundle \
  --format flatgeobuf \
  --format geoparquet \
  --geoparquet-large-output \
  --chunk-size 10000
```

This remains GeoParquet-oriented behavior. FlatGeobuf output keeps its
GeoPackage-staged indexed writer path, while GeoParquet receives the bbox
covering column and grid spatial sorting declarations. Partitioned
GeoParquet output remains deferred and is not exposed as a CLI option.

Convert with manually supplied GBIF occurrence download citation metadata and
no network access:

```bash
dwca-cloud-geospatial convert /path/to/0038004-260519110011954.zip /path/to/output-bundle \
  --gbif-download-key 0038004-260519110011954 \
  --gbif-doi 10.15468/dl.3xbk5b \
  --gbif-citation "GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b" \
  --gbif-license CC_BY_NC_4_0
```

Opt in to GBIF API enrichment when a download key can be inferred or supplied:

```bash
dwca-cloud-geospatial convert /path/to/0038004-260519110011954.zip /path/to/output-bundle --gbif-enrich
```

Read-only enrichment does not require GBIF credentials. It does not create
downloads, perform occurrence search, use taxonomy matching or add a backend
service. [GBIF citation guidance](https://www.gbif.org/citation-guidelines)
says occurrence download citations should include the DOI expressed as a URL,
and GBIF's
[API downloads documentation](https://techdocs.gbif.org/en/data-use/api-downloads)
documents the download metadata endpoint. The converter preserves citation
text in `metadata/source.json.gbif.citation`, summarizes it through
`manifest.source.citation` when dataset citation metadata is absent, and the
static viewer renders the DOI URL as a link. The resolved GBIF download
metadata is also copied to `metadata/processing.json.source_provenance.gbif`
for processing audit.

Validate an existing output bundle:

```bash
dwca-cloud-geospatial validate /path/to/output-bundle
dwca-cloud-geospatial validate --json /path/to/output-bundle
```

`validate` calls `dwca_cloud_geospatial.validation.validate_output_bundle`
directly. It exits non-zero only when required validation errors are present.
Dependency-dependent optional reader skips are reported as warnings or skipped
checks, not as failures.

## Tkinter GUI

A primitive desktop GUI is available for non-CLI users through the console
script:

```bash
dwca-cloud-geospatial-gui
```

If the shell reports `command not found`, activate the documented local
environment first or call the script by explicit path:

```bash
source "${REPO}/.venv/bin/activate"
dwca-cloud-geospatial-gui
```

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial-gui"
```

The module entry point is also available:

```bash
python -m dwca_cloud_geospatial.gui
```

The GUI uses the same core conversion API as the CLI:
`dwca_cloud_geospatial.conversion.convert_dwca_archive` with
`ConversionOptions`. It does not parse DwC-A rows, normalize records, write
geospatial files, write bundle metadata or validate bundles independently.

GUI controls:

- Input DwC-A archive or unpacked archive directory.
- Output bundle directory.
- Output formats: FlatGeobuf is selected by default; GeoParquet is explicit.
- Overwrite checkbox. Existing output paths are rejected unless this checkbox
  is selected, matching CLI `--overwrite` behavior.
- GBIF DOI citation lookup checkbox. This is selected by default and maps to
  `GbifDownloadOptions(enrich=True)`, equivalent to CLI `--gbif-enrich`.
  Clear it to keep conversion fully no-network unless explicit GBIF metadata
  was supplied through the Python API.
- Optional validation after conversion, using
  `dwca_cloud_geospatial.validation.validate_output_bundle`.
- GeoParquet large-output mode, labeled as GeoParquet-only behavior. This maps
  to `GeoParquetWriterOptions(large_output_mode=True)` and the configured
  conversion chunk size. Partitioned GeoParquet output is not exposed because
  it is not implemented.

The GUI status panel reports accepted and rejected counts from the core
conversion result, generated paths, non-fatal conversion warnings and
validation results. FlatGeobuf large indexed-write warnings such as
`large_indexed_flatgeobuf_write` are shown separately from conversion
failures. GBIF citation lookup failures are shown as non-fatal warnings when
the lookup checkbox is selected. When FlatGeobuf conversion returns a retained
GeoPackage staging artifact, the GUI shows the `data/occurrences.gpkg` path as
an artifact.

Validation output separates required validation errors from warnings and
dependency-dependent skipped checks. Required errors indicate an invalid
bundle; skipped optional reader checks indicate local validation tooling or
driver support was unavailable.

The GUI can open the generated output directory and shows static viewer
instructions. Generated bundles include the copied viewer entry point at:

```text
<output>/index.html
```

For a local browser check, serve the output parent and open the copied viewer:

```bash
python -m http.server 8000 --directory /path/to/output-parent
```

```text
http://localhost:8000/output-bundle/index.html
```

FlatGeobuf bundles use `data/occurrences.fgb` as the MVP browser map source.
The retained `data/occurrences.gpkg` file is artifact/download metadata only.
GeoParquet-only bundles are valid and open in the copied viewer as a
metadata/provenance/artifact inventory state with no MVP map layer. In that
state, the viewer tells users to generate the bundle with the FlatGeobuf
output format selected if they want occurrence points to appear on the map.

The GUI status and viewer-instructions text can be copied with the right-click
context menu (`Copy` / `Copy all`) or the `Copy Text` button. Keyboard copy
shortcuts (`Ctrl+C` / `Cmd+C`) are currently a Tk/macOS limitation in this MVP
and should not be relied on until they are verified interactively.

The Python GUI does not start a backend service and does not bundle offline
frontend assets. The copied static viewer still references MapLibre GL JS and
FlatGeobuf JavaScript from public CDN URLs and uses OpenStreetMap raster tiles
as its default basemap; see `viewer/README.md` for viewer launch details and
offline-hosting considerations.

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
  index.html
  styles.css
  app.js
  README.md
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

Static hosting and external demo review steps, including default FlatGeobuf
bundles, explicit GeoParquet-only bundles and checklist negative examples, are
documented in `docs/deployment.md`.
