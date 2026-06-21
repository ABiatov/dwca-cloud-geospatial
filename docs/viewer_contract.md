# Static Viewer Contract

Status: Accepted MVP contract

Last updated: 2026-06-19

## Purpose

This document defines how the minimal static MapLibre viewer reads output
bundles produced by the DwC-A converter.

The MVP viewer is manifest-driven and file-based. It must be able to inspect a
valid output bundle from static files without a backend service, database,
scheduler, cloud runtime, live GBIF API, live OBIS API or PMTiles.

## Bundle Discovery

Viewer startup begins with a bundle root URL or local static root and reads:

```text
manifest.json
```

All other files must be discovered from `manifest.json`; the viewer must not
hard-code dataset-specific file paths beyond the documented bundle-relative
defaults.

The viewer uses these manifest fields:

| Field | Required behavior |
| --- | --- |
| `bundle_schema_version` | Reject unsupported major/incompatible versions with an unsupported-bundle message. |
| `viewer_contract_version` | Reject unsupported viewer contracts with an unsupported-bundle message. |
| `occurrence_schema_version` | Display or log the schema version; do not infer source Darwin Core terms from it. |
| `title` | Primary dataset title when source metadata has no better title. |
| `created_at` | Generated timestamp in the provenance panel. |
| `generator` | Converter name/version/commit in the provenance panel. |
| `source` | Startup source summary before `metadata/source.json` is loaded. |
| `files` | Authoritative inventory for metadata, reports and downloadable artifacts. |
| `layers` | Authoritative geospatial layer declarations. |
| `viewer` | Default layer, initial bounds, display fields and filter fields. |
| `counts` | High-level source, accepted and rejected counts. |

`manifest.files` lists only generated files. A file absent from the inventory
must be treated as intentionally not generated, not as an error. File paths are
bundle-relative POSIX paths and must not be resolved outside the bundle root.

## Metadata Files

The viewer reads these required metadata files when they are declared in
`manifest.files`:

| Path | Role |
| --- | --- |
| `metadata/source.json` | Source archive, DwC-A, dataset, rights, GBIF and OBIS provenance. |
| `metadata/processing.json` | Converter configuration, output decisions, counts, warnings, validation summary and parser diagnostics. |

If either required metadata file is missing from a generated bundle, fails to
load or fails to parse as JSON, the viewer should show a bundle-load error.
This is a bundle validity problem.

The viewer may expose these optional files as links or metadata rows when they
are declared in `manifest.files`:

| Role | Typical path | Viewer behavior |
| --- | --- | --- |
| `report` | `reports/rejected_records.csv` | Link/download and rejected-count context; parsing is optional for MVP. |
| `geoparquet` | `data/occurrences.parquet` | Analytical artifact link and metadata display; not an MVP browser map source. |
| `geopackage` | `data/occurrences.gpkg` | Retained staging artifact link and metadata display; not an MVP browser map source. |
| `flatgeobuf` | `data/occurrences.fgb` | Preferred MVP map layer when declared in `manifest.layers`. |

Missing optional fields inside metadata objects must be displayed as absent or
unknown. Missing DOI, citation, GBIF keys, OBIS identifiers, publisher,
license, validation warnings or rejected-report files are not load errors.

## Geospatial Layers

The MVP map layer is the first declared layer whose:

- `type` is `point`;
- `source_format` is `flatgeobuf`;
- `path` points to a generated FlatGeobuf file, normally
  `data/occurrences.fgb`.

`manifest.viewer.default_layer` should select that layer when present. If it
does not, the viewer should fall back to the first usable FlatGeobuf point
layer and surface a non-fatal contract warning.

FlatGeobuf loading behavior:

- Read the layer URL from `manifest.layers[].path`, relative to the bundle
  root.
- Use point geometry in longitude/latitude order.
- Treat the CRS as `OGC:CRS84`.
- Use `manifest.layers[].bounds` or `manifest.viewer.initial_bounds` for the
  initial map view when present.
- Use `manifest.layers[].record_count` and `manifest.counts.accepted_records`
  for counts; do not require reading every feature before showing metadata.
- If browser or host support allows range requests, the implementation may use
  FlatGeobuf spatial filtering by current map bounds. If range requests are
  unavailable, it may fetch the file sequentially for small bundles and should
  show a clear performance or unsupported-size message for large bundles.

The viewer must not require PMTiles. PMTiles remains MVP+ and can be added
later as another `manifest.layers` source format.

## GeoPackage Artifacts

`data/occurrences.gpkg` is a retained bundle artifact produced by the
GeoPackage-staged FlatGeobuf path. The viewer should:

- show it in an output/artifacts list when `manifest.files` declares role
  `geopackage`;
- show its record count, byte size and checksum when present;
- describe it as the retained staging/source artifact for the FlatGeobuf
  output;
- offer it as a download link when static hosting permits direct file access.

The MVP viewer must not load GeoPackage as the default browser map layer.
GeoPackage browser rendering is outside this contract.

## No-FlatGeobuf State

