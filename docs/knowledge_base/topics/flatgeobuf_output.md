---
id: flatgeobuf-output
status: candidate
applies_to:
  - geospatial conversion
  - FlatGeobuf outputs
  - static viewer contract
sources:
  - examples/code/cloud-optimized-geospatial-formats-guide/flatgeobuf/
  - examples/code/cloud-optimized-geospatial-formats-guide/overview.qmd
---

# FlatGeobuf Output

## Use In This Project

FlatGeobuf is a candidate lightweight vector exchange and browser-accessible geospatial output. It is more viewer-friendly than analytical Parquet for some clients because it is streamable and supports HTTP range request access patterns.

## Fit

Use FlatGeobuf when the project needs:

- a single vector file that can be loaded by GIS tools;
- static-hosted vector access without a database;
- spatial index support for remote partial reads;
- a simpler web-viewer data source than raw GeoParquet.

## Tradeoffs

- FlatGeobuf is row-oriented and streamable.
- It is not compressed in the same way as Parquet because random reads are part of the design.
- It complements GeoParquet rather than replacing it.
- It is likely a better exchange/viewer artifact than a primary analytical artifact.

## Candidate Output Role

In an output bundle:

- GeoParquet can be the analytical table.
- FlatGeobuf can be an optional exchange or viewer data layer.
- PMTiles can be the optimized map tile layer for larger browser maps.

## Open Questions

- Whether FlatGeobuf is a required output or optional export.
- Whether FlatGeobuf should include all valid occurrence points or only viewer-filtered fields.
- Whether rejected/null-geometry rows should be represented separately in diagnostics only.

