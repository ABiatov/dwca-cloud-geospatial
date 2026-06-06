---
name: geospatial-pipeline
description: Designs and improves the local DwC-A-to-geospatial conversion pipeline, including Darwin Core occurrence normalization, coordinate filtering, quality flags, GeoParquet, FlatGeobuf, PMTiles, metadata, and static-viewer-ready files.
---

# Skill: Geospatial Pipeline

## Purpose

Design and review the processing workflow that turns Darwin Core Archive occurrence records into cloud-optimized geospatial files and a lightweight static viewer output.

## When to use

Use this skill when work involves:
- defining converter pipeline stages;
- extracting occurrence records from DwC-A parser output;
- normalizing coordinates, dates, taxa and quality flags;
- writing GeoParquet, FlatGeobuf, PMTiles or metadata outputs;
- preparing files for static publication or MapLibre inspection;
- deciding whether local processing should use Python, DuckDB, GeoPandas, pyogrio, GDAL, Tippecanoe, pmtiles tooling or other bounded tools.

## Instructions

### 1. Preserve the file-based boundary

Published outputs must be portable static files. Local build-time tools may use temporary caches or local analytical engines, but do not make PostgreSQL/PostGIS, a web API, cloud services or scheduled infrastructure mandatory unless explicitly accepted.

Prefer designs where the generated files can be served from static hosting, object storage, a local HTTP server or a small VPS as plain files.

### 2. Define pipeline stages

Default stage order:

1. Load and validate converter configuration.
2. Open DwC-A safely and parse `meta.xml`.
3. Locate occurrence core or occurrence extension records.
4. Map Darwin Core fields into project-owned fields.
5. Normalize coordinates, dates, names and source identifiers.
6. Validate required values and record rejected/skipped rows with reason codes.
7. Create geometries in a documented CRS, normally WGS84 longitude/latitude.
8. Apply optional spatial, date or quality filters.
9. Write GeoParquet occurrence output with geometry metadata.
10. Write optional FlatGeobuf export.
11. Write optional PMTiles for map visualization.
12. Write manifest, source metadata, processing metadata and reports.
13. Validate output structure, schema versions and viewer contract.

### 3. Treat outputs as contracts

Design outputs for both analysis and static viewer use:
- GeoParquet for occurrence records with geometry;
- FlatGeobuf for geospatial exchange or direct map loading;
- PMTiles for tiled visualization;
- JSON manifest, source/provenance metadata and processing summaries;
- CSV/Parquet reports for rejected records, warnings and quality summaries;
- stable schema versions and migration notes when fields change.

Avoid viewer logic that depends on raw DwC-A archive internals. Normalize to project-owned fields and keep raw/source evidence separately when useful.

### 4. Spatial and quality strategy

For spatial processing:
- validate latitude/longitude parseability and numeric ranges;
- preserve original Darwin Core coordinate fields when useful;
- track coordinate uncertainty, geodetic datum assumptions and coordinate-related issues;
- document how null, zero, swapped or out-of-range coordinates are handled.

For quality filtering:
- make rules configurable and versioned;
- record rejected or excluded records with reason codes;
- preserve enough source context to audit decisions;
- separate "not loaded", "loaded but flagged", and "viewer-hidden by default" behaviors.

### 5. Optional aggregates and tiles

Aggregates and PMTiles are output features, not mandatory infrastructure. Add them when they serve a viewer or analysis requirement.

Possible outputs:
- per-taxon counts;
- year/month summaries;
- source dataset summaries;
- quality-flag summaries;
- PMTiles point tiles or clustered/grid-derived tiles;
- small GeoJSON summaries for quick viewer startup.

### 6. Output expectations

When answering pipeline tasks, return:

1. Proposed stages and data ownership.
2. Required inputs and configuration.
3. Darwin Core field mapping flow.
4. Spatial filtering and quality strategy.
5. Output files to produce.
6. Provenance and validation fields.
7. Performance risks and test/demo evidence.

## Checklist

- Is the output still publishable as static files?
- Are source archive and normalized fields separated where needed?
- Are coordinates and rejected records explainable?
- Are output schema versions and provenance written?
- Can the static viewer read the outputs without a backend?
