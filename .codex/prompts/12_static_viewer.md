# Prompt 12: Static Viewer

## Required Skills

- `static-viewer-contract`: implement the agreed static viewer behavior.
- `data-package-spec`: manifest and metadata consumption.
- `planning-artifact-curator`: session log and downstream prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/viewer_contract.md`
- `docs/converter.md` if it exists.
- Prompts `01` through `11`, including `10b`
- Latest session logs for prompts `01` through `11`, including `10b` when present
- Current sample output bundle generation path.
- Prompt 06 FlatGeobuf writer output contract: MVP bundles load
  `exports/occurrences.fgb`, with required fields from
  `FLATGEOBUF_PROJECTION_COLUMNS`, point geometry in longitude/latitude order,
  CRS assumption `OGC:CRS84`, nullable `quality_flags`, and
  `has_quality_flags`.
- Prompt 06 large-output behavior: generated FlatGeobuf files are indexed by
  default unless conversion explicitly used `SPATIAL_INDEX=NO`. If processing
  metadata exposes writer warning code `large_indexed_flatgeobuf_write`, the
  viewer should treat it as a non-fatal processing warning, not as a data-load
  error.
- Prompt 04 normalized occurrence field names and rejection/count structures,
  especially `quality_flags`, `has_quality_flags`, `source_records`,
  `accepted_records` and `rejected_records`.
- Prompt 05 quality flag semantics: split nullable `|`-delimited
  `quality_flags` strings and match exact tokens; use `has_quality_flags`
  when present for show/hide controls.
- Prompt 10b large-output handoff when present: if manifest or processing
  metadata declares partitioned GeoParquet, covering bbox, spatial sorting or
  large-output warnings, display or preserve those declarations consistently
  with `docs/viewer_contract.md`. The MVP map display may continue to use
  FlatGeobuf unless the viewer contract explicitly changes.

## Goal

Implement the minimal static MapLibre viewer for generated MVP bundles.

## Tasks

- Add static viewer files in the project location established by current docs or Prompt 11.
- Reuse existing `tests/fixtures/output_bundles/` fixtures for static viewer
  smoke inputs where practical.
- Load a generated bundle from `manifest.json`.
- Read `metadata/source.json` and `metadata/processing.json`.
- Display `exports/occurrences.fgb` as a point layer.
- Show dataset provenance fields when available.
- Show feature details for viewer-required fields.
- Implement browser-side filters for fields present in the bundle: text contains search for `scientific_name`, categorical filters, year filtering and show/hide records with `quality_flags`.
- Do not use substring matching for individual quality flag codes.
- Omit absent filter fields from the UI without error.
- Avoid live GBIF/OBIS API calls.
- Add static viewer smoke tests or browser checks where practical in the existing toolchain.

## Constraints

- Do not add a backend service.
- Do not require PMTiles.
- Keep the UI focused on actual inspection, not a landing page.
- If adding frontend dependencies, keep them justified and documented.

## Acceptance Criteria

- The viewer opens a generated sample bundle from static files.
- Missing optional metadata is handled gracefully.
- Missing filter fields are omitted without errors.
- No live GBIF or OBIS API access is required.
- Basic smoke verification is recorded.

## Required Session Log

Write `session_logs/YYYY-MM-DD_12_static_viewer.md` with:

- Viewer file locations.
- Data loading and filter behavior.
- Manual or automated smoke evidence.
- Known browser/static-hosting limitations.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent when Python tests are run.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `13` and `14` if viewer launch instructions, file paths, bundle assumptions, frontend commands or verification steps changed.