Valid bundles may omit `data/occurrences.fgb`, especially explicit
GeoParquet-only bundles and large-output GeoParquet bundles.

When no FlatGeobuf point layer is declared:

- Do not treat the bundle as invalid solely because no map layer is available.
- Load and display `manifest.json`, `metadata/source.json` and
  `metadata/processing.json`.
- Show provenance, counts, generated-file inventory and processing warnings.
- Show a clear no-map-layer state. The current implementation says:
  "No FlatGeobuf map layer is available for this bundle. To display
  occurrence points on the map, generate the bundle with the FlatGeobuf output
  format selected."
- Expose declared GeoParquet files as analytical/download artifacts.
- Do not attempt browser GeoParquet loading in the MVP.

If a later accepted contract adds browser GeoParquet loading, it must update
this document and `docs/output_format.md` if the manifest or bundle shape
changes.

## Provenance Panel

The dataset provenance panel should display these fields when available:

| Label | Source |
| --- | --- |
| Dataset title | `metadata/source.json.dataset.title`, then `manifest.title`, then `manifest.source.title`. |
| Description | `metadata/source.json.dataset.description`. |
| Publisher | `metadata/source.json.dataset.publisher` or `manifest.source.publisher`. |
| Homepage | `metadata/source.json.dataset.homepage`. |
| DOI | `metadata/source.json.dataset.doi`, `metadata/source.json.gbif.doi`, `metadata/source.json.obis.doi`, then `manifest.source.doi`. |
| Citation | `metadata/source.json.dataset.citation`, GBIF citation, OBIS citation, then `manifest.source.citation`. |
| License | GBIF download license, OBIS license, `metadata/source.json.rights.license`, then `manifest.source.license`. |
| Rights holder | `metadata/source.json.rights.rights_holder`. |
| Source archive | `metadata/source.json.source_archive.name`, path, kind, bytes and checksum when present. |
| GBIF dataset key | `metadata/source.json.gbif.dataset_key` or `manifest.source.gbif_dataset_key`. |
| GBIF download key | `metadata/source.json.gbif.download_key` or `manifest.source.gbif_download_key`. |
| OBIS dataset id | `metadata/source.json.obis.dataset_id` or `manifest.source.obis_dataset_id`. |
| Generated timestamp | `manifest.created_at` and `metadata/processing.json.created_at`. |
| Converter version | `manifest.generator.version` and `metadata/processing.json.generator.version`. |
| Counts | `manifest.counts` and `metadata/processing.json.counts`. |
| Validation status | `metadata/processing.json.validation.status`. |
| Processing warnings | `metadata/processing.json.warnings`. |

Processing warning code `large_indexed_flatgeobuf_write` is non-fatal. Display
it as a generation warning with `stage`, `feature_count` and
`estimated_spatial_index_bytes` when present.

DOI provenance rows should render as external links to
`https://doi.org/{doi}` when the value is a bare DOI or DOI URL. Citation
values may contain a DOI URL inside longer text; the viewer should build safe
DOM nodes, keep surrounding citation text as text nodes, and render only the
DOI URL segment as an external link with `target="_blank"` and
`rel="noopener noreferrer"`. Missing DOI or citation values remain absent
rows, not load errors. The viewer must not call GBIF, OBIS or a project
backend to fill citation fields.

Processing warning code `gbif_download_metadata_lookup_failed` is non-fatal
and indicates optional conversion-time GBIF enrichment could not complete.
The static viewer only displays the generated warning and stored provenance.

GeoParquet large-output declarations in
`metadata/processing.json.configuration.geoparquet` should be displayed or
preserved without contradiction: `large_output_mode`,
`covering_bbox_column.enabled`, `spatial_sorting.enabled`,
`spatial_sorting.strategy` and `partitioned_dataset.enabled`. Partitioned
GeoParquet output is currently deferred and should be shown as disabled for
valid MVP bundles.

## Feature Details Panel

When a FlatGeobuf feature is selected, the viewer should show fields from
`manifest.viewer.display_fields` in that order, then any remaining known
details that are present and useful. Missing properties are omitted.

Known details:

| Field |
| --- |
| `scientific_name` |
| `verbatim_scientific_name` |
| `kingdom` |
| `phylum` |
| `class` |
| `order` |
| `family` |
| `genus` |
| `taxon_rank` |
| `iucn_red_list_category` |
| `event_date` |
| `event_year` |
| `basis_of_record` |
| `degree_of_establishment` |
| `decimal_longitude` |
| `decimal_latitude` |
| `coordinate_uncertainty_in_meters` |
| `country_code` |
| `locality` |
| `identified_by` |
| `dataset_name` |
| `license` |
| `references` |
| `rights_holder` |
| `source_record_id` |
| `source_file` |
| `source_row_number` |
| `source_data_row_number` |
| `quality_flags` |
| `has_quality_flags` |

The normalized output field is `class`. Viewer code must not look for the
Python implementation attribute name `class_`.

When `source_record_id` is present, the current viewer derives an additional
`source record URL` detail row after it. The link target is:

