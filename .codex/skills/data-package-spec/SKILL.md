---
name: data-package-spec
description: Designs and reviews the portable output bundle for DwC-A to cloud-optimized geospatial conversion, including layout, manifest JSON, schema versions, GeoParquet occurrence files, FlatGeobuf exports, PMTiles, provenance, validation, and static-hosting constraints.
---

# Skill: Data Package Spec

## Purpose

Design and review the file-based output bundle produced by this repository's DwC-A converter and consumed by analysts or the lightweight static MapLibre viewer.

## When to use

Use this skill when work involves:
- defining output directory layout;
- adding or changing manifest/catalog metadata;
- defining occurrence, geometry, quality, tile or provenance schemas;
- deciding GeoParquet, FlatGeobuf, PMTiles, JSON or CSV outputs;
- validating output completeness;
- planning schema versions and migrations.

## Instructions

### 1. Output principles

The output bundle must be:
- self-describing enough to inspect without hidden services;
- static-hostable as plain files;
- reproducible from a source archive, configuration and processing metadata;
- portable across DwC-A publishers and datasets;
- versioned so older outputs can be detected and handled.

Do not require a live database or API for published output use.

### 2. Suggested output contents

Use these as defaults unless an accepted spec says otherwise:

- `manifest.json` -> output ID, title, schema version, generated timestamp, source archive summary, file inventory, checksums, license and supported viewer contract.
- `metadata/source.json` -> source archive path/URL, archive checksum, source files, DwC-A metadata, EML summary when available, citations/rights and retrieval timestamp if relevant.
- `metadata/processing.json` -> converter version, config hash, field-mapping version, counts, warnings and validation results.
- `metadata/fields.json` -> Darwin Core source fields mapped into project fields, types, nullability and derived-field notes.
- `data/occurrences.parquet` or partitioned `data/occurrences/*.parquet` -> GeoParquet occurrence records.
- `exports/occurrences.fgb` -> optional FlatGeobuf export for simple geospatial exchange.
- `tiles/occurrences.pmtiles` -> optional PMTiles output for map visualization.
- `reports/rejected_records.csv` or Parquet -> skipped/rejected rows with reason codes and source context.

Keep raw/source evidence separate from normalized viewer-facing fields where that improves auditability.

### 3. Schema discipline

For each table/file define:
- stable field names;
- types and nullability;
- coordinate/CRS assumptions;
- whether a field is source, interpreted or project-derived;
- stable source identifiers where available;
- relation to source archive, source file and source row;
- schema version and compatibility notes.

Prefer explicit schema validation over implicit inference from the first file read.

### 4. Provenance requirements

Output metadata should allow a future maintainer to answer:
- which DwC-A archive and source files produced each output;
- which Darwin Core terms were mapped into each normalized field;
- which coordinate/date/quality rules included, excluded or flagged a record;
- which converter version, config and field-mapping version generated the output;
- which outputs were produced, with checksums and record counts.

For GBIF-sourced archives, preserve GBIF download key, DOI/citation, dataset keys and request metadata when available, but do not make GBIF metadata required for non-GBIF archives.

### 5. Validation

Output validation should check:
- required files exist;
- manifest file inventory matches actual files;
- schema versions are supported;
- referenced files and checksums are valid;
- GeoParquet geometry metadata is present;
- coordinates are in expected ranges and CRS is documented;
- row counts reconcile across parser, filters and outputs;
- required provenance links are not broken.

## Output expectations

When answering output-spec tasks, return:

1. Output files affected.
2. Schema or manifest changes.
3. Provenance fields.
4. Validation rules.
5. Static viewer compatibility impact.
6. Migration or backward-compatibility notes.

## Checklist

- Can the output be served as static files?
- Is it self-describing?
- Are GeoParquet/FlatGeobuf/PMTiles/JSON schema versions explicit?
- Are source archive and field mappings traceable?
- Can the static viewer discover required files from the manifest?
