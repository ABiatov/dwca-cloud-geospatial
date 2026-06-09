# Prompt 05: Quality Rules

Date: 2026-06-09

## Scope

Implemented MVP quality-rule behavior on top of Prompt 04 occurrence
normalization. This prompt did not write FlatGeobuf, GeoParquet, manifest,
metadata, rejected CSV or final bundle files.

## Quality Flag Codes Added

Accepted records now serialize `quality_flags` as nullable `|`-delimited
strings. Records without flags store `quality_flags = None` and
`has_quality_flags = False`. Flag codes are stable lowercase snake_case tokens
and are validated to exclude the `|` delimiter.

Initial quality flag codes:

- `missing_scientific_name`
- `missing_event_date`
- `missing_coordinate_uncertainty`
- `invalid_coordinate_uncertainty`
- `missing_geodetic_datum`
- `invalid_event_year`

Tests assert exact token lists after splitting on `|`, including a negative
substring check for `missing_event`.

## Type Conversion Failure Policy Implemented

Added normalization result structures:

- `TypeConversionFailure`
- `OccurrenceNormalizationWarning`
- `OccurrenceNormalizationResult.type_conversion_failures`
- `OccurrenceNormalizationResult.warnings`
- `OccurrenceNormalizationCounts.warning_count`

Conversion failures are counted by `field`, `reason_code` and `action`.

Implemented actions:

- `null_value`
- `record_rejected`
- `conversion_failed` is reserved for later conversion-level failures.

Implemented optional conversion behavior:

- `coordinate_uncertainty_in_meters` invalid float values become null and are
  counted with `invalid_float`.
- `event_year` invalid integer values become null and are counted with
  `invalid_integer`.
- Optional conversion failure warnings are emitted when a field failure rate is
  `>= 5%` of parsed records, using warning code
  `optional_conversion_failure_rate`.

Implemented critical behavior:

- Coordinate failures still reject affected records.
- Required provenance failures for unusable `source_file` or
  `source_row_number` reject affected records with `missing_required_field`.
- Missing source IDs alone are not rejected because the Prompt 04 fallback
  `source_file:source_row_number` still produces required `source_record_id`
  when source provenance is usable.

Conversion-level failure policy remains documented for the future core
conversion workflow: fail only when no accepted records remain, required
provenance cannot be produced, or parser/metadata structure prevents reliable
row interpretation. Optional conversion warnings do not fail normalization.

## New Rejection Reason Codes

No new rejected-record reason codes were added.

Prompt 04 coordinate reason codes were preserved:

- `missing_coordinates`
- `invalid_latitude`
- `invalid_longitude`
- `coordinate_out_of_range`
- `zero_zero_coordinate`

The existing `missing_required_field` reason code is now actively used for
critical provenance rejection.

New type-conversion failure reason codes:

- `invalid_float`
- `invalid_integer`

These are processing metadata reason codes, not rejected-record reason codes
unless a later critical field uses them with `record_rejected`.

## Fixtures And Tests

Added quality-rule fixture files under the existing Prompt 01 fixture root:

- `tests/fixtures/dwca/minimal_occurrence/quality_rules/meta.xml`
- `tests/fixtures/dwca/minimal_occurrence/quality_rules/metadata.xml`
- `tests/fixtures/dwca/minimal_occurrence/quality_rules/occurrence.txt`

Updated `tests/test_occurrence_normalization.py` to cover:

- nullable `quality_flags` and `has_quality_flags`;
- exact quality flag token behavior;
- optional conversion failure counts and `>= 5%` warning threshold;
- coordinate rejection failure accounting;
- critical provenance rejection semantics;
- warning count reconciliation.

## Documentation Updates

- Updated `docs/output_format.md` with `warning_count`,
  `type_conversion_failures`, warning fields, initial quality flags, initial
  conversion failure reason codes and FlatGeobuf `has_quality_flags`.
- Updated `docs/dwca_parser.md` with the Prompt 05 normalization result
  additions, quality flags, conversion failures and active
  `missing_required_field` rejection behavior.
- Updated `docs/development_plan.md` with initial quality flag codes and moved
  immediate next work to writer/metadata/validation stages.
- Updated `docs/knowledge_base/topics/validation_and_quality.md` and
  `docs/knowledge_base/playbooks/validate_output_bundle.md` so agent-facing
  validation guidance reflects Prompt 05.
- Follow-up documentation consistency pass also updated
  `docs/knowledge_base/topics/flatgeobuf_output.md`,
  `docs/knowledge_base/topics/geoparquet_output.md`,
  `docs/knowledge_base/topics/dwca_to_parquet_patterns.md`,
  `docs/knowledge_base/playbooks/implement_geoparquet_writer.md` and
  `docs/knowledge_base/playbooks/add_static_viewer_output.md` so writer and
  viewer guidance preserves `quality_flags`, `has_quality_flags` and Prompt 05
  normalization result boundaries.

## Verification Commands And Results

Verification used the documented in-repository `.venv/` workflow from
`docs/developer_setup.md`.

- `.venv/bin/python -m pytest tests/test_occurrence_normalization.py`
  - Result: passed, `6 passed`.
- `.venv/bin/python -m pytest tests`
  - Result: passed, `21 passed`.

## Open Questions Or Risks

These are handoff notes for later prompts, not blockers before Prompt 06.

- Conversion-level fatal handling still belongs to the future core conversion
  API; Prompt 05 records the policy and exposes enough normalization result
  structure for that API.
- Future output writers must preserve `quality_flags` as nullable text and
  include `has_quality_flags` where required by the output projection.

## Prompt Updates

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
  `06_flatgeobuf_writer.md` as the current next work item.
