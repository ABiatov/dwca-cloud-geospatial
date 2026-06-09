# MVP Development Prompt Flow

Status: Active prompt sequence for MVP implementation

Purpose: this directory contains ordered prompts for building the DwC-A to cloud-optimized geospatial MVP. Each prompt is intended to be run as a separate implementation session. Prompts are numbered because later prompts must explicitly read the artifacts produced by earlier prompts.

## Operating Rules For Every Prompt

- Start by reading `README.md`, `.codex/AGENTS.md`, `docs/development_plan.md`, `docs/output_format.md`, the previous prompt files, and the latest relevant `session_logs/*.md`.
- Use the skills named in the prompt. If a skill file is unavailable, record that in the session log and continue with the best local fallback.
- Keep the MVP file-based: local DwC-A archive in, static output bundle out. Do not add required databases, permanent APIs, schedulers, cloud runtimes, live GBIF/OBIS downloads, taxonomy matching, PMTiles, or packaged desktop binaries unless a later accepted decision changes scope.
- Preserve provenance from source archive rows through parser, normalization, outputs, metadata, CLI, GUI and viewer.
- For Python development and verification, prefer the in-repository `.venv/` documented in `docs/developer_setup.md`; do not install project development dependencies into Conda `base` or the system Python unless intentionally using a separate disposable environment.
- After implementation, run the narrowest useful verification commands available in the repository.
- Write a session log under `session_logs/` at the end of every prompt. Include decisions, files changed, verification evidence, open questions, and required follow-up edits.
- If implementation creates, renames, removes, or materially changes artifacts expected by later prompts, update the later `.codex/prompts/*.md` files in the same session so the flow remains accurate.
- If a prompt cannot complete its acceptance criteria, record the blocker in the session log and update the next prompt with the exact recovery task.

## Prompt Sequence

1. `01_project_skeleton.md`: create package, CLI stub, tests and fixture layout.
2. `02_dwca_inspection.md`: implement safe DwC-A archive inspection and `meta.xml` parsing.
3. `03_occurrence_parser.md`: stream or chunk occurrence core rows into structured source records.
4. `04_occurrence_normalization.md`: map source records into normalized occurrence and rejection models.
5. `05_quality_rules.md`: implement quality flags, conversion failure accounting and rejected-record behavior.
6. `06_flatgeobuf_writer.md`: write the default `exports/occurrences.fgb` projection.
7. `07_geoparquet_writer.md`: write explicit GeoParquet output with GeoParquet metadata.
8. `08_manifest_metadata_writers.md`: write manifest, source metadata and processing metadata.
9. `09_bundle_validation.md`: validate output bundles and reconcile counts/files/schema.
10. `10_core_api_cli.md`: expose conversion, inspection and validation through a thin core API and `argparse` CLI.
11. `11_viewer_contract.md`: document the static viewer contract.
12. `12_static_viewer.md`: implement the minimal static MapLibre viewer.
13. `13_tkinter_gui.md`: implement the primitive desktop GUI over the same core API.
14. `14_demo_docs_hardening.md`: complete docs, demos, regression tests and MVP limitations.

## Artifact Handoff Map

| Prompt | Produces | Later prompts must read |
| --- | --- | --- |
| 01 | Package layout, CLI stub, test harness, fixture conventions | 02-14 |
| 02 | Archive inspection API, `meta.xml` model, parser docs draft | 03, 10, 14 |
| 03 | Occurrence row reader and source-record model | 04-10, 14 |
| 04 | Normalized occurrence/rejection dataclasses or schemas | 05-10, 12-14 |
| 05 | Quality flags, reason codes, conversion failure metadata | 06-10, 12, 14 |
| 06 | FlatGeobuf writer and projection tests | 08-12, 14 |
| 07 | GeoParquet writer and projection tests | 08-10, 14 |
| 08 | Output bundle metadata writers | 09-14 |
| 09 | Bundle validator | 10, 14 |
| 10 | Public core API and CLI docs draft | 11-14 |
| 11 | Viewer contract document | 12, 14 |
| 12 | Static viewer files and smoke checks | 13-14 |
| 13 | GUI entry point | 14 |
| 14 | Final MVP documentation and evidence | Future MVP+ prompts |

## Prompt Maintenance Protocol

At the end of each prompt:

1. Add or update `session_logs/YYYY-MM-DD_<prompt-number>_<short-name>.md`.
2. Review all later prompt files for references to paths, commands, APIs, schemas, or acceptance criteria changed in this session.
3. Patch later prompts immediately when the next session would otherwise receive stale instructions.
4. Update the canonical `## Current next work item` pointer in this file to exactly one next prompt, or to `None` only when the active sequence is complete.
5. In the session log, include a section named `Prompt Updates` listing which later prompt files were changed and whether `.codex/prompts/dev_flow_description.md` was updated, or stating `None`.
6. If a durable architecture or output-format decision changed, update the canonical project document first, then update prompts to match the canonical document.

## Current next work item

`07_geoparquet_writer.md`
