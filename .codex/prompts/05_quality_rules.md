# Prompt 05: Quality Rules

## Required Skills

- `geospatial-pipeline`: coordinate quality rules, quality flags and conversion failure policy.
- `data-package-spec`: output-schema implications for `quality_flags`, rejected records and processing metadata.
- `planning-artifact-curator`: record decisions and downstream prompt updates.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `docs/developer_setup.md`
- `docs/dwca_parser.md` if it exists.
- Prompts `01` through `04`
- Latest session logs for prompts `01` through `04`
- Current normalization and rejected-record tests.

## Goal

Complete MVP quality behavior: stable `quality_flags`, type conversion failure accounting, and rejected/skipped record handling.

## Tasks

- Implement quality flag assignment with lowercase snake_case tokens that never contain `|`.
- Reuse existing test fixture roots from Prompt 01; add quality-rule fixtures
  under `tests/fixtures/` only with explicit paths.
- Represent `quality_flags` as nullable `|`-delimited string; no flags must be null.
- Add `has_quality_flags` where the output schema requires it.
- Implement `0,0` coordinate policy from `docs/output_format.md` and current decisions.
- Count type conversion failures by field and reason.
- Apply optional-field conversion failure behavior: set normalized value to null and warn when field failure rate is `>= 5%` of parsed records.
- Apply critical-field conversion behavior: reject affected records for coordinate and required provenance failures.
- Ensure conversion fails only when no accepted records remain, required provenance cannot be produced, or parser/metadata structure prevents reliable row interpretation.
- Add tests for quality flags, failure counts, warning thresholds and rejected-record semantics.

## Constraints

- Do not write final bundle files yet unless the current architecture already has a narrow report writer required by tests.
- Keep reason codes stable and document any additions.

## Acceptance Criteria

- `quality_flags` matches the accepted nullable string representation.
- Optional and critical conversion failures are counted with stable reason codes.
- Accepted, rejected and warning counts reconcile.
- Tests demonstrate exact-token quality flag behavior rather than substring matching.

## Required Session Log

Write `session_logs/YYYY-MM-DD_05_quality_rules.md` with:

- Quality flag codes added.
- Type conversion failure policy implemented.
- Any new rejection reason codes.
- Verification commands and results.
- Confirmation that verification used the documented `.venv/` workflow or a
  documented equivalent.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `06` through `14` if quality flag storage, reason codes, warning structures, failure-count structures or conversion result objects changed.
