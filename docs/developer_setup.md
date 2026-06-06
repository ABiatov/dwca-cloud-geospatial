# Developer Setup

Status: Initial project skeleton

## Paths

Use an explicit repository path in commands instead of relying on the current
working directory:

```bash
export REPO="/Users/Alevtina/Documents/GitHub/dwca-cloud-geospatial"
```

If the repository is checked out somewhere else, set `REPO` to that absolute
path.

## Local Installation

Preferred development setup: create and activate an in-repository virtual
environment at `${REPO}/.venv`.

Do not install this project's development dependencies into Conda `base` or
the system Python unless you are intentionally using a separate disposable
environment. Keeping dependencies in `.venv/` makes the project reproducible
and avoids changing global interpreter state.

```bash
python -m venv "${REPO}/.venv"
source "${REPO}/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e "${REPO}[dev]"
```

The package uses a `src/` layout with import package
`dwca_cloud_geospatial` and console script `dwca-cloud-geospatial`.

After activation, `python`, `pip`, `pytest` and `dwca-cloud-geospatial` should
resolve inside `${REPO}/.venv/`.

## Tests

Run the test suite with:

```bash
python -m pytest "${REPO}/tests"
```

Without activating the environment, use the explicit interpreter path:

```bash
"${REPO}/.venv/bin/python" -m pytest "${REPO}/tests"
```

The fixture path contract starts at:

```text
${REPO}/tests/fixtures/
${REPO}/tests/fixtures/dwca/minimal_occurrence/
${REPO}/tests/fixtures/output_bundles/
```

Tests should derive fixture locations from `tests/conftest.py` so they do not
depend on the process working directory.

## CLI Help

After local installation, run:

```bash
dwca-cloud-geospatial --help
dwca-cloud-geospatial inspect --help
dwca-cloud-geospatial convert --help
dwca-cloud-geospatial validate --help
```

Without installing the console script, the module entry point is:

```bash
PYTHONPATH="${REPO}/src" python -m dwca_cloud_geospatial --help
```

Without activating `.venv/`, use:

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial" --help
```

The Prompt 01 CLI is a stub. It exposes the planned `inspect`, `convert` and
`validate` commands, but converter behavior is intentionally deferred.
