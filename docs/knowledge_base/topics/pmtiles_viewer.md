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

Accepted MVP override: the first static viewer should load `exports/occurrences.fgb`. PMTiles is an intended MVP+ viewer-optimized map output, not an MVP requirement.

The static MapLibre viewer should consume generated files and a manifest from static hosting without requiring a permanent backend.

## Viewer Contract Principles

- Load data from a manifest JSON rather than hard-coded filenames.
- Support static files only: FlatGeobuf for MVP, PMTiles for MVP+, GeoParquet metadata, diagnostics, and style/config JSON.
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

## Resolved By Accepted Docs

- PMTiles is deferred to MVP+. The first prototype should start with FlatGeobuf viewer loading: `planning/decisions/ADR-001-mvp-boundaries-and-interfaces.md` moves PMTiles to MVP+, and `docs/development_plan.md` excludes PMTiles generation from the MVP except as documented MVP+ work.
- The MVP static viewer should read `manifest.json`, metadata files and `exports/occurrences.fgb`, with browser-side filters over generated bundle fields. This is accepted in `docs/development_plan.md` M5 and `docs/output_format.md`.
- PMTiles generation is deferred to MVP+ and should use Tippecanoe as the preferred tiler when available. Tippecanoe remains an optional external dependency, not an MVP runtime requirement. The converter should fail gracefully with an actionable message when PMTiles generation is requested but `tippecanoe` is not installed.
- PMTiles point attributes should default to the same compact normalized occurrence field set as FlatGeobuf. A smaller PMTiles-specific attribute profile may be introduced later for large datasets if tile size or browser performance requires it.

## Open Questions

- None currently.
