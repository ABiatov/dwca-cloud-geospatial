---
id: flatgeobuf-output
status: accepted
applies_to:
  - geospatial conversion
  - FlatGeobuf outputs
  - static viewer contract
sources:
  - examples/code/cloud-optimized-geospatial-formats-guide/flatgeobuf/
  - examples/code/cloud-optimized-geospatial-formats-guide/overview.qmd
---

# FlatGeobuf Output

## Use In This Project

FlatGeobuf is the accepted MVP lightweight vector exchange and browser-accessible geospatial output. It is more viewer-friendly than analytical Parquet for some clients because it is streamable and supports HTTP range request access patterns.

## Fit

Use FlatGeobuf when the project needs:

- a single vector file that can be loaded by GIS tools;
- static-hosted vector access without a database;
- spatial index support for remote partial reads;
- a simpler web-viewer data source than raw GeoParquet.

## Tradeoffs

- FlatGeobuf is row-oriented and streamable.
- It is not compressed in the same way as Parquet because random reads are part of the design.
- It complements GeoParquet rather than replacing it.
- It is likely a better exchange/viewer artifact than a primary analytical artifact.

## Output Role

Accepted and planned output roles:

- GeoParquet can be the analytical table.
- FlatGeobuf can be an exchange or viewer data layer.
- PMTiles can be the optimized map tile layer for larger browser maps in MVP+.

Accepted MVP override: FlatGeobuf is the default viewer/exchange output when
the user does not choose another format. It is omitted from explicit
GeoParquet-only bundles, including GeoParquet large-output bundles.

## Resolved By Accepted Docs

- FlatGeobuf is the default MVP output when the user does not choose an explicit conversion format. `docs/development_plan.md` and `docs/output_format.md` both record `exports/occurrences.fgb` as the default output.
- FlatGeobuf should contain accepted records with non-null point geometry, not rejected or null-geometry rows. Rejected or skipped rows are represented through diagnostics/reports, especially conditional `reports/rejected_records.csv`.
- FlatGeobuf must include the viewer-required fields and MVP filter fields when those fields are present in the generated bundle, per `docs/development_plan.md` M3 and M5.
- FlatGeobuf should use a compact normalized occurrence field set optimized for viewer and lightweight exchange, not the full source/raw Darwin Core field set. It must include geometry, required provenance fields, accepted viewer display fields, accepted filter fields when present, coordinates, nullable `quality_flags` and `has_quality_flags`. Full raw/core/extension table preservation belongs in future raw Parquet-family exports, not in the MVP FlatGeobuf layer.
- FlatGeobuf writing should start from accepted `NormalizedOccurrenceRecord`
  values produced by normalization after Prompt 05 quality rules. Use
  `to_dict()` or an equivalent explicit projection so Python attribute
  `class_` is emitted as output column `class`.
- Additional Darwin Core fields required in FlatGeobuf beyond the previously accepted viewer fields are: `license`, `references`, `rightsHolder`, `identifiedBy`, `scientificName`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `taxonRank`, `verbatimScientificName`, `coordinateUncertaintyInMeters` and `degreeOfEstablishment`. The generated column names should follow the normalized occurrence schema naming used by the output contract.

## Implemented Prompt 06 Writer

- Writer API:
  `dwca_cloud_geospatial.flatgeobuf.write_flatgeobuf_occurrences`.
- Output path: `exports/occurrences.fgb`.
- Production backend: Pyogrio/GDAL through PyArrow; do not use GeoPandas for
  the production writer path.
- Development dependency extra: install with
  `python -m pip install -e "${REPO}[dev,flatgeobuf]"`.
- Verified local stack after Prompt 06 follow-up: Pyogrio `0.12.1`, GDAL
  `3.11.4` as reported by Pyogrio, PyArrow `24.0.0`, and FlatGeobuf driver
  support `rw`.
- Dependency behavior: if Pyogrio/PyArrow/GDAL support is unavailable, the
  writer raises `FlatGeobufDependencyError`; tests can still validate
  projection and guardrails through the isolated backend seam.
- Prompt 06 verification evidence: `tests/test_flatgeobuf_writer.py` passed
  with `6 passed` when the optional writer stack was installed, and the then
  current full suite passed with `27 passed`.

## Spatial Index And Large Outputs

- Prompt 06 requests `SPATIAL_INDEX=YES` by default.
- `FlatGeobufWriterOptions(spatial_index=False)` requests
  `SPATIAL_INDEX=NO` and suppresses spatial-index memory warnings.
- Prompt 10 exposes FlatGeobuf writer options through the public core
  conversion API:
  `ConversionOptions(flatgeobuf=FlatGeobufWriterOptions(...))`. The MVP CLI
  does not expose a `SPATIAL_INDEX=NO` flag yet, so CLI default conversion
  keeps indexed FlatGeobuf writes.
- Initial warning code: `large_indexed_flatgeobuf_write`.
- Initial warning thresholds: indexed writes at `>= 1,000,000` accepted
  features or estimated spatial-index memory `>= 256 MiB`.
- Initial estimate: `64` bytes per accepted feature for spatial-index
  construction.
- Large-output warnings are non-fatal. The writer warns before the backend
  write but still attempts the indexed write unless conversion options
  explicitly disable the index.
- Core conversion preserves these writer warnings in
  `metadata/processing.json.warnings` with `stage="flatgeobuf_writer"`.
- Example: 5 million accepted features estimate about 320,000,000 bytes for
  spatial-index construction, so the writer emits
  `large_indexed_flatgeobuf_write` and still attempts the indexed write by
  default.

## Current Large-Data Limitation

Prompt 06 does not yet provide a fully streaming large-data pipeline. The
current parser, normalizer and FlatGeobuf writer materialize full record sets
in memory. Very large DwC-A inputs may take a long time, consume substantial
memory or fail until chunked parser/normalizer/writer handoff is implemented.

## Open Questions

- Whether to expose `SPATIAL_INDEX=NO` as an MVP CLI flag remains deferred.
  The core API can already request it through `FlatGeobufWriterOptions`.
