---
name: static-viewer-contract
description: Designs and reviews the lightweight static MapLibre viewer contract for DwC-A geospatial outputs, including manifest-driven loading, PMTiles/FlatGeobuf/GeoParquet access, map layers, filters, exports, accessibility, and no-backend deployment constraints.
---

# Skill: Static Viewer Contract

## Purpose

Design and review how the browser-based MapLibre viewer reads generated geospatial outputs without a required backend.

## When to use

Use this skill when work involves:
- defining viewer-readable manifests;
- displaying PMTiles, FlatGeobuf, GeoJSON or derived map layers with MapLibre GL JS;
- deciding whether and how to query GeoParquet/Parquet in the browser;
- designing filters, tables, exports or summary indicators;
- checking static hosting constraints;
- validating loading, empty and error states.

## Instructions

### 1. Preserve no-backend operation

The viewer must be able to run from static hosting plus generated output files. Do not require a server API for basic package loading, mapping, filtering or metadata inspection.

If a future optional API is proposed, keep it outside the baseline viewer contract and document graceful fallback behavior.

### 2. Manifest-driven loading

Viewer startup should read `manifest.json` or an accepted equivalent and discover:
- output schema version;
- supported viewer contract version;
- file inventory and URLs;
- map defaults, bounds and coordinate assumptions;
- available layers such as PMTiles, FlatGeobuf, GeoJSON summaries or GeoParquet;
- occurrence fields available for popups, filters and tables;
- file sizes/checksums where useful.

Avoid hard-coding demo-specific files or labels into viewer logic.

### 3. Browser data strategy

Prefer:
- PMTiles for fast tiled map visualization when tiles are generated;
- FlatGeobuf or GeoJSON for small/simple map overlays;
- GeoParquet as the analytical output and optional browser-query source;
- DuckDB-WASM only when in-browser Parquet querying materially improves filtering, aggregation or export workflows;
- precomputed summaries only where they materially improve browser performance.

Design field names and types so filters can be expressed over stable output schemas.

### 4. Core viewer workflows

Default viewer capabilities should include:
- load output metadata;
- display occurrence points or tiles on a map;
- show source archive and processing summary;
- filter by available occurrence fields such as taxon/name, date, dataset/source and quality flags;
- show selected-record details;
- expose table and CSV export when source records are available in a browser-readable form;
- show clear loading, empty, error and unsupported-version states.

### 5. UX and accessibility

Keep the first screen as a usable viewer, not a marketing page. Prioritize compact, scannable controls for dataset inspection.

Ensure:
- keyboard-accessible controls;
- map interactions do not hide source/provenance context;
- long scientific names and source labels fit common control widths;
- exports include enough metadata for citation or source tracing;
- large datasets degrade gracefully when only tiled visualization is practical.

### 6. Output expectations

When answering viewer-contract tasks, return:

1. Manifest fields needed.
2. Output files/tables consumed.
3. Query/filter/export behavior.
4. Map and table data requirements.
5. Accessibility implications.
6. Static deployment risks.

## Checklist

- Can the viewer load outputs without a backend?
- Are files discovered from the manifest?
- Are map layers backed by declared PMTiles/FlatGeobuf/GeoParquet files?
- Are filters backed by stable fields?
- Are loading and unsupported-output states defined?
