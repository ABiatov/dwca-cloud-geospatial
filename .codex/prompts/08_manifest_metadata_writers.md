# Prompt 08: Manifest And Metadata Writers

## Required Skills

- `data-package-spec`: bundle layout, manifest, source metadata, processing metadata, provenance and counts.
- `geospatial-pipeline`: conversion result integration with output writers.
- `planning-artifact-curator`: session log and prompt maintenance.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- Prompts `01` through `07`
- Latest session logs for prompts `01` through `07`
- Current parser, normalization, quality, FlatGeobuf and GeoParquet writer APIs.
- Prompt 04 normalization API and count/rejection models:
  `normalize_occurrence_records`, `OccurrenceNormalizationResult`,
  `OccurrenceNormalizationCounts`, `NormalizedOccurrenceRecord` and
  `RejectedOccurrenceRecord`.
- Use Prompt 04 counts for `source_records`, `parsed_records`,
  `accepted_records` and `rejected_records`; use
  `RejectedOccurrenceRecord.to_dict()` or an equivalent explicit column
  mapping for `reports/rejected_records.csv`.
- When serializing accepted normalized records for metadata/projection helpers,
  preserve the Prompt 04 `class_` to output `class` mapping and avoid emitting
  source camelCase Darwin Core terms as normalized fields.
- Prompt 03 source-record handoff API for parser provenance context:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `OccurrenceReadResult` and `OccurrenceSourceRecord`.
- Post-Prompt-03 handoff clarification: EML content extraction was deferred
  deliberately and is not a blocker for Prompt 04 normalization. Prompt 08 is
  the first prompt expected to read the declared `ArchiveMetadata.metadata_file`
  contents for `metadata/source.json`.

## Goal

Generate the static output bundle metadata files: `manifest.json`, `metadata/source.json`, `metadata/processing.json`, and conditional `reports/rejected_records.csv`.

## Tasks

- Implement output directory layout exactly as documented.
- Reuse existing fixture roots from Prompt 01, including
  `tests/fixtures/output_bundles/` for sample bundle fixtures.
- Write `manifest.json` with schema versions, id, title, timestamps, generator, source summary, files inventory, layers, viewer defaults and counts.
- Write `metadata/source.json` from archive, DwC-A, EML, dataset, rights, GBIF and OBIS provenance when available.
- Implement the EML content extraction deferred from Prompt 02/03 by reading
  the declared `ArchiveMetadata.metadata_file` when present and safely
  available. Missing EML values must remain nullable source metadata fields.
- Write `metadata/processing.json` with effective configuration, field mapping, quality rules, counts, type conversion failures, warnings and validation summary placeholder.
- Write `reports/rejected_records.csv` only when at least one record is rejected or skipped.
- Omit files not generated from `manifest.files`.
- Include file size and checksum where practical.
- Add tests for FlatGeobuf-only default bundle and explicit GeoParquet bundle inventory.

## Constraints

- Missing GBIF/OBIS values must be null, not invented.
- `reports/rejected_records.csv` must be absent when no records are rejected.
- Do not implement full bundle validation here beyond local writer consistency checks; Prompt 09 owns validator behavior.

## Acceptance Criteria

- Generated bundle layout matches `docs/output_format.md`.
- Manifest file inventory reconciles with generated files.
- Counts reconcile across conversion result and metadata.
- Conditional rejected report behavior is tested.
- Viewer fields include only fields supported by the generated projection.

## Required Session Log

Write `session_logs/YYYY-MM-DD_08_manifest_metadata_writers.md` with:

- Metadata writer APIs.
- File inventory/count behavior.
- Any source metadata limitations.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `09` through `14` if manifest shape, metadata paths, count fields, report columns or writer APIs changed.
