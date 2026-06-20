# Output Format

Status: Accepted baseline for MVP

Last updated: 2026-06-20

## Purpose

This document defines the portable output bundle produced by the DwC-A converter and consumed by the static viewer, CLI validation commands, Python integrations and future `biodiversity-viewer-serverless` work.

The MVP output bundle is file-based and static-hostable. It must not require a database, API service or live GBIF/OBIS network access to be inspected after conversion.

## Bundle Layout

Default output directory:

```text
output/
  index.html                    # static viewer entry point copied by convert
  styles.css                    # static viewer style
  app.js                        # static viewer behavior
  README.md                     # static viewer launch notes
  manifest.json
  metadata/
    source.json
    processing.json
  data/
    occurrences.gpkg            # when FlatGeobuf is generated
    occurrences.fgb             # when FlatGeobuf is generated
    occurrences.parquet         # when GeoParquet is selected
  reports/                      # when one or more records are rejected
    rejected_records.csv
```

MVP files:

- `index.html`, `styles.css`, `app.js` and `README.md`: static viewer files
  copied into the bundle root by `convert`. These files are convenience
  publishing assets and are not listed in `manifest.files`.
- `manifest.json`: top-level discovery document for tools and the viewer.
- `metadata/source.json`: source archive, DwC-A, GBIF and OBIS provenance when available.
- `metadata/processing.json`: converter version, configuration, counts, warnings and validation summary.
- `data/occurrences.fgb`: default FlatGeobuf output for GIS exchange and simple viewer loading.
- `data/occurrences.gpkg`: persistent GeoPackage staging artifact retained
  whenever FlatGeobuf is generated; this is a bundle artifact, not a
  temporary file.
- `data/occurrences.parquet`: GeoParquet occurrence table when GeoParquet output is explicitly selected.
- `reports/rejected_records.csv`: rejected or skipped records with reason codes and source context, written only when at least one record is rejected or skipped.

Deferred MVP+ files:

- `tiles/occurrences.pmtiles`: future optimized tiled map output. PMTiles generation is deferred to MVP+ and should use Tippecanoe as the preferred tiler when available. Tippecanoe remains an optional external dependency, not an MVP runtime requirement. PMTiles point attributes should default to the same compact normalized occurrence field set as FlatGeobuf; a smaller PMTiles-specific attribute profile may be introduced later for large datasets if tile size or browser performance requires it.

## Format Selection

When the user does not choose an explicit conversion format, the MVP converter should write FlatGeobuf output by default.

GeoParquet remains an MVP-supported output format for analytical workflows, but it should be generated only when the user explicitly selects it or when a documented command/config option requests a full multi-format bundle.

Generated data, metadata and report files must be listed in `manifest.files`.
Static viewer files copied into the bundle root are not data artifacts and are
not listed in `manifest.files`.

## Versioning

Each output bundle must declare:

- `bundle_schema_version`: version of this output bundle contract.
- `viewer_contract_version`: version of the static viewer contract the bundle supports.
- `occurrence_schema_version`: version of the normalized occurrence table schema.
- `created_at`: UTC timestamp in ISO 8601 format.

Initial MVP versions:

```json
{
  "bundle_schema_version": "0.1.0",
  "viewer_contract_version": "0.1.0",
  "occurrence_schema_version": "0.1.0"
}
```

Before the first tagged release, these versions may change. After the first tagged release, breaking changes require a new schema version and migration notes.

## Canonical Occurrence Schema And Projections

The normalized occurrence schema is the canonical project-level representation for accepted geospatial occurrence records. It is independent of any single file format and is versioned by `occurrence_schema_version`.

The canonical schema uses stable snake_case field names. Darwin Core source terms, GBIF fields, OBIS fields, IUCN terms and enrichment fields should be mapped into these project field names through `metadata/processing.json.field_mapping`; generated output columns should not mix source camelCase terms into the normalized schema. For example, the normalized field is `iucn_red_list_category`, even when the source term or enrichment provider uses a different spelling such as `http://iucn.org/terms/iucnRedListCategory`.

The canonical schema includes these field groups:

| Field group | Purpose | Examples |
| --- | --- | --- |
| Source identity and provenance | Trace each accepted output record back to the source archive row. | `source_record_id`, `source_file`, `source_row_number`, `source_data_row_number`, `occurrence_id` |
| Taxonomy and identification | Provide the names and ranks needed for display, filtering and analysis when present. | `scientific_name`, `verbatim_scientific_name`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `taxon_id`, `taxon_rank`, `identified_by` |
| Record semantics | Preserve common occurrence attributes useful for filtering and interpretation. | `basis_of_record`, `degree_of_establishment`, `event_date`, `event_year`, `recorded_by` |
| Location and geometry inputs | Preserve parsed coordinates and relevant location context. | `decimal_longitude`, `decimal_latitude`, `coordinate_uncertainty_in_meters`, `geodetic_datum`, `country_code`, `locality` |
| Dataset, rights and provenance metadata | Carry dataset identity, publisher and rights fields onto records where useful. | `dataset_name`, `dataset_key`, `publisher`, `license`, `rights_holder`, `references` |
| Quality and derived fields | Expose converter decisions and derived convenience values. | `quality_flags`, `has_quality_flags`, `iucn_red_list_category` |
| Optional source-preservation fields | Keep selected raw/source identifiers and verbatim values without exporting full raw tables. | `catalog_number`, `collection_code`, `institution_code`, `record_number`, `organism_id`, `gbif_id`, `obis_id`, `raw_decimal_longitude`, `raw_decimal_latitude`, `raw_event_date` |

