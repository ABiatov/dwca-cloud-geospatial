# Changelog

All notable changes to this project are documented here.

## v0.1.2 - 2026-07-14

Initial public prototype release of the DwC-A to cloud-optimized geospatial
conversion workflow.

### Added

- Darwin Core Archive inspection for local `.zip` archives and unpacked
  archive directories.
- Occurrence-core row reading driven by `meta.xml`, including safe zip path
  checks, row provenance and actionable diagnostics.
- Occurrence normalization into a stable project-owned schema with coordinate
  validation, quality flags, rejected-record reporting and selected
  Darwin Core, Dublin Core, GBIF, OBIS and IUCN field mappings.
- Core Python conversion API through
  `dwca_cloud_geospatial.conversion.convert_dwca_archive`.
- CLI commands for `inspect`, `convert` and `validate`.
- Tkinter GUI entry point through `dwca-cloud-geospatial-gui`.
- Default FlatGeobuf output at `data/occurrences.fgb`.
- Retained GeoPackage staging artifact at `data/occurrences.gpkg` whenever
  FlatGeobuf is generated.
- Explicit GeoParquet output at `data/occurrences.parquet`, including a
  large-output mode with chunked parser/normalizer/writer handoff, a `bbox`
  covering column and bounded grid spatial ordering.
- Static output bundle metadata:
  - `manifest.json`
  - `metadata/source.json`
  - `metadata/processing.json`
  - `reports/rejected_records.csv` when rows are rejected or skipped.
- Optional GBIF occurrence download DOI/citation provenance supplied manually
  or resolved through explicit conversion-time enrichment.
- Bundle validation API and CLI validation command with required checks and
  dependency-dependent optional checks.
- Lightweight static MapLibre viewer copied into generated output bundles.
- GeoParquet-only bundle support with a no-map-layer metadata/provenance state.
- Public project documentation covering project overview, converter usage,
  output format, parser behavior, viewer contract, developer setup and static
  deployment.
- Citation metadata in `CITATION.cff`.

### Verified

- Local test run on 2026-06-21: `97 passed, 1 skipped`.
- Verified workflow covers parser behavior, normalization, output writing,
  bundle metadata, validation, CLI behavior, GUI option handling and static
  viewer contract behavior.

### Known Limitations

- Geospatial conversion targets occurrence archives with declared coordinate
  terms.
- Checklist archives with `Taxon` cores can be inspected but are not converted
  to geospatial occurrence outputs in this release.
- Multi-file occurrence-core streaming is deferred.
- PMTiles generation is deferred.
- Browser GeoParquet loading is deferred; GeoParquet-only bundles show
  metadata, provenance and artifact inventory.
- Partitioned GeoParquet datasets are rejected until manifest and validator
  contracts support partition file inventories.
- FlatGeobuf generation stages through GeoPackage to avoid Python-side full
  accepted-record materialization, but GDAL may still need substantial memory
  while building the final indexed FlatGeobuf.
- The copied static viewer currently references public frontend CDN assets and
  an OpenStreetMap raster basemap.
