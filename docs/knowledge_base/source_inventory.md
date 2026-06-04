---
id: source-inventory
status: reference
scope: examples-code
---

# Source Inventory

This file summarizes the local reference corpus under `examples/code/`. It explains what each source is useful for in this project and what should not be copied into the baseline design.

| Source | Local Path | Use For | Do Not Import Blindly |
| --- | --- | --- | --- |
| python-dwca-reader | `examples/code/python-dwca-reader/` | DwC-A reader concepts, archive structure, rows/star records, existing Python API shape. | Do not assume it should become a dependency. The project may prefer direct `meta.xml` parsing and streaming. |
| dwca-tools | `examples/code/dwca-tools/` | CLI layout, archive summarization, safe zip inspection, batch SQL loading, test/fixture ideas. | Its SQL database workflow and GBIF download commands are not baseline requirements here. |
| dwca-to-sql | `examples/code/dwca-to-sql/` | Older SQL conversion pattern and simple CLI examples. | PostgreSQL is explicitly outside the required runtime for this repository. |
| dwca2parquet | `examples/code/dwca2parquet/` | Strongest local reference for DwC-A to Parquet/GeoParquet: `meta.xml`, streaming batches, `_id`/`_coreid`, raw/interpreted modes, geometry, provenance metadata. | Treat its exact output layout and mode defaults as candidate patterns until accepted in project docs. |
| cloud-optimized-geospatial-formats-guide | `examples/code/cloud-optimized-geospatial-formats-guide/` | Conceptual map of cloud-optimized geospatial formats, FlatGeobuf, GeoParquet, PMTiles, partial reads, HTTP range requests. | It covers many formats outside this project; do not broaden scope to raster, Zarr, HDF5, or point clouds. |
| geoparquet | `examples/code/geoparquet/` | GeoParquet specification, metadata schema, CRS, geometry columns, validation fixtures. | Prefer stable released spec guidance when writing accepted docs; local dev spec content may be ahead of stable readers. |
| geoparquet.github.io | `examples/code/geoparquet.github.io/` | Public GeoParquet website structure and releases metadata. | Not an implementation reference for the converter. |
| geoparquet-io | `examples/code/geoparquet-io/` | CLI/API organization for GeoParquet conversion, validation, sorting, partitioning, PMTiles creation, DuckDB/PyArrow practices. | It is a broad geospatial tool, not a DwC-A converter. Avoid importing its cloud upload/service extraction scope by default. |
| GeoParquet writing cookbook | `examples/code/geomermaids-GeoParquet_Writing_cookbook.md` | Practical writer defaults: GeoParquet versions, ZSTD, bbox, row groups, spatial sorting, `gpio`, GDAL and DuckDB recipes. | Some version advice depends on toolchain freshness; confirm before locking accepted specs. |
| GeoParquet reading cookbook | `examples/code/geomermaids-GeoParquet_Reading_Cookbook.md` | Reader behavior, DuckDB/GDAL/GeoPandas examples, practical inspection. | Use as usage guidance, not as a normative specification. |

## Recommended Extraction Style

When mining `examples/code/`, extract:

- project-applicable patterns;
- assumptions and defaults;
- known limitations;
- validation commands;
- dependency and runtime implications;
- open questions for project decisions.

Avoid copying large chunks of external docs into this repository. Keep the knowledge base concise and link back to local source paths.