MVP outputs are projections of the canonical occurrence schema:

| Output | Projection role | Required relationship to canonical schema |
| --- | --- | --- |
| `data/occurrences.parquet` | Analytical GeoParquet projection. | Should carry the broad normalized field set needed for analysis, provenance and GeoParquet geometry metadata. |
| `data/occurrences.fgb` | Compact viewer and exchange projection when FlatGeobuf is generated. | May omit analytical-only fields, but must include stable provenance fields, point geometry, viewer display fields, accepted filter fields, parsed coordinates, `quality_flags` and `has_quality_flags` when generated. |
| `data/occurrences.gpkg` | Persistent GeoPackage staging projection when FlatGeobuf is generated. | Uses the same compact accepted-record projection as FlatGeobuf and must reconcile record counts and accepted record set with `data/occurrences.fgb`. It is inventoried for audit/download but is not the MVP default viewer map layer. |
| Future `tiles/occurrences.pmtiles` | MVP+ tiled visualization projection. | Should derive from the same accepted records and default to the FlatGeobuf compact field set unless a later accepted decision defines a smaller tile attribute profile. |

When both GeoParquet and FlatGeobuf are generated, they must represent the same accepted occurrence record set unless `metadata/processing.json` documents a deliberate export filter. Rejected, skipped, missing-coordinate or invalid-coordinate rows are not part of the accepted occurrence projections; they belong in `reports/rejected_records.csv` and processing metadata.

## `manifest.json`

`manifest.json` is the bundle entry point. Tools and viewers should start here and discover all other files from it.

Required fields:

| Field | Type | Description |
| --- | --- | --- |
| `bundle_schema_version` | string | Output bundle schema version. |
| `viewer_contract_version` | string | Viewer contract version supported by this bundle. |
| `occurrence_schema_version` | string | Normalized occurrence table schema version. |
| `id` | string | Stable output bundle identifier generated by the converter. |
| `title` | string | Human-readable dataset or bundle title. |
| `created_at` | string | UTC ISO 8601 timestamp. |
| `generator` | object | Converter name, version and optional commit. |
| `source` | object | Short source summary for viewer startup. |
| `files` | array | Inventory of generated files. |
| `layers` | array | Viewer-readable geospatial layers. |
| `viewer` | object | Viewer defaults and fields. |
| `counts` | object | High-level accepted, rejected and output record counts. |

Recommended `source` fields:

| Field | Type | Description |
| --- | --- | --- |
| `title` | string or null | Source dataset title. |
| `publisher` | string or null | Source publisher or organization. |
| `doi` | string or null | DOI when present. |
| `citation` | string or null | Citation text when present. |
| `license` | string or null | License or rights URI/text when present. |
| `gbif_dataset_key` | string or null | GBIF dataset key when available. |
| `gbif_download_key` | string or null | GBIF download key when available. |
| `obis_dataset_id` | string or null | OBIS dataset identifier when available. |

Required `files[]` fields:

| Field | Type | Description |
| --- | --- | --- |
| `path` | string | Relative path from bundle root. |
| `role` | string | Logical role, such as `metadata`, `geopackage`, `geoparquet`, `flatgeobuf` or `report`. |
| `media_type` | string | MIME/media type where known. |
| `bytes` | integer or null | File size in bytes when available. |
| `sha256` | string or null | File checksum when available. |
| `record_count` | integer or null | Row count when applicable. |

Required `layers[]` fields:

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Stable layer identifier. |
| `title` | string | Human-readable layer title. |
| `type` | string | `point`. |
| `source_format` | string | `flatgeobuf` for MVP viewer layer, `geoparquet` for analytical data. |
| `path` | string | Relative path to source file. |
| `geometry` | object | Geometry column, CRS and coordinate order. |
| `record_count` | integer | Number of records in the layer. |
| `bounds` | array or null | `[west, south, east, north]` in lon/lat order. |

Example with FlatGeobuf and GeoParquet selected, and rejected records present:

