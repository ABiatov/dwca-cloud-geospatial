# Prompt 04: Occurrence Normalization

Date: 2026-06-09

## Scope

Implemented occurrence normalization from Prompt 03 `OccurrenceSourceRecord`
values into accepted normalized occurrence records and rejected occurrence
records. This prompt did not write FlatGeobuf, GeoParquet, manifest, metadata
or rejected CSV files, and did not add taxonomy matching or enrichment.

## Normalized Schema/Model Summary

- Added `dwca_cloud_geospatial.normalization.normalize_occurrence_records`.
- Added `normalize_occurrence_record` for single-record normalization.
- Added `OccurrenceNormalizationResult` with `accepted_records`,
  `rejected_records` and `counts`.
- Added `OccurrenceNormalizationCounts` with `source_records`,
  `parsed_records`, `accepted_records` and `rejected_records`.
- Added `NormalizedOccurrenceRecord` using project-owned snake_case field
  names aligned with `docs/output_format.md`.
- Exported the normalization API from `dwca_cloud_geospatial.__init__`.

Accepted records include required provenance fields:

- `source_record_id`
- `source_file`
- `source_row_number`
- `source_data_row_number`

Accepted records also include parsed numeric `decimal_longitude` and
`decimal_latitude`, raw coordinate strings, normalized/derived event fields,
nullable dataset/GBIF/OBIS fields when present in records, and placeholder
quality fields with `quality_flags = None` and `has_quality_flags = False`.

Python reserves `class`, so the dataclass attribute is `class_`. Its
`to_dict()` method exports the output field as `class`.

## Rejection Model Summary

Added `RejectedOccurrenceRecord`, aligned with the required
`reports/rejected_records.csv` columns:

- `source_file`
- `source_row_number`
- `source_record_id`
- `occurrence_id`
- `scientific_name`
- `decimal_longitude`
- `decimal_latitude`
- `event_date`
- `reason_code`
- `reason_message`
- `source_data_row_number`

Implemented coordinate rejection reason codes:

- `missing_coordinates`
- `invalid_latitude`
- `invalid_longitude`
- `coordinate_out_of_range`
- `zero_zero_coordinate`

The model also preserves documented placeholder reason codes for later
conversion/reporting stages:

- `missing_required_field`
- `row_parse_error`
- `type_conversion_failed`

## Mapping Decisions

- Normalization consumes source values through
  `OccurrenceSourceRecord.value_for_term(term)`.
- Darwin Core, Dublin Core, GBIF and OBIS terms are mapped centrally in
  `NORMALIZED_FIELD_TERMS`.
- Source camelCase terms are not exposed as normalized output fields.
- `source_record_id` uses the parser-provided source identifier when present,
  then `occurrence_id`, then a stable `source_file:source_row_number`
  fallback for accepted records.
- `event_date` is normalized for practical ISO-style single values:
  `YYYY`, `YYYY-MM`, `YYYY-MM-DD` and ISO datetimes.
- `event_year` is derived from normalized `event_date` or Darwin Core `year`
  when practical.
- `coordinate_uncertainty_in_meters` is parsed as an optional float; failed
  optional conversion currently becomes null. Prompt 05 owns warning/failure
  accounting for optional-field conversion failures.

## Deviations From `docs/output_format.md`

- No output files are written in this prompt, so FlatGeobuf/GeoParquet
  projection enforcement remains for writer prompts.
- `quality_flags` and `has_quality_flags` are present on accepted records, but
  quality flag assignment remains Prompt 05 work.
- Full processing metadata and type-conversion failure arrays remain Prompt 05
  and Prompt 08 work.

## Fixtures And Tests

Added normalization fixture archive:

- `tests/fixtures/dwca/minimal_occurrence/normalization/meta.xml`
- `tests/fixtures/dwca/minimal_occurrence/normalization/metadata.xml`
- `tests/fixtures/dwca/minimal_occurrence/normalization/occurrence.txt`

Added `tests/test_occurrence_normalization.py` covering:

- accepted record field mapping and provenance preservation;
- coordinate parsing into numeric longitude/latitude;
- event date normalization and event year derivation;
- rejected records and stable coordinate reason codes;
- accepted/rejected/source count reconciliation.

## Documentation Updates

- Updated `docs/dwca_parser.md` with the normalization API handoff and reason
  codes.
- Updated `docs/development_plan.md` so immediate next actions start with
  quality rules instead of already-completed normalization.
- Updated `docs/knowledge_base/topics/dwca_archive_parsing.md`,
  `docs/knowledge_base/topics/validation_and_quality.md`,
  `docs/knowledge_base/topics/dwca_to_parquet_patterns.md`,
  `docs/knowledge_base/topics/flatgeobuf_output.md`,
  `docs/knowledge_base/topics/geoparquet_output.md`,
  `docs/knowledge_base/playbooks/implement_geoparquet_writer.md` and
  `docs/knowledge_base/playbooks/validate_output_bundle.md` so agent-facing
  documentation starts later writer/validator work from Prompt 04 normalized
  records and treats coordinate failure codes as rejection reason codes, not
  accepted-record quality flags.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`.

- `.venv/bin/python -m pytest tests/test_occurrence_normalization.py`
  - Result: passed, `3 passed`.
- `.venv/bin/python -m pytest tests`
  - Result: passed, `18 passed`.

## Open Questions Or Risks

- Prompt 05 still needs type-conversion failure accounting for optional fields
  such as `coordinate_uncertainty_in_meters`.
- Prompt 05 should preserve the Prompt 04 `zero_zero_coordinate` rejection
  behavior while adding quality flags and warning structures.
- Multi-file occurrence-core streaming remains deferred.
- EML/source metadata extraction remains deferred to Prompt 08.

## Prompt Updates

- Updated `.codex/prompts/05_quality_rules.md`.
- Updated `.codex/prompts/06_flatgeobuf_writer.md`.
- Updated `.codex/prompts/07_geoparquet_writer.md`.
- Updated `.codex/prompts/08_manifest_metadata_writers.md`.
- Updated `.codex/prompts/09_bundle_validation.md`.
- Updated `.codex/prompts/10_core_api_cli.md`.
- Updated `.codex/prompts/11_viewer_contract.md`.
- Updated `.codex/prompts/12_static_viewer.md`.
- Updated `.codex/prompts/13_tkinter_gui.md`.
- Updated `.codex/prompts/14_demo_docs_hardening.md`.
- Updated `.codex/prompts/dev_flow_description.md` to set
  `05_quality_rules.md` as the current next work item.
