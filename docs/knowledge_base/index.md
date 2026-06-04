---
id: knowledge-base-index
status: accepted
scope: agent-routing
---

# Knowledge Base Index

This directory turns local reference projects in `examples/code/` into concise, project-specific guidance for agents working on DwC-A to cloud-optimized geospatial conversion.

The raw examples remain reference material. These files are the agent-facing layer: read only the files relevant to the current task, then consult the raw sources when implementation details are needed.

## Source Of Truth

- `README.md` is the canonical public project description.
- `.codex/AGENTS.md` is the canonical agent rule file.
- `docs/knowledge_base/` is a curated reference layer, not a replacement for accepted architecture or output specs.
- Future accepted architecture and output contracts should live in `docs/architecture.md`, `docs/output_format.md`, `docs/dwca_parser.md`, `docs/converter.md`, and `docs/viewer_contract.md`.

## Routing

If working on DwC-A archive parsing, read:

- `topics/dwca_archive_parsing.md`
- `playbooks/implement_dwca_parser.md`

If converting DwC-A tables to Parquet or GeoParquet, read:

- `topics/dwca_to_parquet_patterns.md`
- `topics/geoparquet_output.md`
- `playbooks/implement_geoparquet_writer.md`

If designing the output bundle, read:

- `topics/geoparquet_output.md`
- `topics/flatgeobuf_output.md`
- `topics/pmtiles_viewer.md`
- `topics/validation_and_quality.md`
- `playbooks/validate_output_bundle.md`

If building a static viewer output, read:

- `topics/pmtiles_viewer.md`
- `topics/flatgeobuf_output.md`
- `playbooks/add_static_viewer_output.md`

If implementing a CLI or local pipeline, read:

- `topics/cli_and_pipeline_patterns.md`
- `topics/validation_and_quality.md`

If evaluating raw examples, start with:

- `source_inventory.md`

## Boundaries

The baseline project remains file-based and reproducible: local DwC-A archive in, static geospatial files and metadata out.

Do not introduce PostgreSQL/PostGIS, a permanent API, scheduler, object-store dependency, or cloud-specific runtime as a required component unless the user explicitly accepts that scope.

GBIF acquisition and taxonomy matching are optional future scopes. Do not assume they are part of the baseline converter.

