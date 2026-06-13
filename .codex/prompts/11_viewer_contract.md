# Prompt 11: Viewer Contract

## Required Skills

- `static-viewer-contract`: manifest-driven MapLibre viewer inputs, filters, static hosting and no-backend constraints.
- `data-package-spec`: consistency with manifest, metadata and FlatGeobuf output contract.
- `planning-artifact-curator`: record accepted viewer decisions and update downstream prompts.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/converter.md` if it exists.
- Prompts `01` through `10`, plus `10b`
- Latest session logs for prompts `01` through `10`, plus `10b` when present
- Current generated bundle examples/tests.
- Prompt 08 generated metadata contract: bundle metadata is written by
  `dwca_cloud_geospatial.bundle.write_bundle_metadata` to `manifest.json`,
  `metadata/source.json`, `metadata/processing.json`, and conditional
  `reports/rejected_records.csv`. `manifest.files` only lists generated files
  and includes file size and SHA-256 checksums where present.
- Prompt 08 viewer defaults: `manifest.viewer.display_fields` and
  `manifest.viewer.filter_fields` are intersected with the selected generated
  projection columns, so the viewer should trust absent fields as intentionally
  omitted rather than treating them as errors.
- Prompt 08 processing warnings include FlatGeobuf writer warning
  `large_indexed_flatgeobuf_write` with `stage="flatgeobuf_writer"`,
  `feature_count` and `estimated_spatial_index_bytes`.
- Prompt 06 FlatGeobuf output path and projection:
  `exports/occurrences.fgb` from `DEFAULT_FLATGEOBUF_RELATIVE_PATH`, required
  columns from `FLATGEOBUF_PROJECTION_COLUMNS`, point geometry in
  longitude/latitude order, CRS assumption `OGC:CRS84`, and default indexed
  writes with dependency-specific validation when Pyogrio/PyArrow/GDAL are
  available.
- Prompt 06/08 large-output behavior: FlatGeobuf spatial indexing is requested
  by default and large indexed writes produce metadata-worthy warnings rather
  than automatically disabling the index. Prompt 08 exposes those warnings in
  `metadata/processing.json`.
- Prompt 04 normalized field model for accepted/rejected occurrence records,
  especially `NormalizedOccurrenceRecord.to_dict()` exporting the Python
  `class_` attribute as output field `class`.
- Prompt 05 quality flag contract: `quality_flags` is nullable
  `|`-delimited text, no flags are null, `has_quality_flags` is boolean, and
  viewers must split on `|` for exact-token matching instead of substring
  matching.
- Prompt 10b large-output handoff when present: preserve any implemented
  large-archive metadata fields, partitioned GeoParquet declarations and
  large-output warnings in the viewer contract. The MVP static viewer may
  still prefer FlatGeobuf for map display, but it should not contradict the
  accepted large-output GeoParquet metadata contract.

## Goal

Create `docs/viewer_contract.md` as the accepted contract for the minimal static viewer.

## Tasks

- Define how the viewer discovers data through `manifest.json`.
- Define required and optional metadata files read by the viewer.
- Define FlatGeobuf point layer loading behavior.
- Define dataset provenance panel fields.
- Define feature details panel fields.
- Define MVP filters: `scientific_name`, `kingdom`, `event_year`, `basis_of_record`, `iucn_red_list_category`, `quality_flags`.
- Define `quality_flags` filter semantics using exact tokens and
  `has_quality_flags` where available.
- Specify behavior when optional fields or metadata are absent.
- Specify no-backend/static-hosting constraints.
- Specify no live GBIF/OBIS API dependency.
- Add any needed viewer-specific acceptance tests or contract fixtures under
  the existing `tests/fixtures/` roots if the project pattern supports them.

## Constraints

- Do not implement the viewer UI in this prompt unless tiny fixtures are needed to prove the contract.
- Do not require PMTiles.
- Do not change output bundle shape without updating `docs/output_format.md` first.

## Acceptance Criteria

- `docs/viewer_contract.md` exists and is consistent with `docs/output_format.md`.
- Missing optional fields are explicitly handled.
- Filter semantics are clear enough for implementation.
- Static hosting constraints are documented.

## Required Session Log

Write `session_logs/YYYY-MM-DD_11_viewer_contract.md` with:

- Viewer contract decisions.
- Any output contract adjustments.
- Open implementation risks for Prompt 12.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent when Python tests are run.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `12` and `14` if viewer file paths, contract semantics, filter behavior, fixture paths or documentation expectations changed.
