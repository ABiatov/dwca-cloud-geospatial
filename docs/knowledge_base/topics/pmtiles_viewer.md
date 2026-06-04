---
id: pmtiles-viewer
status: candidate
applies_to:
  - PMTiles outputs
  - static viewer contract
  - deployment/static hosting
sources:
  - examples/code/cloud-optimized-geospatial-formats-guide/pmtiles/
  - examples/code/cloud-optimized-geospatial-formats-guide/overview.qmd
  - examples/code/geoparquet-io/README.md
---

# PMTiles And Static Viewer

## Use In This Project

PMTiles is the likely viewer-optimized map output. The static MapLibre viewer should consume generated files and a manifest from static hosting without requiring a permanent backend.

## Viewer Contract Principles

- Load data from a manifest JSON rather than hard-coded filenames.
- Support static files only: PMTiles, FlatGeobuf, GeoParquet metadata, diagnostics, and style/config JSON.
- Avoid hidden network calls except declared basemap or static package assets.
- Keep the viewer read-only.
- Make generated viewer-facing structures documented and stable enough for static publishing.

## PMTiles Role

Use PMTiles for:

- fast browser map visualization;
- tiled point rendering at multiple zoom levels;
- static deployment on object storage, GitHub Pages, Netlify, or similar static hosts.

Do not treat PMTiles as the primary analytical store. It is derived from canonical converted records.

## Candidate Viewer Manifest Fields

Likely manifest sections:

- dataset identity and citation;
- source archive metadata;
- output file paths and media types;
- bounds and center;
- layer definitions;
- field list for popups/tables;
- quality flags and skipped-record summaries;
- generation tool version and schema version.

## Open Questions

- Which tiler/tool should generate PMTiles from point GeoParquet or FlatGeobuf.
- Whether the first prototype should include PMTiles immediately or start with FlatGeobuf/GeoJSON-like viewer loading.
- Which occurrence fields are included in tile attributes versus sidecar metadata.

