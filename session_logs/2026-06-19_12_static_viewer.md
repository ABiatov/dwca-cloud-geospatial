# Prompt 12: Static Viewer

Date: 2026-06-19

## Viewer File Locations

Implemented the minimal static viewer source under:

```text
viewer/
  index.html
  styles.css
  app.js
  README.md
```

The viewer does not add a backend service. The source files live under
`viewer/`, and `dwca-cloud-geospatial convert` now copies them into each
generated bundle root.

Current local launch pattern after conversion:

```bash
python -m http.server 8000 --directory "${REPO}"
```

```text
http://localhost:8000/scratch/sample-bundle/index.html
```

The shared source viewer still accepts `?bundle=<bundle-root-url>` and
`?manifest=<manifest-json-url>`.

## Data Loading Behavior

- Startup reads `manifest.json`, then required `metadata/source.json` and
  `metadata/processing.json` from paths declared in `manifest.files`.
- Bundle-relative paths are rejected when absolute, URL-like, backslash-based
  or path-traversing.
- Supported bundle and viewer contract versions are currently exact
  `0.1.0`.
- The viewer selects `manifest.viewer.default_layer` only when it is a usable
  FlatGeobuf point layer and falls back to the first declared usable
  FlatGeobuf point layer with a non-fatal warning.
- FlatGeobuf is loaded through the browser FlatGeobuf JavaScript library and
  rendered as a MapLibre GeoJSON source/layer.
- `data/occurrences.gpkg` is shown in generated-file inventory as retained
  GeoPackage staging/source artifact and is not loaded as a browser map layer.
- `data/occurrences.parquet` is shown as an analytical/download artifact and
  is not loaded in the browser.
- GeoParquet-only bundles without FlatGeobuf load manifest/source/processing
  metadata, counts, warnings and generated-file inventory, then show:
  `No FlatGeobuf map layer is available for this bundle.`
- No GBIF or OBIS API calls were added.

## Filter Behavior

Filters are created only when declared in `manifest.viewer.filter_fields` and
present on loaded FlatGeobuf features:

- `scientific_name`: case-insensitive text contains search.
- `kingdom`, `basis_of_record`, `iucn_red_list_category`: exact categorical
  checkbox filters, OR within a field.
- `event_year`: numeric min/max range; non-numeric values are excluded only
  when a year filter is active.
- `quality_flags`: flagged/all/unflagged control plus exact token checkboxes.

`quality_flags` values are split on `|`; exact tokens are matched with
`tokens.includes(selectedToken)`. `has_quality_flags` is preferred for the
flagged/unflagged mode when it is present and boolean.

## Feature And Metadata Display

- Dataset provenance uses `metadata/source.json` first, then manifest source
  fallbacks where documented in `docs/viewer_contract.md`.
- Counts use manifest counts and update visible record count after filtering.
- Processing warnings are displayed, including non-fatal
  `large_indexed_flatgeobuf_write` with stage, feature count and estimated
  spatial-index bytes.
- GeoParquet large-output declarations are displayed from
  `metadata/processing.json.configuration.geoparquet`.
- Feature details display `manifest.viewer.display_fields` first, followed by
  known useful normalized fields that are present.
- Missing optional metadata values, optional files and optional feature fields
  are omitted or shown as unknown rather than causing blocking errors.

## Smoke Evidence

Automated tests added:

```text
tests/test_static_viewer.py
```

Focused verification:

```bash
.venv/bin/python -m pytest tests/test_static_viewer.py -q
```

Result:

```text
5 passed
```

Full verification:

```bash
.venv/bin/python -m pytest tests -q
```

Result:

```text
71 passed, 1 skipped
```

JavaScript syntax check:

```bash
node --check viewer/app.js
```

Result: passed.

Diff whitespace check:

```bash
git diff --check
```

Result: passed.

Generated FlatGeobuf sample bundle:

```bash
.venv/bin/dwca-cloud-geospatial convert \
  tests/fixtures/dwca/minimal_occurrence/normalization \
  /private/tmp/dwca_prompt12_flatgeobuf \
  --overwrite
```

Result: converted successfully with `2` accepted records and `5` rejected
records. Manifest declared:

```text
metadata/source.json
metadata/processing.json
data/occurrences.gpkg
data/occurrences.fgb
reports/rejected_records.csv
```

Validation:

```bash
.venv/bin/dwca-cloud-geospatial validate --json /private/tmp/dwca_prompt12_flatgeobuf
```

Result: `status="passed"` with no errors or warnings.

Generated GeoParquet-only sample bundle:

```bash
.venv/bin/dwca-cloud-geospatial convert \
  tests/fixtures/dwca/minimal_occurrence/normalization \
  /private/tmp/dwca_prompt12_geoparquet \
  --format geoparquet \
  --overwrite
```

Result: converted successfully with `2` accepted records and `5` rejected
records. Manifest declared GeoParquet only for geospatial output and no
FlatGeobuf/GeoPackage files.

Validation:

```bash
.venv/bin/dwca-cloud-geospatial validate --json /private/tmp/dwca_prompt12_geoparquet
```

Result: `status="passed_with_warnings"` with no required errors. The warning
was the existing optional Pyogrio/GDAL GeoParquet reader skip because local
GDAL does not recognize Parquet/GeoParquet as a vector read format.

Temporary static-host smoke setup:

```text
/private/tmp/dwca_prompt12_static_site.jNeG8a/
  viewer/
  flatgeobuf/
  geoparquet/
```