```json
{
  "bundle_schema_version": "0.1.0",
  "viewer_contract_version": "0.1.0",
  "occurrence_schema_version": "0.1.0",
  "id": "dwca-geo-20260604-001",
  "title": "Example occurrence dataset",
  "created_at": "2026-06-04T12:00:00Z",
  "generator": {
    "name": "dwca-cloud-geospatial",
    "version": "0.1.0",
    "commit": null
  },
  "source": {
    "title": "Example occurrence dataset",
    "publisher": null,
    "doi": null,
    "citation": null,
    "license": null,
    "gbif_dataset_key": null,
    "gbif_download_key": null,
    "obis_dataset_id": null
  },
  "files": [
    {
      "path": "metadata/source.json",
      "role": "metadata",
      "media_type": "application/json",
      "bytes": null,
      "sha256": null,
      "record_count": null
    },
    {
      "path": "metadata/processing.json",
      "role": "metadata",
      "media_type": "application/json",
      "bytes": null,
      "sha256": null,
      "record_count": null
    },
    {
      "path": "data/occurrences.gpkg",
      "role": "geopackage",
      "media_type": "application/geopackage+sqlite3",
      "bytes": null,
      "sha256": null,
      "record_count": 1000
    },
    {
      "path": "data/occurrences.parquet",
      "role": "geoparquet",
      "media_type": "application/vnd.apache.parquet",
      "bytes": null,
      "sha256": null,
      "record_count": 1000
    },
    {
      "path": "data/occurrences.fgb",
      "role": "flatgeobuf",
      "media_type": "application/octet-stream",
      "bytes": null,
      "sha256": null,
      "record_count": 1000
    },
    {
      "path": "reports/rejected_records.csv",
      "role": "report",
      "media_type": "text/csv",
      "bytes": null,
      "sha256": null,
      "record_count": 200
    }
  ],
  "layers": [
    {
      "id": "occurrences",
      "title": "Occurrences",
      "type": "point",
      "source_format": "flatgeobuf",
      "path": "data/occurrences.fgb",
      "geometry": {
        "column": "geometry",
        "crs": "OGC:CRS84",
        "coordinate_order": "longitude_latitude"
      },
      "record_count": 1000,
      "bounds": [-10.0, 35.0, 5.0, 60.0]
    }
  ],
  "viewer": {
    "default_layer": "occurrences",
    "initial_bounds": [-10.0, 35.0, 5.0, 60.0],
    "display_fields": [
      "scientific_name",
      "event_date",
      "basis_of_record",
      "source_record_id"
    ],
    "filter_fields": [
      "scientific_name",
      "kingdom",
      "event_year",
      "basis_of_record",
      "iucn_red_list_category",
      "quality_flags"
    ]
  },
  "counts": {
    "source_records": 1200,
    "accepted_records": 1000,
    "rejected_records": 200,
    "occurrence_records": 1000
  }
}
```

## `metadata/source.json`

`source.json` preserves source archive and dataset provenance. It should include raw values when available and normalized fields for viewer display.

Required fields:

| Field | Type | Description |
| --- | --- | --- |
| `source_archive` | object | Input archive path, name, size and checksum when known. |
| `dwca` | object | DwC-A metadata parsed from `meta.xml` and EML when available. |
| `dataset` | object | Normalized dataset identity and citation fields. |
| `rights` | object | License and rights fields. |
| `gbif` | object | GBIF provenance fields, nullable. |
| `obis` | object | OBIS provenance fields, nullable. |
| `source_files` | array | Declared files from the archive and their roles. |

Recommended `dataset` fields:

| Field | Type | Description |
| --- | --- | --- |
| `title` | string or null | Dataset title. |
| `description` | string or null | Dataset description or abstract. |
| `publisher` | string or null | Publishing organization. |
| `homepage` | string or null | Dataset homepage. |
| `doi` | string or null | DOI from source metadata. |
| `citation` | string or null | Preferred citation. |

Recommended `gbif` fields:

| Field | Type | Description |
| --- | --- | --- |
| `dataset_key` | string or null | GBIF dataset key. |
| `download_key` | string or null | GBIF occurrence download key. |
| `doi` | string or null | GBIF occurrence download DOI, when available. Stored as a bare DOI string such as `10.15468/dl.3xbk5b`. |
| `citation` | string or null | GBIF occurrence download citation text. When derived from GBIF download metadata, this should use the recommended occurrence download form and include the DOI as a `https://doi.org/...` URL. |
| `license` | string or null | GBIF license value. |

Recommended `obis` fields:

| Field | Type | Description |
| --- | --- | --- |
| `dataset_id` | string or null | OBIS dataset identifier. |
| `resource_id` | string or null | OBIS resource identifier when available. |
| `doi` | string or null | OBIS DOI, when available. |
| `citation` | string or null | OBIS citation text. |
| `license` | string or null | OBIS license value. |

GBIF occurrence download DOI/citation metadata belongs in `gbif`, not in
`dataset`, unless the source EML itself provides a dataset-level DOI or
citation. The converter may populate `gbif.download_key`, `gbif.doi` and
`gbif.citation` from explicit conversion options or from opt-in
conversion-time GBIF API enrichment. Ordinary conversion remains no-network
and missing values should be stored as `null`.

The converter must not invent GBIF or OBIS identifiers. Missing values should be stored as `null`.

## `metadata/processing.json`

`processing.json` records how the bundle was created.

Required fields:

