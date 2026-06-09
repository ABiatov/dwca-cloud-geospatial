---
id: flatgeobuf-output
status: candidate
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

FlatGeobuf is a candidate lightweight vector exchange and browser-accessible geospatial output. It is more viewer-friendly than analytical Parquet for some clients because it is streamable and supports HTTP range request access patterns.

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

## Candidate Output Role

Candidate or future output roles:

- GeoParquet can be the analytical table.
- FlatGeobuf can be an exchange or viewer data layer.
- PMTiles can be the optimized map tile layer for larger browser maps in MVP+.

Accepted MVP override: FlatGeobuf is the default viewer/exchange output, not optional, unless the user explicitly selects a different documented output mode.

## Resolved By Accepted Docs

- FlatGeobuf is the default MVP output when the user does not choose an explicit conversion format. `docs/development_plan.md` and `docs/output_format.md` both record `exports/occurrences.fgb` as the default output.
- FlatGeobuf should contain accepted records with non-null point geometry, not rejected or null-geometry rows. Rejected or skipped rows are represented through diagnostics/reports, especially conditional `reports/rejected_records.csv`.
- FlatGeobuf must include the viewer-required fields and MVP filter fields when those fields are present in the generated bundle, per `docs/development_plan.md` M3 and M5.
- FlatGeobuf should use a compact normalized occurrence field set optimized for viewer and lightweight exchange, not the full source/raw Darwin Core field set. It must include geometry, required provenance fields, accepted viewer display fields, accepted filter fields when present, coordinates and quality flags. Full raw/core/extension table preservation belongs in future raw Parquet-family exports, not in the MVP FlatGeobuf layer.
- FlatGeobuf writing should start from accepted `NormalizedOccurrenceRecord`
  values produced by Prompt 04 normalization. Use `to_dict()` or an equivalent
  explicit projection so Python attribute `class_` is emitted as output column
  `class`.
- Additional Darwin Core fields required in FlatGeobuf beyond the previously accepted viewer fields are: `license`, `references`, `rightsHolder`, `identifiedBy`, `scientificName`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `taxonRank`, `verbatimScientificName`, `coordinateUncertaintyInMeters` and `degreeOfEstablishment`. The generated column names should follow the normalized occurrence schema naming used by the output contract.

## Open Questions

- None currently.
