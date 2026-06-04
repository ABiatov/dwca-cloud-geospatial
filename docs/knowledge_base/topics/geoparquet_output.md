---
id: geoparquet-output
status: candidate
applies_to:
  - geospatial conversion
  - GeoParquet outputs
  - metadata/provenance
  - validation
sources:
  - examples/code/geoparquet/README.md
  - examples/code/geoparquet/format-specs/geoparquet.md
  - examples/code/geomermaids-GeoParquet_Writing_cookbook.md
  - examples/code/geoparquet-io/README.md
  - examples/code/dwca2parquet/REFERENCE.md
---

# GeoParquet Output

## Use In This Project

GeoParquet is the primary analytical geospatial output for occurrence records with usable coordinates. It should remain a normal Parquet table with explicit geospatial metadata, suitable for DuckDB, GeoPandas, QGIS, GDAL, and other readers.

## Geometry Rules

- Build point geometry only from parseable `decimalLongitude` and `decimalLatitude`.
- Store coordinates in longitude, latitude order.
- Preserve original coordinate columns alongside geometry.
- Use null geometry or rejected-row reporting for missing or invalid coordinates, according to the accepted output policy.
- Geometry should be limited to the occurrence/core table unless an accepted extension-specific geometry use case exists.

## CRS

Darwin Core coordinates are normally WGS84 longitude/latitude. For GeoParquet metadata, prefer explicit CRS information. Be careful about axis order:

- WKB coordinate order is x, y, meaning longitude, latitude.
- OGC:CRS84 is longitude-latitude.
- EPSG:4326 is often used in tools, but its formal axis order can be latitude-longitude. Avoid ambiguity in accepted specs.

## Version Guidance

Candidate publishing default:

- GeoParquet 1.1 is the safest broad-compatibility default today.
- GeoParquet 2.0 may be useful when the project controls downstream readers and toolchain support is mature.
- GeoParquet 1.0 should generally be avoided for new published outputs because it lacks newer metadata and optimization features.

Confirm current reader support before making a long-lived decision.

## Optimization Practices

Useful practices from GeoParquet tooling and cookbooks:

- ZSTD compression for cloud or network-bound reads.
- Reasonable row group sizes for query pruning.
- Spatial sorting, such as Hilbert ordering or bbox ordering, before writing large files.
- Bbox metadata or bbox columns when supported by the chosen GeoParquet version and writer.
- Attribute partitioning only when it matches common query filters and does not overcomplicate the static output bundle.

## Validation

GeoParquet outputs should be validated with a spec-aware tool when possible:

- `gpq validate`
- GDAL/OGR GeoParquet validation tools
- `geoparquet-io` inspection/check commands, if adopted as a dev dependency or external tool

Validation should check both metadata and actual data where possible.

## Open Questions

- Whether baseline output should write GeoParquet 1.1 only, or support configurable 1.1 and 2.0.
- Whether a separate bbox column is required in the project schema or left to writer/tool defaults.
- Whether spatial sorting is mandatory for all outputs or only for larger datasets.

