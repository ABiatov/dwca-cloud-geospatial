# Deployment And Demo Review

Status: Accepted MVP static hosting workflow

Last updated: 2026-06-24

## Purpose

This document describes how to publish and review generated DwC-A geospatial
output bundles with static files only.

The MVP deployment model is deliberately small: generate a local bundle, serve
or copy that directory to static hosting, and open the copied viewer
`index.html`. No Python backend, project API, database, live GBIF/OBIS lookup,
taxonomy service or cloud-specific runtime is required after conversion.

## Local Demo Workflow

Use the documented in-repository virtual environment:

```bash
git clone https://github.com/ABiatov/dwca-cloud-geospatial.git
cd dwca-cloud-geospatial
export REPO="$(pwd)"
python -m venv "${REPO}/.venv"
source "${REPO}/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"
```

Create a default FlatGeobuf bundle from the local occurrence fixture:

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial" convert \
  "${REPO}/tests/fixtures/dwca/minimal_occurrence/normalization" \
  "${REPO}/scratch/sample-bundle" \
  --overwrite
```

Validate it:

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial" validate \
  "${REPO}/scratch/sample-bundle"
```

Serve the repository or any parent directory containing the bundle:

```bash
python -m http.server 8000 --directory "${REPO}"
```

Open the copied viewer:

```text
http://localhost:8000/scratch/sample-bundle/index.html
```

The shared source viewer can also load a generated bundle explicitly:

```text
http://localhost:8000/viewer/?bundle=../scratch/sample-bundle/
```

## Output Types To Review

Default FlatGeobuf bundles include:

```text
index.html
styles.css
app.js
README.md
manifest.json
metadata/source.json
metadata/processing.json
data/occurrences.gpkg
data/occurrences.fgb
reports/rejected_records.csv   # only when records are rejected
```

`data/occurrences.fgb` is the MVP browser map layer. `data/occurrences.gpkg`
is a retained GeoPackage staging artifact and download/audit item, not the
default browser map layer.

Explicit GeoParquet-only bundles are valid and may omit
`data/occurrences.fgb`:

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial" convert \
  "${REPO}/tests/fixtures/dwca/minimal_occurrence/normalization" \
  "${REPO}/scratch/sample-geoparquet-only" \
  --format geoparquet \
  --overwrite
```

The copied viewer opens these bundles as metadata, provenance and artifact
inventory pages with the accepted no-map-layer message:

```text
No FlatGeobuf map layer is available for this bundle. To display occurrence points on the map, generate the bundle with the FlatGeobuf output format selected.
```

GeoParquet large-output mode is GeoParquet-specific MVP behavior. It can be
enabled for GeoParquet-only bundles or for the GeoParquet output in a
multi-format bundle. It uses chunked parser/normalizer/writer handoff, writes
a `bbox` covering column and records spatial sorting configuration in
processing metadata. Browser GeoParquet loading and partitioned GeoParquet
datasets are deferred.

## Static Hosting Requirements

A static host should serve the generated bundle files directly:

- JSON files as `application/json` or text.
- CSV reports as text.
- FlatGeobuf, GeoPackage and GeoParquet files as binary downloads.
- `index.html`, `styles.css` and `app.js` from the bundle root.

For remote FlatGeobuf map performance, prefer hosts that support HTTP range
requests. If the viewer and bundle are on different origins, configure CORS so
the viewer can fetch `manifest.json`, metadata files and declared artifacts.

The current viewer references MapLibre GL JS and FlatGeobuf JavaScript from
public CDN URLs and uses OpenStreetMap raster tiles as the default basemap.
These are frontend static assets, not a project backend or biodiversity-data
API. Fully offline hosting must mirror those JavaScript/CSS assets, replace or
mirror the basemap URL, and update the copied/source viewer files.

## Checklist Archive Boundary

Checklist DwC-A archives with `Taxon` cores are valid inspection inputs but
not MVP geospatial conversion inputs. Use:

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial" inspect --json \
  "${REPO}/tests/fixtures/dwca/dwca-appendixiibernconventionua-v1.2.zip"
```

Conversion fails with an actionable non-occurrence error when no Occurrence
core is declared. This is expected and should be included in demo evidence for
checklist archives.

## Known MVP Limitations

- The converter only writes geospatial outputs from occurrence archives with
  declared coordinate terms.
- Multi-file occurrence-core streaming is deferred.
- PMTiles generation is deferred to MVP+.
- Browser GeoParquet loading is deferred; GeoParquet-only bundles use the
  no-FlatGeobuf state in the viewer.
- Partitioned GeoParquet datasets are rejected until manifest and validation
  contracts support partition inventories.
- FlatGeobuf conversion avoids Python-side full accepted-record
  materialization by staging through GeoPackage, but GDAL may still need
  substantial memory while building the final indexed FlatGeobuf. Five million
  accepted records estimate about 320,000,000 bytes for spatial-index
  construction and emit `large_indexed_flatgeobuf_write`.
- Optional GBIF DOI/citation enrichment is conversion-time only. Generated
  bundles and the copied viewer do not call GBIF, OBIS or a project backend.

## MVP+ Roadmap

Recommended follow-up work:

- PMTiles generation and viewer layer support as an optional tiled map output.
- Partitioned GeoParquet dataset manifest and validation support.
- Multi-file occurrence-core streaming.
- Offline viewer asset packaging or documented mirroring workflow.
- Packaged desktop distribution after the Tkinter workflow is stable.
