# Generated DwC-A Geospatial Bundle

This directory is a generated output bundle from `dwca-cloud-geospatial`.

## Open The Viewer

Serve this directory, or any parent directory that contains it, with ordinary
static file hosting and open `index.html` in a browser.

For local review from the repository root:

```bash
python -m http.server 8000 --directory .
```

Then open the bundle-relative viewer URL, for example:

```text
http://localhost:8000/path/to/output-bundle/index.html
```

## Bundle Contents

- `manifest.json`: discovery document for tools and the static viewer.
- `metadata/source.json`: source archive, dataset, rights and provenance
  metadata.
- `metadata/processing.json`: converter configuration, counts, validation
  summary, warnings and parser diagnostics.
- `data/`: generated geospatial outputs such as FlatGeobuf, GeoPackage and
  GeoParquet when selected.
- `reports/`: rejected-record reports when source rows are rejected or skipped.
- `index.html`, `styles.css` and `app.js`: static viewer assets copied into
  the bundle.

The viewer does not require a project backend, database, scheduler or live
GBIF/OBIS API. Optional external frontend assets and basemap tiles depend on
the copied viewer configuration.

## Viewer Visibility Controls

`manifest.viewer.visibility` is optional presentation configuration. New
generated manifests contain the complete all-visible tree; omitted or partial
trees keep unspecified elements visible. Only the JSON boolean `false` at an
`is_visible` node hides the target.

The tree can control sidebar panels and their launcher buttons, Info blocks and
named provenance rows, filter groups, the named download artifacts, bottom
panel content/sections and point popups. Artifact keys are `occurrences.fgb`,
`occurrences.gpkg`, `occurrences.parquet`, `source.json` and
`processing.json`; they apply only to their standard bundle paths. Unlisted
inventory artifacts retain normal display.

`bottom-toggle-bar` is not a visibility key. Use `bottom-panels`,
`bottom-panels-content`, `feature_details` and `processing` for footer
presentation. Visibility changes only the viewer interface: it does not remove
inventory files or change data, counts, source metadata or processing
provenance.

## Citation And License

Dataset DOI, citation, license, rights holder and GBIF/OBIS provenance are
recorded in `metadata/source.json` and summarized in `manifest.json` when
available. Preserve those fields when publishing or redistributing this
generated bundle.
