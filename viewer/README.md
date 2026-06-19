# Static Viewer

This directory contains the source copy of the minimal static MapLibre viewer
for generated DwC-A output bundles. `dwca-cloud-geospatial convert` copies
these files into each output bundle root.

The viewer reads `manifest.json`, `metadata/source.json` and
`metadata/processing.json` from a bundle root. If a declared FlatGeobuf point
layer is available, it loads `data/occurrences.fgb` in the browser. Declared
GeoPackage and GeoParquet files are shown as generated artifacts; they are not
loaded as MVP browser map layers.

## Local Launch

Create a bundle with the documented converter workflow, then serve a directory
that contains both `viewer/` and the bundle:

```bash
export REPO="/Users/Alevtina/Documents/GitHub/dwca-cloud-geospatial"
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
inventory, then shows the accepted no-FlatGeobuf map state.

The browser loads MapLibre GL JS and FlatGeobuf JavaScript from public CDN
URLs. The map uses the public OpenStreetMap raster tile endpoint as a basemap
with visible attribution. To run fully offline, mirror those assets, configure
an alternative basemap and update `viewer/index.html` / `viewer/app.js`.