| Field | Type | Description |
| --- | --- | --- |
| `created_at` | string | UTC ISO 8601 timestamp. |
| `generator` | object | Converter name, version, commit and runtime information. |
| `input` | object | Input archive path, checksum and detected format. |
| `configuration` | object | Effective conversion configuration and config hash. |
| `source_provenance` | object | Resolved optional source-enrichment metadata used during conversion, including GBIF download DOI/citation metadata when supplied or enriched. |
| `field_mapping` | object | Source terms mapped into normalized fields. Includes supported Darwin Core, Dublin Core, GBIF, OBIS and IUCN terms where applicable. |
| `quality_rules` | object | Coordinate, date and required-field rule versions. |
| `counts` | object | Source, accepted, rejected and output row counts. |
| `type_conversion_failures` | array | Type conversion failures counted by field and reason. |
| `warnings` | array | Non-fatal conversion warnings. |
| `validation` | object | Output validation result summary. |

Required `counts` fields:

| Field | Type |
| --- | --- |
| `source_records` | integer |
| `parsed_records` | integer |
| `accepted_records` | integer |
| `rejected_records` | integer |
| `warning_count` | integer |
| `geoparquet_records` | integer |
| `flatgeobuf_records` | integer |

For formats not generated in a conversion, the corresponding output count should be `0`.
`warning_count` should equal the number of entries in `warnings`, including
normalization warnings and non-fatal writer warnings.

When GBIF download DOI/citation metadata is supplied manually or resolved
through opt-in enrichment, `source_provenance.gbif` repeats the resolved
`download_key`, `doi`, `citation` and `license` values for processing audit.
The canonical source-provenance copy remains `metadata/source.json.gbif`, and
the viewer-facing summary remains `manifest.source`.

Required `type_conversion_failures[]` fields:

| Field | Type | Description |
| --- | --- | --- |
| `field` | string | Normalized field name or source term. |
| `reason_code` | string | Stable machine-readable conversion failure reason. |
| `failure_count` | integer | Number of parsed records affected. |
| `failure_rate` | number | Failure count divided by parsed record count. |
| `action` | string | `null_value`, `record_rejected` or `conversion_failed`. |

Optional-field conversion failures should set normalized values to null and emit warnings when the failure rate for a field is `>= 5%` of parsed records. Critical-field failures, including coordinate parsing failures, should reject affected records with stable reason codes. The conversion should fail only when no accepted occurrence records remain, required provenance fields cannot be produced, or parser/metadata structure prevents reliable row interpretation.

Initial type-conversion and validation failure reason codes:

| Reason code | Meaning |
| --- | --- |
| `invalid_float` | Optional numeric float conversion failed; the normalized value is set to null. |
| `invalid_integer` | Optional integer conversion failed; the normalized value is set to null. |
| `missing_coordinates` | Required latitude or longitude is empty or absent; the record is rejected. |
| `invalid_latitude` | Required latitude cannot be parsed as a finite number; the record is rejected. |
| `invalid_longitude` | Required longitude cannot be parsed as a finite number; the record is rejected. |
| `coordinate_out_of_range` | Required latitude or longitude is outside valid ranges; the record is rejected. |
| `zero_zero_coordinate` | Coordinate is exactly `0,0` and excluded by policy; the record is rejected. |
| `missing_required_field` | Required provenance needed for output cannot be produced; the record is rejected. |

Required `warnings[]` fields:

| Field | Type | Description |
| --- | --- | --- |
| `code` | string | Stable machine-readable warning code. |
| `message` | string | Human-readable warning message. |
| `stage` | string | Processing stage that emitted the warning, such as `normalization` or `flatgeobuf_writer`. |
| `field` | string or null | Normalized field or source term affected when applicable. |
| `reason_code` | string or null | Stable conversion failure reason that caused the warning when applicable. |
| `failure_count` | integer or null | Number of parsed records affected when applicable. |
| `failure_rate` | number or null | Failure count divided by parsed record count when applicable. |

Initial warning codes:

| Warning code | Meaning |
| --- | --- |
| `optional_conversion_failure_rate` | Optional-field conversion failures for a field reached the warning threshold of `>= 5%` of parsed records. |
| `large_indexed_flatgeobuf_write` | A default indexed FlatGeobuf write may require substantial spatial-index construction memory. |

FlatGeobuf writer warnings should also include `feature_count` and
`estimated_spatial_index_bytes` when available. Conversion-specific fields
such as `field`, `reason_code`, `failure_count` and `failure_rate` should be
`null` for writer warnings that are not caused by a source field conversion.

Recommended `validation` fields:

| Field | Type | Description |
| --- | --- | --- |
| `status` | string | `passed`, `passed_with_warnings` or `failed`. |
| `errors` | array | Validation errors. |
| `warnings` | array | Validation warnings. |
| `checked_files` | array | Files checked by the converter. |

## `data/occurrences.parquet`

`occurrences.parquet` is the analytical occurrence output when GeoParquet is selected. It must be valid Parquet with GeoParquet metadata.

Geometry:

- Geometry type: point.
- Geometry column: `geometry`.
- Coordinate order: longitude, latitude.
- CRS: `OGC:CRS84` for unambiguous lon/lat order.
- Source coordinates must be preserved in separate numeric columns.
- File-level bounds must be preserved in GeoParquet metadata for metadata
  handoff and bundle manifests.

Large-output behavior:

- The implemented bounded-memory large-archive path applies to GeoParquet-only
  conversions with `GeoParquetWriterOptions.large_output_mode=True`.
