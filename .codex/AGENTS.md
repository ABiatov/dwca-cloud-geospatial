# Project Agent Rules

## Project Identity

This repository is for **DwC-A to Cloud-Optimized Geospatial Formats**: a prototype toolchain for converting Darwin Core Archive biodiversity datasets into static, cloud-friendly geospatial outputs.

Canonical public description: `README.md`.

Primary project goal:
- read a Darwin Core Archive (DwC-A) dataset;
- extract occurrence records with usable coordinates;
- normalize Darwin Core fields into explicit project schemas;
- write cloud-friendly MVP outputs such as GeoParquet and FlatGeobuf;
- write metadata describing source files, processing parameters and generated outputs;
- provide a lightweight browser-based MapLibre viewer for static publishing and inspection.

This repository is an early standalone component of the Biodiversity Viewer Serverless roadmap, but its immediate scope is the DwC-A conversion prototype described above. Do not assume the broader Biodiversity Viewer Serverless package, GBIF acquisition, checklist matching or regional-demo workflow exists unless current repository files or the user explicitly introduce that scope.

## Core Architecture Rules

- Keep the baseline workflow file-based and reproducible: local input archive(s) in, static geospatial assets and metadata out.
- Do not introduce PostgreSQL/PostGIS, a permanent API service, object-store dependency, scheduler or cloud-specific infrastructure as a required runtime unless the user explicitly accepts that scope.
- Build-time tools may use local processing engines and temporary files when practical, but published outputs should remain portable files.
- Use open, inspectable formats: GeoParquet for analytical geospatial output, FlatGeobuf for lightweight geospatial exchange, JSON for metadata/catalog/configuration, and CSV where useful for diagnostics. PMTiles is an intended MVP+ output for tiled map visualization, not a primary MVP output.
- Treat APIs, file layouts and CLIs as experimental until the first tagged release.
- Preserve source lineage from generated records back to the source archive, source file, row identifier where available, and processing rule version.
- Keep AGPL-3.0 obligations in mind when making architecture and dependency choices.

## Current Repository Shape

- `README.md` -> canonical public project description and near-term roadmap.
- `LICENSE` -> AGPL-3.0 license.
- `.codex/` -> agent rules and local skills for this project.
- `examples/` -> code samples and DwC-A archives for prototype experiments.

Expected future directories, if/when implemented:
- `src/` or `packages/` -> converter and viewer implementation code, following the chosen stack.
- `configs/` -> reusable conversion, field-mapping, quality-rule and viewer configs.
- `docs/` -> architecture, output format, parser, viewer, deployment and demo documentation.
- `tests/` -> parser, conversion, schema and viewer-contract tests.
- `planning/` -> accepted internal planning notes and ADR-style decisions.
- `session_logs/` -> exploratory notes and handoff logs when useful.

Do not assume old directories such as `input_docs/`, region-specific demo folders, PostgreSQL schema docs, or GBIF-only pipeline folders exist in this repository.

## Canonical Source Rules

If documents conflict:
- prefer `README.md` for current product identity and roadmap until a more specific accepted document exists;
- prefer project-facing files in `docs/` for accepted architecture, output schema and viewer contracts once created;
- use `docs/knowledge_base/` as curated agent-facing reference material extracted from local examples, not as a replacement for accepted specs;
- keep exploratory notes in `session_logs/` or `planning/`;
- mark assumptions explicitly;
- do not spread contradictory decisions across multiple files.

Suggested canonical mapping:
- system boundaries -> `docs/architecture.md`;
- output bundle layout/schema -> `docs/output_format.md`;
- DwC-A parser and field mappings -> `docs/dwca_parser.md`;
- converter CLI/configuration -> `docs/converter.md`;
- static viewer contract -> `docs/viewer_contract.md`;
- deployment/static hosting -> `docs/deployment.md`;
- long-lived tradeoffs -> `planning/decisions/ADR-*.md`.

