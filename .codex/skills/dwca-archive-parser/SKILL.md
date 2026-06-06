---
name: dwca-archive-parser
description: Guides safe parsing of Darwin Core Archive datasets for DwC-A to geospatial conversion, including meta.xml, core and extension files, Darwin Core fields, source metadata, streaming/chunked parsing, validation, and mapping into GeoParquet/FlatGeobuf/PMTiles-ready outputs.
---

# Skill: DwC-A Archive Parser

## Purpose

Design and review Darwin Core Archive parsing for this repository's file-based geospatial converter. Parsing must be safe, bounded in memory, auditable and independent of a permanent database backend.

## When to use

Use this skill when work involves:
- reading `.zip` or unpacked Darwin Core Archive datasets;
- interpreting `meta.xml`, EML metadata, core files and extension files;
- mapping Darwin Core terms into project schemas;
- streaming/chunking occurrence rows;
- validating coordinates, dates, identifiers or taxonomy fields;
- using sample archives under `examples/`.

## Instructions

### 1. Start from Darwin Core Archive structure

Use `meta.xml` as the source of truth for:
- core and extension file locations;
- field delimiters, quote characters, encoding and header settings;
- row type and Darwin Core term mapping;
- ID fields and relationships between core and extensions.

Prefer standards-aware parsing over ad hoc assumptions about filenames or column positions.

Useful references to check when contracts matter:
- Darwin Core standard and terms from TDWG;
- DwC-A documentation from GBIF/TDWG;
- GBIF download format docs when the archive came from GBIF.

### 2. Locate occurrence records intentionally

Occurrence data may appear as:
- an Occurrence core;
- an Occurrence extension attached to another core;
- a GBIF download table with interpreted occurrence fields.

Record which pattern was used. If the archive has no occurrence records with usable coordinates, fail with a clear validation error rather than writing misleading empty geospatial outputs.

### 3. Safe archive and file handling

Parser implementation must:
- stream compressed archives/files where practical;
- reject path traversal entries in zip archives;
- honor declared delimiter, quote, escape, encoding, header and null-value settings;
- handle missing optional files without crashing the whole build;
- avoid loading whole archives into memory;
- calculate checksums for source files when feasible;
- preserve enough file/line context for rejected rows.

Do not extract archive entries blindly into user-controlled paths.

### 4. Required source metadata

For every parsed archive preserve:
- source archive path or URL;
- archive checksum and size when available;
- DwC-A metadata, including EML title/citation/rights when available;
- core/extension file inventory;
- parser version and field-mapping version;
- row counts by file and by parser stage.

For occurrence rows preserve available source fields such as:
- occurrence ID, catalog number or source row identifier;
- dataset/source identifiers where present;
- basis of record;
- scientific name and taxonomic fields;
- decimal latitude/longitude and coordinate uncertainty;
- event date/year/month/day;
- occurrence status;
- rights/license/publisher where present;
- source file and row number.

For GBIF-sourced archives, additionally preserve `gbifID`, `datasetKey`, download key, DOI/citation and issue flags when available.

### 5. Darwin Core mapping discipline

Define mappings as structured configuration or centralized schema code, not scattered ad hoc column names.

For each mapped field specify:
- Darwin Core source term;
- output table/file and target field;
- type conversion;
- nullability and default behavior;
- validation rule;
- whether the field is raw, interpreted or project-derived.

Keep raw/source evidence available separately from normalized viewer-facing fields when useful.

### 6. Validation before output write

Validate:
- required identifiers or fallback source-row identifiers;
- coordinate parseability and allowed ranges;
- date/year/month/day normalization;
- vocabulary fields used by downstream filters;
- duplicate occurrence identifiers and chosen behavior;
- row count reconciliation between source files, accepted records and rejected records.

Rejected rows need reason codes and source context. Ambiguous records should remain available as flagged records where policy allows.

### 7. Output expectations

When answering parser/import tasks, return:

1. Archive structure used.
2. Files/terms consumed.
3. Darwin Core field to output-field mapping.
4. Streaming/chunking strategy.
5. Source metadata persistence.
6. Validation/rejection rules.
7. Output files affected.

## Checklist

- Is `meta.xml` used instead of filename/position guesses?
- Are source metadata and citations preserved where available?
- Is the field mapping explicit and versioned?
- Does parsing avoid unsafe extraction and unbounded memory use?
- Are rejected rows explainable and counted?