- Implemented large-archive pipeline shape:
  - streaming/chunked occurrence reader;
  - chunked normalization result handoff;
  - streaming GeoParquet accepted-record writer;
  - streaming rejected-record/report writer;
  - bounded-memory counts and warning aggregation.
- For large GeoParquet 1.1 outputs, a covering bbox column is default-on. The
  column should be named `bbox` and encoded as a struct with numeric fields
  `xmin`, `ymin`, `xmax` and `ymax`, matching GeoParquet 1.1 covering bbox
  conventions for point geometries in `OGC:CRS84`.
- For large GeoParquet outputs, spatial sorting is default-on and
  strategy-configurable. The implemented `grid` strategy streams rows into
  temporary coarse longitude/latitude buckets and emits buckets in sorted
  spatial order. It avoids a full Python in-memory sort.
- Partitioned GeoParquet dataset output is an optional large-dataset mode,
  but remains deferred. Enabling partitioned mode is rejected until the
  manifest and validator contract can represent partition file inventories and
  aggregate counts cleanly.
- Processing metadata must record whether covering bbox, spatial sorting or
  partitioned output was used, including the selected strategy, threshold or
  partition key when applicable.

Large-output processing configuration fields under
`metadata/processing.json.configuration.geoparquet`:

| Field | Meaning |
| --- | --- |
| `large_output_mode` | Whether large-output GeoParquet behavior was requested. |
| `covering_bbox_column.enabled` | Whether the `bbox` struct column was written. |
| `covering_bbox_column.strategy` | `point_bbox_struct` when enabled. |
| `spatial_sorting.enabled` | Whether spatial sorting was applied before writing. |
| `spatial_sorting.strategy` | `grid` for the implemented bounded strategy. |
| `partitioned_dataset.enabled` | Always `false` until partitioned output is implemented. |
| `partitioned_dataset.partition_key` | Requested partition key, or `null`. |
| `partitioned_dataset.threshold` | Requested threshold, or `null`. |

Required GeoParquet projection fields:

| Field | Type | Source or meaning |
| --- | --- | --- |
| `occurrence_id` | string or null | Darwin Core `occurrenceID`. |
| `source_record_id` | string | Stable project source row identifier. |
| `source_file` | string | Source archive file containing the row. |
| `source_row_number` | integer | Physical 1-based row number in the source data file, including skipped header rows. |
| `source_data_row_number` | integer or null | Logical 1-based data-record number after declared header rows, when available. |
| `scientific_name` | string or null | Darwin Core `scientificName`. |
| `kingdom` | string or null | Darwin Core `kingdom`. |
| `taxon_id` | string or null | Darwin Core `taxonID`. |
| `basis_of_record` | string or null | Darwin Core `basisOfRecord`. |
| `iucn_red_list_category` | string or null | IUCN Red List category when present in source data or accepted enrichment. Current source terms include `http://iucn.org/terms/iucnRedListCategory`, `http://rs.gbif.org/terms/1.0/iucnRedListCategory` and `http://rs.tdwg.org/dwc/terms/iucnRedListCategory`. |
| `event_date` | string or null | Darwin Core `eventDate`, normalized where possible. |
| `event_year` | integer or null | Year derived from `eventDate` or `year`. |
| `decimal_longitude` | double | Parsed longitude. |
| `decimal_latitude` | double | Parsed latitude. |
| `coordinate_uncertainty_in_meters` | double or null | Darwin Core `coordinateUncertaintyInMeters`. |
| `geodetic_datum` | string or null | Darwin Core `geodeticDatum`. |
| `country_code` | string or null | Darwin Core `countryCode`. |
| `locality` | string or null | Darwin Core `locality`. |
| `recorded_by` | string or null | Darwin Core `recordedBy`. |
| `identified_by` | string or null | Darwin Core `identifiedBy`. |
| `license` | string or null | Record or dataset license when available. |
| `rights_holder` | string or null | Darwin Core `rightsHolder`. |
| `dataset_name` | string or null | Darwin Core `datasetName` or source metadata. |
| `dataset_key` | string or null | GBIF dataset key, OBIS dataset id or source dataset key when available. |
| `publisher` | string or null | Source publisher when available. |
| `quality_flags` | string or null | Quality flags assigned by the converter as `\|`-delimited tokens. Null when no flags are present. |
| `has_quality_flags` | boolean | True when `quality_flags` is not empty. |
| `geometry` | geometry | GeoParquet point geometry. |

`quality_flags` values must use stable lowercase snake_case flag codes. Flag codes must not contain the `|` delimiter. Viewers and downstream consumers must split `quality_flags` on `|` and perform exact token matching, not substring matching.

Initial quality flag codes:

| Flag code | Meaning |
| --- | --- |
| `missing_scientific_name` | Accepted record has no usable scientific name. |
| `missing_event_date` | Accepted record has neither a usable event date nor an event year. |
| `missing_coordinate_uncertainty` | Accepted record has no coordinate uncertainty value. |
| `invalid_coordinate_uncertainty` | Accepted record had a coordinate uncertainty value that could not be parsed as a finite float and was normalized to null. |
| `missing_geodetic_datum` | Accepted record has no geodetic datum value. |
| `invalid_event_year` | Accepted record had a source year value that could not be parsed as an integer and was normalized to null. |

