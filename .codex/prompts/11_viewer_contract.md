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
- Prompts `01` through `10`
- Latest session logs for prompts `01` through `10`
- Current generated bundle examples/tests.

## Goal

Create `docs/viewer_contract.md` as the accepted contract for the minimal static viewer.

## Tasks

- Define how the viewer discovers data through `manifest.json`.
- Define required and optional metadata files read by the viewer.
- Define FlatGeobuf point layer loading behavior.
- Define dataset provenance panel fields.
- Define feature details panel fields.
- Define MVP filters: `scientific_name`, `kingdom`, `event_year`, `basis_of_record`, `iucn_red_list_category`, `quality_flags`.
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
