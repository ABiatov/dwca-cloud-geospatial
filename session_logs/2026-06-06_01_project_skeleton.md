# Prompt 01: Project Skeleton

Date: 2026-06-06

## Scope

Created the minimal Python project skeleton for the MVP implementation. No
Darwin Core Archive parsing, normalization, geospatial writers, viewer, GUI,
GBIF/OBIS integration, taxonomy matching, PMTiles generation, database,
backend service or cloud runtime behavior was added.

## Files Created Or Updated

- Created `pyproject.toml` with setuptools packaging, `src/` layout, dev test
  extra, pytest configuration and console script entry point.
- Created `src/dwca_cloud_geospatial/__init__.py`.
- Created `src/dwca_cloud_geospatial/__main__.py`.
- Created `src/dwca_cloud_geospatial/cli.py`.
- Created `tests/conftest.py`.
- Created `tests/test_cli.py`.
- Created `tests/test_fixture_paths.py`.
- Created `tests/fixtures/README.md`.
- Created `tests/fixtures/dwca/minimal_occurrence/README.md`.
- Created `tests/fixtures/output_bundles/README.md`.
- Created `docs/developer_setup.md`.
- Updated `README.md` with minimal development commands.
- Updated `README.md` and `docs/developer_setup.md` after setup verification
  to state that development should use the in-repository `.venv/`.
- Updated `.codex/prompts/dev_flow_description.md` so future prompt sessions
  prefer the documented `.venv/` for Python development and verification.
- Updated prompts `02` through `04` to explicitly reference
  `docs/developer_setup.md`, the Prompt 01 package/CLI/test artifacts,
  `.venv/` verification expectations and fixture path contracts where
  relevant.
- Updated prompts `05` through `14` to explicitly reference
  `docs/developer_setup.md`, `.venv/` verification expectations, existing
  CLI/package contracts and fixture roots where relevant.
- Updated `.gitignore` with Python generated-artifact ignores.
- Created `session_logs/2026-06-06_01_project_skeleton.md`.

## Package And CLI Decisions

- Distribution package name: `dwca-cloud-geospatial`.
- Import package namespace: `dwca_cloud_geospatial`.
- Packaging layout: conservative modern `src/` layout with setuptools via
  `pyproject.toml`.
- Required runtime dependencies: none for the skeleton.
- Development extra: `pytest>=8`.
- Development environment preference: use `${REPO}/.venv/`; do not install
  project development dependencies into Conda `base` or system Python unless
  intentionally using a separate disposable environment.
- CLI framework: Python standard-library `argparse`.
- Console command: `dwca-cloud-geospatial`.
- Module entry point: `python -m dwca_cloud_geospatial`.
- Stub commands exposed for planned MVP workflows: `inspect`, `convert` and
  `validate`.
- Stub command behavior: command-specific help is available; invoking planned
  workflow commands exits with code `2` and a clear not-implemented error.

## Fixture Decisions

- Test fixture root: `tests/fixtures/`.
- Initial DwC-A fixture path contract:
  `tests/fixtures/dwca/minimal_occurrence/`.
- Initial output bundle fixture path contract:
  `tests/fixtures/output_bundles/`.
- Tests derive fixture paths from absolute `pathlib.Path` constants in
  `tests/conftest.py` instead of the process working directory.

## Verification Commands And Results

- `PYTHONPATH=/Users/Alevtina/Documents/GitHub/dwca-cloud-geospatial/src python -m dwca_cloud_geospatial --help`
  succeeded and displayed top-level CLI help.
- Initial `python -m pytest` failed because `pytest` was not installed in the
  active Python environment.
- `python -m pip install -e '.[dev]'` initially failed under restricted network
  access while resolving build dependencies.
- Retried `python -m pip install -e '.[dev]'` with approved package/network
  access in the initially active Miniconda environment; installation
  succeeded, but this was later corrected to use `.venv/`.
- Initial CLI and test checks in the active environment succeeded before the
  environment correction: `dwca-cloud-geospatial --help`,
  `python -m dwca_cloud_geospatial --help`, `python -m pytest` with
  `5 passed`, and
  `dwca-cloud-geospatial inspect /explicit/path/to/archive.zip` exiting with
  code `2` and the expected not-implemented error.
- Follow-up environment correction: removed `dwca-cloud-geospatial`, `pytest`
  and `iniconfig` from Miniconda `base`; created `${REPO}/.venv/`; installed
  `.[dev]` into `.venv/`; verified `base` no longer reports those packages,
  `.venv/bin/python -m pytest` succeeds with `5 passed`, and
  `.venv/bin/dwca-cloud-geospatial --help` displays top-level CLI help.

## Resolved Follow-Up

- The initial dependency installation accidentally targeted Miniconda `base`.
  This was corrected by uninstalling `dwca-cloud-geospatial`, `pytest` and
  `iniconfig` from `base`, creating `${REPO}/.venv/`, installing `.[dev]`
  into `.venv/`, and documenting `.venv/` as the preferred development
  environment in `README.md` and `docs/developer_setup.md`.

## Open Questions Or Risks

- None for Prompt 01.

## Handoff Notes

- CLI command names are now established for later prompts: `inspect`,
  `convert` and `validate`. Command behavior remains intentionally
  unimplemented until later MVP milestones.
- The fixture directories currently contain marker README files only. Parser
  and bundle prompts should add minimal fixture data without changing these
  path contracts.

## Prompt Updates

- Updated `.codex/prompts/dev_flow_description.md` with the `.venv/`
  development-environment preference for future prompt sessions and marked
  the prompt flow as active.
- Updated `.codex/prompts/02_dwca_inspection.md`,
  `.codex/prompts/03_occurrence_parser.md` and
  `.codex/prompts/04_occurrence_normalization.md` so early implementation
  prompts carry the Prompt 01 setup, CLI and fixture contracts explicitly.
- Updated `.codex/prompts/05_quality_rules.md` through
  `.codex/prompts/14_demo_docs_hardening.md` so later implementation prompts
  also carry the Prompt 01 setup, `.venv/`, CLI/package and fixture contracts
  where relevant.