Recommended optional source-preservation fields:

| Field | Type | Source |
| --- | --- | --- |
| `catalog_number` | string or null | Darwin Core `catalogNumber`. |
| `collection_code` | string or null | Darwin Core `collectionCode`. |
| `institution_code` | string or null | Darwin Core `institutionCode`. |
| `record_number` | string or null | Darwin Core `recordNumber`. |
| `organism_id` | string or null | Darwin Core `organismID`. |
| `gbif_id` | string or null | GBIF `gbifID` if present. |
| `obis_id` | string or null | OBIS identifier if present. |
| `raw_decimal_longitude` | string or null | Original longitude string. |
| `raw_decimal_latitude` | string or null | Original latitude string. |
| `raw_event_date` | string or null | Original event date string. |

Rows in `occurrences.parquet` should contain records accepted for geospatial output. Records rejected for missing or invalid coordinates belong in `reports/rejected_records.csv` when any rejected records exist.

## `data/occurrences.fgb`

`occurrences.fgb` is the FlatGeobuf representation of accepted occurrence points.

Default FlatGeobuf generation writes accepted normalized records in bounded
chunks into `data/occurrences.gpkg`, then creates indexed FlatGeobuf from that
GeoPackage through Pyogrio/GDAL with `SPATIAL_INDEX=YES`. The GeoPackage is
retained after conversion.

When both FlatGeobuf and GeoParquet are generated, FlatGeobuf should contain the same accepted records as `data/occurrences.parquet` unless `metadata/processing.json` documents a deliberate export filter.

Required behavior:

- Geometry type: point.
- Coordinate order: longitude, latitude.
- CRS assumption: `OGC:CRS84`.
- Use a compact normalized occurrence field set optimized for viewer and lightweight exchange, not the full source/raw Darwin Core field set.
- Include all required viewer display fields and accepted filter fields when present.
- Include stable source identifiers so viewer-selected features can be traced back to source rows.
- Write a spatial index by default.
- Emit a large dataset warning before indexed writes that may require substantial memory.
- Store `quality_flags` using the same nullable `|`-delimited string representation as GeoParquet.

Initial large indexed-write warning behavior:

- Warning code: `large_indexed_flatgeobuf_write`.
- Warn when indexed writes have `>= 1,000,000` accepted features or estimated
  spatial-index construction memory `>= 256 MiB`.
- Initial spatial-index memory estimate: `64` bytes per accepted feature.
- The warning is non-fatal and does not automatically change the writer option
  to `SPATIAL_INDEX=NO`; the default staged FlatGeobuf path keeps
  `SPATIAL_INDEX=YES`.
- For example, 5 million accepted features estimate about 320,000,000 bytes
  for spatial-index construction, so they should emit
  `large_indexed_flatgeobuf_write` before the writer attempts the indexed
  FlatGeobuf output.

Required FlatGeobuf projection columns:

| Column | Type | Source or meaning |
| --- | --- | --- |
| `source_record_id` | string | Stable project source row identifier. |
| `source_file` | string | Source archive file containing the row. |
| `source_row_number` | integer | Physical 1-based row number in the source data file, including skipped header rows. |
| `source_data_row_number` | integer or null | Logical 1-based data-record number after declared header rows, when available. |
| `occurrence_id` | string or null | Darwin Core `occurrenceID`. |
| `scientific_name` | string or null | Darwin Core `scientificName`. |
| `verbatim_scientific_name` | string or null | Darwin Core `verbatimScientificName`. |
| `kingdom` | string or null | Darwin Core `kingdom`. |
| `phylum` | string or null | Darwin Core `phylum`. |
| `class` | string or null | Darwin Core `class`. |
| `order` | string or null | Darwin Core `order`. |
| `family` | string or null | Darwin Core `family`. |
| `genus` | string or null | Darwin Core `genus`. |
| `taxon_rank` | string or null | Darwin Core `taxonRank`. |
| `basis_of_record` | string or null | Darwin Core `basisOfRecord`. |
| `degree_of_establishment` | string or null | Darwin Core `degreeOfEstablishment`. |
| `iucn_red_list_category` | string or null | IUCN Red List category when present in source data or accepted enrichment. Current source terms include `http://iucn.org/terms/iucnRedListCategory`, `http://rs.gbif.org/terms/1.0/iucnRedListCategory` and `http://rs.tdwg.org/dwc/terms/iucnRedListCategory`. |
| `event_date` | string or null | Darwin Core `eventDate`, normalized where possible. |
| `event_year` | integer or null | Year derived from `eventDate` or `year`. |
| `decimal_longitude` | double | Parsed longitude. |
| `decimal_latitude` | double | Parsed latitude. |
| `coordinate_uncertainty_in_meters` | double or null | Darwin Core `coordinateUncertaintyInMeters`. |
| `country_code` | string or null | Darwin Core `countryCode`. |
| `locality` | string or null | Darwin Core `locality`. |
| `identified_by` | string or null | Darwin Core `identifiedBy`. |
| `license` | string or null | Record or dataset license when available. |
| `references` | string or null | Darwin Core `references`. |
| `rights_holder` | string or null | Darwin Core `rightsHolder`. |
| `dataset_name` | string or null | Darwin Core `datasetName` or source metadata. |
| `quality_flags` | string or null | Quality flags assigned by the converter as `\|`-delimited tokens. Null when no flags are present. |
| `has_quality_flags` | boolean | True when `quality_flags` is not empty. |
| `geometry` | point geometry | Accepted occurrence point geometry in `OGC:CRS84`. |