The local sandbox allowed starting `python -m http.server` only with approved
escalation. The server bound to port `8765`, but separate sandboxed commands
could not connect back to `127.0.0.1` or `::1`, so HTTP fetch verification was
not completed in this environment. The automated tests still generated and
validated the same static bundle inputs used by the viewer.

PyArrow emitted sandbox-related CPU feature `sysctlbyname` warnings during
some conversion/validation commands, matching earlier sessions. Conversion,
validation and tests completed successfully.

## Known Browser And Static-Hosting Limitations

- The viewer references MapLibre GL JS `4.7.1` and FlatGeobuf JavaScript
  `4.3.3` from public CDN URLs in `viewer/index.html`; fully offline static
  hosting should mirror these assets and update the HTML.
- Lack of MapLibre or FlatGeobuf browser assets prevents map rendering, but
  metadata/provenance loading remains the baseline inspection path.
- Large FlatGeobuf browser loading still depends on browser memory and host
  support for direct binary file access. Remote large-file performance is best
  when static hosts support range requests and CORS for cross-origin access.
- No browser GeoParquet or GeoPackage rendering is implemented. Those formats
  remain generated-file inventory/download artifacts in the MVP viewer.
- No Playwright/browser pixel check was added; verification used generated
  static inputs, validator checks, JavaScript syntax checking and Python smoke
  tests.

## Files Created Or Updated

- Created `viewer/index.html`.
- Created `viewer/styles.css`.
- Created `viewer/app.js`.
- Created `viewer/README.md`.
- Created `tests/test_static_viewer.py`.
- Updated `README.md`.
- Updated `docs/developer_setup.md`.
- Updated `docs/development_plan.md`.
- Updated `docs/viewer_contract.md`.
- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md`.

## Prompt Updates

- Updated `.codex/prompts/13_tkinter_gui.md` with static viewer path, copied
  `<output>/index.html` launch pattern, CDN and OpenStreetMap dependency
  behavior, FlatGeobuf `Uint8Array` loading, hidden empty-state handling,
  derived GBIF source-record links, kingdom marker colors, selected-feature
  highlighting and smoke-test handoff.
- Updated `.codex/prompts/14_demo_docs_hardening.md` with final-doc viewer
  path, launch instructions, frontend asset and OpenStreetMap limitations,
  FlatGeobuf `Uint8Array` loading, hidden empty-state handling, derived GBIF
  source-record links, kingdom marker colors, selected-feature highlighting
  and verification command.
- Updated `.codex/prompts/dev_flow_description.md` so the current next work
  item is `13_tkinter_gui.md`.

## Follow-Up Runtime Fix

After manual browser testing against a generated bundle, FlatGeobuf loading
failed with:

```text
Cannot destructure property 'minX' of 'r' as it is undefined.
```

Cause: the viewer called `flatgeobuf.deserialize(url.href)`. The FlatGeobuf
GeoJSON browser API routes string URLs through filtered loading and expects a
rectangle argument. The viewer now fetches the file as bytes and calls
`flatgeobuf.deserialize(new Uint8Array(arrayBuffer))` for the MVP full-file
load path.

Verification:

```bash
node --check viewer/app.js
.venv/bin/python -m pytest tests/test_static_viewer.py -q
```

Result: both passed; static viewer tests reported `5 passed`.

## Follow-Up OpenStreetMap Basemap

Added the public OpenStreetMap raster tile endpoint as the default MapLibre
basemap:

```text
https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

The raster source includes visible OpenStreetMap attribution through MapLibre.
This is an external basemap tile request only; it does not add a project
backend and does not call GBIF or OBIS. Fully offline hosting should replace
or mirror the basemap in `viewer/app.js`.

Verification:

```bash
node --check viewer/app.js
.venv/bin/python -m pytest tests/test_static_viewer.py -q
```

Result: both passed; static viewer tests reported `5 passed`.

## Follow-Up Empty-State Overlay Fix

Manual browser testing showed `#map-empty-state` could still cover the map
even with `hidden=""`, because the author CSS rule `.empty-state { display:
grid; }` overrode the browser default hidden styling. Added:

```css
.empty-state[hidden] {
  display: none;
}
```

This hides the empty/error overlay when a map layer is available and prevents
it from intercepting map interaction.

Verification:

```bash
.venv/bin/python -m pytest tests/test_static_viewer.py -q
```

Result: static viewer tests reported `5 passed`.

## Follow-Up Automatic Viewer Copy

`dwca-cloud-geospatial convert` now copies the static viewer source files into
each generated output bundle root:

```text
index.html
styles.css
app.js
README.md
```

The copied `index.html` reads the neighboring `manifest.json`, so generated
bundles can be opened directly from a static HTTP server:

```text
http://localhost:8000/path/to/output-bundle/index.html
```

The viewer files are not added to `manifest.files`; that inventory remains for
generated data, metadata and reports. CLI output now prints the copied viewer
entry path.

Verification:

```bash
.venv/bin/python -m pytest tests/test_conversion.py tests/test_cli.py tests/test_static_viewer.py -q
```

Result: `22 passed`.

## Follow-Up Feature Detail And Marker Styling

Added viewer refinements:

- derived `source record URL` row immediately after `source record id` when
  `source_record_id` is present;
- GBIF occurrence link format:
  `https://www.gbif.org/occurrence/{source_record_id}`;
- generated link uses `target="_blank"` and `rel="noopener noreferrer"`;
- occurrence marker colors now use a high-contrast `kingdom` match expression;
- selected feature is highlighted by a dedicated MapLibre circle layer
  `occurrence-selected`.

Verification:

```bash
node --check viewer/app.js
.venv/bin/python -m pytest tests/test_static_viewer.py -q
```

Result: both passed; static viewer tests reported `5 passed`.