```text
https://www.gbif.org/occurrence/{source_record_id}
```

The link opens in a new browser tab with `target="_blank"`.

Selected features should be visibly highlighted on the map. Point colors may
use `kingdom` to improve scanning, with a high-contrast fallback when kingdom
is absent or not in the known color set.

## MVP Filters

The viewer should create filters only for fields present in
`manifest.viewer.filter_fields` and available on the loaded layer. The current
MVP filter fields are:

| Field | Behavior |
| --- | --- |
| `scientific_name` | Case-insensitive text contains search. Empty query matches all records. |
| `kingdom` | Exact categorical match over non-empty values. |
| `event_year` | Numeric year range or exact year values. Null/non-numeric values are excluded only when a year filter is active. |
| `basis_of_record` | Exact categorical match over non-empty values. |
| `iucn_red_list_category` | Exact categorical match over non-empty values. |
| `quality_flags` | Flag presence and exact flag-token filters as described below. |

Filter combination semantics are AND across active filter fields. Multiple
selected values within a categorical field are OR.

If a field is absent from `manifest.viewer.filter_fields`, absent from the
loaded features or intentionally omitted from the generated projection, omit
that filter control. Do not show a blocking error for missing optional filter
fields.

## Quality Flag Semantics

`quality_flags` is nullable text. Records with no flags store `null`, and
records with flags store lowercase snake_case tokens separated by `|`.
Individual flag codes never contain `|`.

Viewer filtering must split on `|` and match exact tokens:

```text
missing_event_date|missing_geodetic_datum
```

matches `missing_event_date` and `missing_geodetic_datum`. It must not match
substrings such as `missing_event`.

For show/hide controls:

- Prefer `has_quality_flags` when the field is present and boolean.
- If `has_quality_flags` is absent, derive flag presence from split
  `quality_flags` tokens.
- Treat `null`, empty string and all-empty token lists as no flags.
- Treat malformed tokens containing empty segments as non-fatal feature-level
  data issues; do not let one malformed feature crash the viewer. Generated
  bundles should already be caught by validation.

## Absent Optional Fields

The manifest writer intersects `manifest.viewer.display_fields` and
`manifest.viewer.filter_fields` with the selected generated projection. The
viewer should trust absent fields as intentionally omitted.

Required behavior for absence:

- Omit missing feature-detail rows.
- Omit missing filter controls.
- Show metadata values as absent/unknown instead of errors.
- Continue loading the bundle when optional files such as rejected reports,
  GeoParquet or GeoPackage artifacts are absent.
- Show a bundle-load error only for missing/invalid `manifest.json`, required
  metadata files, unsupported schema versions, unsafe paths or a declared
  FlatGeobuf layer that cannot be loaded when map display is requested.

## Static Hosting Constraints

The viewer must run from static hosting plus generated bundle files. The MVP
must not require:

- a backend API;
- server-side filtering;
- PostgreSQL/PostGIS or another database;
- live GBIF or OBIS requests;
- taxonomy matching services;
- PMTiles;
- cloud-specific storage APIs.

The viewer should fetch bundle files by relative URLs from the bundle root or
from a user-supplied manifest URL. Static hosts should serve JSON and CSV as
text, Parquet/FlatGeobuf/GeoPackage as binary files, and should allow direct
file downloads for declared artifacts.

For remote FlatGeobuf performance, static hosts should support HTTP range
requests and CORS headers when the viewer and bundle are on different origins.
Without range support, the viewer must still load metadata and may show a
limited-map or unsupported-size message instead of failing the whole bundle.

Basemap tiles, if used by the implementation, must be optional to bundle
inspection. Lack of a basemap must not prevent loading the bundle metadata or
declared occurrence layer.

## Implementation Files

The MVP static viewer implementation lives under:

```text
viewer/
  index.html
  styles.css
  app.js
  README.md
```

`dwca-cloud-geospatial convert` copies the runtime viewer files into each
generated bundle root and writes a generated bundle `README.md`. Opening the
copied `index.html` from a static HTTP server reads the neighboring
`manifest.json`. The browser entry point also accepts
`?bundle=<bundle-root-url>` or `?manifest=<manifest-json-url>` when the shared
source viewer under `viewer/` is served separately.

The current implementation loads MapLibre GL JS and FlatGeobuf JavaScript from
public CDN URLs declared in `viewer/index.html`. These are frontend static
assets only; the viewer still does not call GBIF, OBIS or a project backend.
The map style uses the public OpenStreetMap raster tile endpoint
`https://tile.openstreetmap.org/{z}/{x}/{y}.png` with visible attribution as
the default basemap. For fully offline static hosting, mirror those
JavaScript/CSS assets, configure an offline or self-hosted basemap and update
`viewer/index.html` / `viewer/app.js`.

## Contract Fixtures

Viewer-contract fixtures live under:

```text
tests/fixtures/output_bundles/viewer_contract/
```

They are hand-authored contract snippets, not full output bundles. Prompt 12
viewer smoke tests may use them for manifest semantics, but real data-loading
smoke tests should also use generated bundles from the converter.