Full source/raw Darwin Core core and extension table preservation belongs in future raw Parquet-family exports, not in the MVP FlatGeobuf layer.

## `data/occurrences.gpkg`

`occurrences.gpkg` is the persistent GeoPackage staging artifact used to build
`data/occurrences.fgb` when FlatGeobuf is generated. It must remain in the
bundle and be listed in `manifest.files` with role `geopackage`, media type
`application/geopackage+sqlite3`, byte size, SHA-256 and accepted record count.

The GeoPackage occurrence layer uses the same accepted compact projection as
FlatGeobuf, including point geometry in `OGC:CRS84`, longitude/latitude order,
`quality_flags` and `has_quality_flags`. Its accepted record set should match
the final FlatGeobuf output unless processing metadata records an explicit
export filter.

Processing metadata records whether staging was enabled, staging path,
GeoPackage writer backend, whether FlatGeobuf was generated from GeoPackage,
the GDAL/OGR helper strategy and FlatGeobuf spatial-index status.

The static viewer should not use `data/occurrences.gpkg` as the default map
layer under the MVP contract. It should continue to prefer
`data/occurrences.fgb` when FlatGeobuf exists.

The static viewer should prefer `data/occurrences.fgb` for MVP map display
when a FlatGeobuf layer is generated. Explicit GeoParquet-only bundles,
including GeoParquet large-output bundles, may omit FlatGeobuf and remain
valid output bundles; viewer contracts must define a graceful no-FlatGeobuf
state unless GeoParquet browser loading is accepted later.

## `reports/rejected_records.csv`

`rejected_records.csv` records source rows skipped or rejected by the converter. The file should be written only when at least one source row is skipped or rejected. If no records are rejected, the file should be absent and omitted from `manifest.files`.

Required columns:

| Column | Type | Description |
| --- | --- | --- |
| `source_file` | string | Source archive file containing the row. |
| `source_row_number` | integer | Physical 1-based row number in the source data file, including skipped header rows. |
| `source_record_id` | string or null | Project source row identifier if available. |
| `occurrence_id` | string or null | Darwin Core `occurrenceID` when available. |
| `scientific_name` | string or null | Darwin Core `scientificName` when available. |
| `decimal_longitude` | string or null | Raw longitude value. |
| `decimal_latitude` | string or null | Raw latitude value. |
| `event_date` | string or null | Raw event date value. |
| `reason_code` | string | Stable machine-readable rejection reason. |
| `reason_message` | string | Human-readable explanation. |

Recommended columns:

| Column | Type | Description |
| --- | --- | --- |
| `source_data_row_number` | integer or null | Logical 1-based data-record number after declared header rows, when available. |

Initial reason codes:

| Reason code | Meaning |
| --- | --- |
| `missing_coordinates` | Latitude or longitude is empty or absent. |
| `invalid_latitude` | Latitude cannot be parsed as a number. |
| `invalid_longitude` | Longitude cannot be parsed as a number. |
| `coordinate_out_of_range` | Latitude or longitude is outside valid ranges. |
| `zero_zero_coordinate` | Coordinate is exactly `0,0` and excluded by policy. |
| `missing_required_field` | Required field is absent or empty. |
| `row_parse_error` | Row cannot be parsed according to DwC-A metadata. |
| `type_conversion_failed` | Required type conversion failed. |

The converter may add more reason codes, but they must be documented in `metadata/processing.json`.

## Viewer-Required Files And Fields

The thin static viewer must be able to read `manifest.json`,
`metadata/source.json` and `metadata/processing.json`. For map display, it
should use `data/occurrences.fgb` when that layer is generated and declared
in `manifest.layers`. GeoParquet-only bundles are valid without
`data/occurrences.fgb`; the viewer should handle them without crashing and
show metadata/provenance plus the accepted no-map-layer state from
`docs/viewer_contract.md`.

The viewer must display these dataset/provenance fields when available:

| Field | Source |
| --- | --- |
| Dataset title | `manifest.title` or `metadata/source.json.dataset.title`. |
| Publisher | `metadata/source.json.dataset.publisher`. |
| DOI | `metadata/source.json.dataset.doi`, GBIF DOI or OBIS DOI. |
| Citation | `metadata/source.json.dataset.citation`, GBIF citation or OBIS citation. |
| License | `metadata/source.json.rights.license`, GBIF license or OBIS license. |
| GBIF dataset key | `metadata/source.json.gbif.dataset_key`. |
| GBIF download key | `metadata/source.json.gbif.download_key`. |
| OBIS dataset id | `metadata/source.json.obis.dataset_id`. |
| Generated timestamp | `manifest.created_at`. |
| Converter version | `manifest.generator.version`. |
| Accepted/rejected counts | `manifest.counts` and `metadata/processing.json.counts`. |

