# Prompt 11: Viewer Contract

Date: 2026-06-19

## Viewer Contract Decisions

- Created `docs/viewer_contract.md` as the accepted MVP static viewer
  contract.
- Viewer startup is manifest-driven from `manifest.json`; all metadata,
  artifacts and layers are discovered through manifest fields.
- Required viewer metadata files are `metadata/source.json` and
  `metadata/processing.json`.
- The MVP browser map source is a declared FlatGeobuf point layer, normally
  `data/occurrences.fgb`, with point geometry in longitude/latitude order and
  CRS `OGC:CRS84`.
- Persistent GeoPackage artifacts such as `data/occurrences.gpkg` are exposed
  as retained artifact/download metadata only. They are not the default
  browser map layer.
- Valid GeoParquet-only bundles, including large-output GeoParquet bundles,
  may omit FlatGeobuf. The accepted viewer behavior is a graceful
  no-FlatGeobuf/no-map-layer state while still displaying manifest, source and
  processing metadata.
- Browser GeoParquet loading is not accepted for the MVP viewer contract.
- Provenance panel fields, feature detail fields and MVP filter fields are
  documented.
- `quality_flags` filtering must split nullable `|`-delimited strings and
  match exact tokens. `has_quality_flags` is preferred for flagged/unflagged
  controls when present.
- Optional absent fields are intentionally omitted from filter controls and
  feature details instead of causing viewer errors.
- The viewer must not require a backend, server-side filtering, live GBIF or
  OBIS APIs, taxonomy services, PMTiles, cloud-specific storage APIs or a
  database.

## Output Contract Adjustments

- No output bundle shape changes were made.
- `docs/output_format.md` already points to `docs/viewer_contract.md` for the
  no-FlatGeobuf viewer behavior, so it did not require updates in this
  session.
- Added hand-authored viewer-contract manifest snippets under
  `tests/fixtures/output_bundles/viewer_contract/`. These fixtures do not
  change generated bundle output.

## Fixtures And Tests

- Added `tests/fixtures/output_bundles/viewer_contract/README.md`.
- Added
  `tests/fixtures/output_bundles/viewer_contract/flatgeobuf_with_geopackage_manifest.json`
  to document a FlatGeobuf map layer with a GeoPackage inventory artifact.
- Added
  `tests/fixtures/output_bundles/viewer_contract/geoparquet_only_manifest.json`
  to document a valid GeoParquet-only no-FlatGeobuf state.
- Added `tests/test_viewer_contract.py` to verify:
  - the viewer contract document records MVP map/source boundaries;
  - GeoPackage is inventory-only in the FlatGeobuf fixture;
  - GeoParquet-only manifests are valid no-FlatGeobuf fixtures;
  - filter fields match the accepted MVP set;
  - the normalized output field is `class`, not `class_`.

## Open Implementation Risks For Prompt 12

- Browser FlatGeobuf performance will depend on host support for HTTP range
  requests and CORS when the viewer and bundle are served from different
  origins.
- GeoParquet-only bundles need a clear no-map-layer UI state so users do not
  interpret the bundle as invalid.
- The viewer should handle malformed optional feature properties defensively,
  but generated bundles should still rely on `dwca-cloud-geospatial validate`
  for strict quality flag and field validation.
- Basemap availability should not block metadata or occurrence-layer loading.
- Prompt 12 should use generated bundles for real data-loading smoke tests;
  the Prompt 11 fixtures are manifest-semantics fixtures only.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`.

```bash
.venv/bin/python -m pytest tests/test_viewer_contract.py -q
```

Result:

```text
3 passed in 0.03s
```

```bash
.venv/bin/python -m pytest tests -q
```

Result:

```text
66 passed, 1 skipped in 3.23s
```

The skipped test is the existing dependency-dependent Pyogrio/GDAL
GeoParquet-aware reader check.

```bash
git diff --check
```

Result: passed with no output.

## Files Created Or Updated

- Updated `README.md` with a link to the accepted static viewer contract and
  the FlatGeobuf/GeoPackage/GeoParquet-only viewer behavior.
- Updated `docs/development_plan.md` so M5 and immediate next actions reflect
  that the viewer contract is already accepted and Prompt 12 should implement
  against it.
- Created `docs/viewer_contract.md`.
- Created `tests/test_viewer_contract.py`.
- Created `tests/fixtures/output_bundles/viewer_contract/README.md`.
- Created
  `tests/fixtures/output_bundles/viewer_contract/flatgeobuf_with_geopackage_manifest.json`.
- Created
  `tests/fixtures/output_bundles/viewer_contract/geoparquet_only_manifest.json`.
- Updated `.codex/prompts/12_static_viewer.md`.
- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md`.

## Follow-Up Documentation Audit

After Prompt 11, project documentation was checked for viewer-contract handoff
coverage. `docs/knowledge_base/topics/pmtiles_viewer.md` and
`docs/knowledge_base/playbooks/add_static_viewer_output.md` already referenced
the accepted no-FlatGeobuf behavior and exact-token `quality_flags` filtering.
`README.md` and `docs/development_plan.md` were updated so the accepted viewer
contract and Prompt 12 handoff are visible in canonical project-facing
documentation. `docs/output_format.md` was tightened so the viewer filter
table states the accepted exact-token `quality_flags` behavior instead of
describing it as a future addition.

## Prompt Updates

- Updated `.codex/prompts/12_static_viewer.md` with Prompt 11 viewer contract
  decisions, no-map-layer behavior and fixture paths.
- Updated `.codex/prompts/13_tkinter_gui.md` with Prompt 11 viewer contract
  implications for GUI viewer instructions, GeoPackage artifact handling and
  GeoParquet-only no-map-layer guidance.
- Updated `.codex/prompts/14_demo_docs_hardening.md` with final-doc viewer
  contract decisions, filter semantics and fixture paths.
- Updated `.codex/prompts/dev_flow_description.md` so the current next work
  item is `12_static_viewer.md`.
