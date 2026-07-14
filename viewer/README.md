# Static Viewer

This directory contains the source copy of the minimal static MapLibre viewer
for generated DwC-A output bundles. `dwca-cloud-geospatial convert` copies
these files into each output bundle root.

The viewer reads `manifest.json`, `metadata/source.json` and
`metadata/processing.json` from a bundle root. If a declared FlatGeobuf point
layer is available, it loads `data/occurrences.fgb` in the browser. Declared
GeoPackage and GeoParquet files are shown as generated artifacts; they are not
loaded as MVP browser map layers.

## Manifest visibility controls

`manifest.viewer.visibility` is optional presentation configuration for this
static viewer. New converter output writes the complete all-visible tree;
older or partial manifests keep unspecified elements visible. Only the JSON
boolean `false` at an `is_visible` node hides the target.

It can independently hide sidebar panels and their launcher buttons, Info
blocks and named provenance rows, filter groups, the five named download
artifacts, bottom-panel content/sections, and point popups. The artifact keys
are `occurrences.fgb`, `occurrences.gpkg`, `occurrences.parquet`,
`source.json` and `processing.json`; they map only to the corresponding
standard bundle paths. Unlisted inventory artifacts retain normal display.

`bottom-toggle-bar` is not a visibility key. Use `bottom-panels`,
`bottom-panels-content`, `feature_details` and `processing` for footer
presentation. Visibility changes only the interface: it never removes files
from `manifest.json`, changes data or provenance, or introduces a backend.

## Local Launch

Create a bundle with the documented converter workflow, then serve a directory
that contains both `viewer/` and the bundle:

```bash
git clone https://github.com/ABiatov/dwca-cloud-geospatial.git
cd dwca-cloud-geospatial
export REPO="$(pwd)"
python -m venv "${REPO}/.venv"
source "${REPO}/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e "${REPO}[dev,flatgeobuf]"
"${REPO}/.venv/bin/dwca-cloud-geospatial" convert \
  "${REPO}/tests/fixtures/dwca/minimal_occurrence/normalization" \
  "${REPO}/scratch/sample-bundle" \
  --overwrite
python -m http.server 8000 --directory "${REPO}"
```

Open the copied viewer:

```text
http://localhost:8000/scratch/sample-bundle/index.html
```

The source viewer can also be used directly:

```text
http://localhost:8000/viewer/?bundle=../scratch/sample-bundle/
```

For an explicit GeoParquet-only bundle, use `--format geoparquet`; the same
viewer URL loads metadata, counts, processing warnings and generated-file
inventory, then shows the accepted no-FlatGeobuf map state. That state tells
users to generate the bundle with the FlatGeobuf output format selected if
they want occurrence points to appear on the map.

The browser loads MapLibre GL JS and FlatGeobuf JavaScript from public CDN
URLs. The map uses the public OpenStreetMap raster tile endpoint as a basemap
with visible attribution. To run fully offline, mirror those assets, configure
an alternative basemap and update `viewer/index.html` / `viewer/app.js`.