The viewer must be able to show these feature fields in popups or a details panel:

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

The current viewer also derives a display-only `source record URL` row from
`source_record_id` when available, using
`https://www.gbif.org/occurrence/{source_record_id}`. This derived link is not
a generated occurrence column and is not required in FlatGeobuf or
GeoParquet schemas.

Map styling is viewer behavior, not output schema: the current viewer colors
points by `kingdom` where available, uses a high-contrast fallback for missing
or unknown kingdoms, and highlights the selected feature on the map.

The viewer must support filters for these fields when present:

| Field | Filter type |
| --- | --- |
| `scientific_name` | text contains search |
| `kingdom` | categorical |
| `event_year` | numeric range or discrete values |
| `basis_of_record` | categorical |
| `iucn_red_list_category` | categorical |
| `quality_flags` | show/hide records with flags; split on `\|` and use exact-token matching for flag-code filters |

DOI rows should render as `https://doi.org/{doi}` links when the source value
is either a bare DOI or a DOI URL. DOI URLs embedded inside citation text
should render as active external links while preserving the surrounding
citation text.

The viewer must omit absent generated-bundle fields from the filter UI without error. Missing DOI, citation, GBIF or OBIS metadata should be shown as absent, not as errors.

## Validation Rules

Bundle validation should check:

- `manifest.json` exists and has supported schema versions.
- Every `manifest.files[].path` exists.
- Checksums match when `sha256` is present.
- `metadata/source.json` and `metadata/processing.json` exist and parse as JSON.
- `data/occurrences.parquet` opens as Parquet and has GeoParquet metadata when declared in `manifest.files`.
- `data/occurrences.gpkg` exists when declared, opens as SQLite/GeoPackage,
  has required GeoPackage metadata tables when checkable and includes the
  occurrence projection columns.
- GeoParquet geometry column is `geometry` when GeoParquet is generated.
- Generated occurrence fields use the normalized snake_case project field names documented by the canonical occurrence schema and do not expose source camelCase terms as normalized output columns.
- Required projection columns are present for each generated occurrence output format.
- Geometry CRS and coordinate order are documented for every generated geospatial output.
- `data/occurrences.fgb` exists when declared in `manifest.layers`.
- Row counts reconcile across manifest, processing metadata, generated geospatial outputs, GeoPackage staging and rejected report when present.
- `reports/rejected_records.csv` has the required columns when rejected records exist.
- Viewer-required fields are either present in the data or omitted from `manifest.viewer.display_fields` and `manifest.viewer.filter_fields`.
- `quality_flags` is nullable string data when present, uses `|` as its delimiter, and does not contain flag codes with the delimiter.

The implemented core validation API is
`dwca_cloud_geospatial.validation.validate_output_bundle`. It returns a
`BundleValidationResult` with status `passed`, `passed_with_warnings` or
`failed`, required failures in `errors`, dependency-dependent optional-reader
warnings/skips in `warnings` and per-check details in `checks`. CLI and GUI
surfaces should consume this result object rather than duplicating validation
logic.

GeoParquet validation is layered:

- Required checks use PyArrow. A declared GeoParquet file must open as Parquet,
  expose required projection columns, reconcile row counts, include
  GeoParquet `geo` metadata, declare the expected geometry column, geometry
  type, encoding and CRS, and preserve `quality_flags` /
  `has_quality_flags` consistency. When a `bbox` column is present, PyArrow
  validation checks the struct schema, GeoParquet covering declaration and
  point bbox values.
- Optional GeoParquet-aware checks should run when tools are installed:
  `geoparquet-io` for spec-aware validation, DuckDB for analytical reader and
  row-group/metadata checks, and Pyogrio/GDAL as a best-effort geospatial
  reader check.
- Missing optional validation tools or unavailable local GDAL Parquet support
  should be reported as warnings or skipped checks, not as bundle failures,
  when required PyArrow validation passes.
- Large-output validation checks covering bbox schema/content when present.
  Spatial sorting is recorded in processing metadata. Partitioned-output
  validation remains deferred because partitioned output is not implemented.

Current validator scope and limitations:

- Implemented GeoParquet validation covers the single-file output
  `data/occurrences.parquet`.
- Partitioned GeoParquet dataset validation is deferred until partitioned
  output is implemented.
- FlatGeobuf inspection is dependency-dependent through Pyogrio/GDAL. When
  readable, validation checks projection fields, point geometry and feature
  counts. Row-level FlatGeobuf `quality_flags` validation depends on local
  geospatial table reader support.

## Compatibility Notes

This MVP contract intentionally excludes PMTiles. PMTiles remains an intended MVP+ output and should be added by extending `manifest.layers` and `manifest.files`, not by changing the GeoParquet or FlatGeobuf contract.

The bundle must remain useful for non-GBIF and non-OBIS DwC-A archives. GBIF, OBIS and IUCN-sourced fields are preserved when available, but they are nullable and not required for successful conversion.
