---
id: add-static-viewer-output-playbook
status: candidate
applies_to:
  - PMTiles outputs
  - FlatGeobuf outputs
  - static viewer contract
  - deployment/static hosting
sources:
  - docs/knowledge_base/topics/pmtiles_viewer.md
  - docs/knowledge_base/topics/flatgeobuf_output.md
  - examples/code/cloud-optimized-geospatial-formats-guide/
---

# Add Static Viewer Output

## Goal

Generate static viewer-facing files from converted occurrence data without adding a backend service.

## Steps

1. Start from validated geospatial occurrence output.
2. Copy the static viewer source files into the output bundle root as
   `index.html`, `styles.css`, `app.js` and `README.md`; keep these viewer
   files out of `manifest.files`.
3. For MVP map display, use `data/occurrences.fgb` when a FlatGeobuf layer
   is generated. GeoParquet-only bundles are valid without FlatGeobuf; handle
   them with the accepted no-map-layer behavior from `docs/viewer_contract.md`
   unless GeoParquet browser loading is accepted later. PMTiles is MVP+ and
   should be added only when requested by accepted docs or user scope.
4. Generate bounds, center, layer metadata, and field list.
5. Write a manifest JSON that declares generated data, metadata and report
   paths.
6. Ensure paths are relative and static-host friendly.
7. Keep basemap or external asset URLs explicit in viewer config.
8. Use `has_quality_flags` when available for show/hide controls, and split
   nullable `quality_flags` on `|` for exact-token filtering.
9. Color points by `kingdom` where available and provide a high-contrast
   selected-feature highlight.
10. Add derived source-record links only from stable provenance fields, for
   example `https://www.gbif.org/occurrence/{source_record_id}`.
11. Add diagnostics for missing or skipped geometry.
12. Test the generated manifest with the static viewer loader.

## Acceptance Evidence

- Viewer can load from static files only.
- Manifest references existing files.
- Map layer bounds match generated data.
- Copied `index.html` opens the neighboring `manifest.json`.
- No permanent API, scheduler, database, or cloud-specific service is required.

## Related Topics

- `../topics/pmtiles_viewer.md`
- `../topics/flatgeobuf_output.md`
