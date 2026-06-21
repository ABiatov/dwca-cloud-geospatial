# Viewer UI Cosmetic Hardening

Date: 2026-06-21

## Session

Scope: cosmetic and user-facing text refinements for the static viewer,
focused on `Generated Files`, `Filters` and `Selected Feature`.

## Accepted conclusions

- `Generated Files` should show primary bundle artifact links in this order:
  `data/occurrences.fgb`, `data/occurrences.gpkg`,
  `data/occurrences.parquet`, `metadata/source.json`,
  `metadata/processing.json`.
- The viewer should keep full manifest paths for link targets, but visible
  labels for `data/*` artifacts should omit the `data/` prefix. For example,
  `data/occurrences.fgb` displays as `occurrences.fgb`.
- Required metadata artifacts should use short visible labels:
  `metadata/source.json` displays as `source.json (metadata)` and
  `metadata/processing.json` displays as `processing.json (metadata)`.
- `Generated Files` should not show artifact-specific implementation
  explanations to end users. Removed inline phrases about FlatGeobuf being
  the MVP browser layer, GeoPackage being retained staging and GeoParquet
  browser loading being outside the MVP contract.
- Filter controls should render in this order and Title Case:
  `Scientific Name`, `Kingdom`, `IUCN Red List Categories`, `Event Year`,
  `Basis of Record`, `Quality Flags`.
- `Selected Feature` field labels should render normalized snake_case fields
  in Title Case while preserving acronyms such as `IUCN`, `GBIF`, `OBIS`,
  `DOI`, `ID` and `URL`.
- These decisions affect only the static viewer presentation contract. They
  do not change manifest paths, output bundle layout, FlatGeobuf loading,
  filtering semantics, generated data schemas or the no-backend constraint.

## Updated canonical artifacts

- `viewer/app.js`: implemented artifact ordering, concise generated-file
  rows, shortened visible data and metadata artifact labels, filter ordering
  and Title Case label formatting.
- `demo/output/app.js`: synchronized the copied demo viewer with source
  viewer behavior.
- `tests/test_static_viewer.py`: added regression checks for generated-file
  order, data artifact labels, removal of technical generated-file text,
  filter ordering and Title Case labels.
- `docs/viewer_contract.md`: documented the accepted generated-file inventory,
  filter order/labels and selected-feature label formatting contract.

## ADR updates

No ADR was added. The decisions are UI copy and display-order refinements
within the accepted static viewer contract, not a long-lived architectural
tradeoff.

## Open questions

- None currently recorded for this UI pass.

## Demo evidence

- The user reported updating `docs/assets/viewer-screenshot.png` after the
  viewer UI refinements.

## Acceptance evidence

Focused viewer test run:

```bash
.venv/bin/python -m pytest tests/test_static_viewer.py
```

Result:

```text
10 passed
```

## Follow-up plan

- Refresh demo screenshots after the UI copy and ordering work is considered
  visually complete.
- If generated bundle demo files are regenerated, ensure the copied viewer in
  the bundle still matches `viewer/app.js`.