Knowledge base routing:
- start at `docs/knowledge_base/index.md` when using local examples as references;
- source inventory -> `docs/knowledge_base/source_inventory.md`;
- DwC-A parsing -> `docs/knowledge_base/topics/dwca_archive_parsing.md`;
- DwC-A to Parquet patterns -> `docs/knowledge_base/topics/dwca_to_parquet_patterns.md`;
- GeoParquet output -> `docs/knowledge_base/topics/geoparquet_output.md`;
- FlatGeobuf output -> `docs/knowledge_base/topics/flatgeobuf_output.md`;
- PMTiles/static viewer -> `docs/knowledge_base/topics/pmtiles_viewer.md`;
- validation and quality -> `docs/knowledge_base/topics/validation_and_quality.md`;
- CLI and pipeline shape -> `docs/knowledge_base/topics/cli_and_pipeline_patterns.md`.

## Skill Routing Rules

Use these local skills intentionally:

- `data-package-spec`: output bundle layout, metadata, schema versioning, GeoParquet/FlatGeobuf/PMTiles/JSON outputs, provenance and validation.
- `dwca-archive-parser`: Darwin Core Archive parsing, `meta.xml`, core/extension files, safe archive handling, Darwin Core field mapping, row validation and source metadata.
- `geospatial-pipeline`: local conversion pipeline from DwC-A records to cloud-optimized geospatial outputs, including coordinate normalization, quality flags, tiling and static-viewer-ready files.
- `static-viewer-contract`: MapLibre static viewer contract, manifest-driven loading, PMTiles/FlatGeobuf/GeoParquet data access, filters, tables, exports, accessibility and no-backend deployment constraints.
- `gbif-api-integration`: optional GBIF API/download integration only when the project explicitly adds fetching source archives from GBIF.
- `gbif-taxonomy-matching`: optional GBIF/checklist taxonomic matching only when the project explicitly adds taxonomy normalization or checklist enrichment.
- `planning-artifact-curator`: preserving accepted decisions, open questions, risks, demo evidence and next actions in project documents.

Do not route ordinary DwC-A parsing or file conversion work through GBIF-specific assumptions unless the source archive or requested feature is specifically GBIF-related.

## Implementation Rules

- Prefer the product direction in `README.md`: a simple, reproducible DwC-A conversion workflow plus a minimal static MapLibre viewer.
- Start with small validated sample archives from `examples/` before optimizing for very large datasets.
- Avoid hidden working-directory assumptions. Use explicit input/output paths and structured configuration.
- Parse DwC-A archives through `meta.xml` and declared field mappings where possible; avoid position-based column logic outside a schema object.
- Validate coordinates, CRS assumptions, row identifiers, date fields and required Darwin Core terms before writing final outputs.
- Preserve rejected or skipped records with reason codes when practical.
- Keep generated viewer-facing structures read-only and documented.
- Do not hard-code a single dataset, region, taxonomic checklist, language or status vocabulary into core logic.
- If GBIF integration is added later, keep it optional and preserve download keys, DOI/citation metadata, request JSON and dataset keys in metadata.

## Security And Reliability Rules

Apply security review to code that handles external archives, local paths, HTTP calls, config files, generated static files and optional deployment scripts.

Always check:
- no secrets committed or logged;
- bounded HTTP timeouts and retries for optional network integrations;
- safe archive extraction or streaming with path-traversal checks;
- validation of external payloads and config files;
- clear overwrite/destructive-operation guardrails;
- no hidden network calls in viewer code beyond declared static package files and map assets.

## Documentation Rules

For each accepted deliverable, keep documentation close to the artifact:
- output format -> `docs/output_format.md`;
- DwC-A parsing and field mappings -> `docs/dwca_parser.md`;
- converter usage/configuration -> `docs/converter.md`;
- viewer contract -> `docs/viewer_contract.md`;
- deployment/static hosting -> `docs/deployment.md`;
- ADRs -> `planning/decisions/`.

Separate accepted decisions from exploratory notes. Durable decisions should not remain only in chat.
