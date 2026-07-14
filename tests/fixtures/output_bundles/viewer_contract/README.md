# Viewer Contract Fixtures

These hand-authored JSON snippets exercise manifest semantics for the static
viewer contract. They are not complete output bundles and do not contain real
geospatial files.

- `flatgeobuf_with_geopackage_manifest.json` represents a generated-style
  FlatGeobuf bundle with the complete all-visible `viewer.visibility` tree.
- `selective_visibility_manifest.json` represents a complete tree with a
  selected provenance row, GeoPackage artifact and point popup hidden.
- `geoparquet_only_manifest.json` intentionally omits `viewer.visibility` to
  preserve the backward-compatibility case.
