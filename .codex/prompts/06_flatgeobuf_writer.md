# Prompt 06: FlatGeobuf Writer

## Required Skills

- `geospatial-pipeline`: point geometry conversion and static-viewer-ready fields.
- `data-package-spec`: FlatGeobuf projection, file layout and validation implications.
- `planning-artifact-curator`: session log and downstream prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- Prompts `01` through `05`
- Latest session logs for prompts `01` through `05`
- Current normalized occurrence and quality-rule implementation, including
  `NormalizedOccurrenceRecord`, `RejectedOccurrenceRecord`,
  `OccurrenceNormalizationResult`, `OccurrenceNormalizationCounts`,
  `TypeConversionFailure`, `OccurrenceNormalizationWarning` and
  `normalize_occurrence_records`.
- Prompt 05 stores accepted-record `quality_flags` as nullable
  `|`-delimited exact tokens, adds `has_quality_flags`, and counts optional
  and critical conversion failures in `OccurrenceNormalizationResult`.
- Use `NormalizedOccurrenceRecord.to_dict()` or an equivalent explicit
  projection when writing output fields so the Python attribute `class_`
  becomes the normalized output column `class`, and no source camelCase terms
  are exposed.
- Prompt 03 source-record handoff API for provenance context:
  `dwca_cloud_geospatial.occurrence.read_occurrence_rows`,
  `OccurrenceReadResult` and `OccurrenceSourceRecord`.

## Goal

Write accepted occurrence records to the MVP default FlatGeobuf export at `data/occurrences.fgb`.

## Tasks

- Implement an isolated FlatGeobuf writer using Pyogrio/GDAL where available.
- Reuse existing fixture roots from Prompt 01, including
  `tests/fixtures/output_bundles/` for bundle/output fixtures when needed.
- Write point geometry in longitude/latitude order with CRS assumption `OGC:CRS84`.
- Use the compact normalized projection required by `docs/output_format.md`.
- Include viewer display/filter fields when present.
- Include stable source identifiers and coordinates.
- Store `quality_flags` using the same nullable `|`-delimited string
  representation and include `has_quality_flags` where the projection requires
  it.
- Enable FlatGeobuf spatial index by default.
- Add a large-output guardrail/warning before indexed writes that may require substantial memory.
- Add tests that verify required columns, record count, geometry behavior and absent rejected records from the export.
- If Pyogrio/GDAL is unavailable in the local environment, isolate the dependency and add tests that can still run without writing real FlatGeobuf where practical.

## Constraints

- Do not use GeoPandas as the production writer path.
- Do not write GeoParquet in this prompt.
- Do not implement manifest or metadata writers except minimal scaffolding needed by tests.

## Acceptance Criteria

- `data/occurrences.fgb` can be produced for sample accepted records when dependencies are available.
- Required FlatGeobuf projection columns are present.
- Spatial index is requested by default.
- Large dataset warning behavior is testable.
- Tests either validate a real FGB file or cleanly skip dependency-specific checks with an explicit reason.

## Required Session Log

Write `session_logs/YYYY-MM-DD_06_flatgeobuf_writer.md` with:

- Writer stack and dependency behavior.
- Projection fields implemented.
- Large dataset guardrail behavior.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `08` through `12` and `14` if FlatGeobuf paths, projection fields, dependency handling, warning structures or writer APIs changed.
