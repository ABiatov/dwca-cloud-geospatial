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
2. Choose viewer artifact: PMTiles, FlatGeobuf, or both.
3. Generate bounds, center, layer metadata, and field list.
4. Write a manifest JSON that declares all viewer-facing paths.
5. Ensure paths are relative and static-host friendly.
6. Keep basemap or external asset URLs explicit in viewer config.
7. Add diagnostics for missing or skipped geometry.
8. Test the generated manifest with the static viewer loader.

## Acceptance Evidence

- Viewer can load from static files only.
- Manifest references existing files.
- Map layer bounds match generated data.
- No permanent API, scheduler, database, or cloud-specific service is required.

## Related Topics

- `../topics/pmtiles_viewer.md`
- `../topics/flatgeobuf_output.md`

