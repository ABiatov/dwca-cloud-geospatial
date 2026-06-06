# Prompt 02: DwC-A Inspection

## Required Skills

- `dwca-archive-parser`: safe Darwin Core Archive handling, `meta.xml`, core/extension files and diagnostics.
- `planning-artifact-curator`: record decisions, evidence and prompt handoff.

## Context To Read First

- `README.md`
- `.codex/AGENTS.md`
- `docs/development_plan.md`
- `docs/output_format.md`
- `.codex/prompts/dev_flow_description.md`
- `.codex/prompts/01_project_skeleton.md`
- Latest `session_logs/*01_project_skeleton*.md`
- Current package, CLI and test files created by Prompt 01.
- `examples/README.md` and the inventory of `examples/dwca/`.

## Goal

Implement safe inspection of local Darwin Core Archives and parse `meta.xml` into structured archive metadata.

## Tasks

- Support both `.zip` archives and unpacked DwC-A directories.
- Inspect archives safely without path traversal vulnerabilities.
- Locate and parse `meta.xml`.
- Model core file, extension files, row types, declared files, field terms, field indexes, delimiters, headers and defaults.
- Detect whether an occurrence core is present.
- Report coordinate-field presence.
- Add parser diagnostics for missing files, malformed metadata and unsupported structures.
- Add a lightweight CLI inspection command if the CLI stub already supports subcommands; otherwise add the core inspection API and update Prompt 10 to wire the CLI.
- Draft or update `docs/dwca_parser.md` with accepted inspection behavior.

## Constraints

- Do not perform full row normalization or geospatial conversion.
- Do not hard-code source columns outside the parsed schema model.
- Do not extract archives unsafely into the repository.

## Acceptance Criteria

- Local sample archives in `examples/dwca/` can be inspected.
- Field access is based on declared DwC-A terms and indexes.
- Parser errors include source file or metadata context.
- Tests cover at least one valid archive and one malformed or missing metadata case.

## Required Session Log

Write `session_logs/YYYY-MM-DD_02_dwca_inspection.md` with:

- Inspection API and data model summary.
- Sample archives tested.
- Diagnostics behavior.
- Verification commands and results.
- `Prompt Updates`: list later prompt files changed, or `None`.

## Prompt Maintenance

Update prompts `03`, `10` and `14` if inspection API names, model names, docs paths, CLI command names or sample fixture locations changed.
