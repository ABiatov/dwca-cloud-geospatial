# Developer Setup

Status: Active development setup

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

## FlatGeobuf Writer Dependencies

The Prompt 06 FlatGeobuf writer production path uses Pyogrio with GDAL
FlatGeobuf support and PyArrow. Install those optional dependencies into the
same in-repository `.venv/`:

```bash
source "${REPO}/.venv/bin/activate"
python -m pip install -e "${REPO}[dev,flatgeobuf]"
```

Equivalent direct installation, useful when the editable package is already
installed, is:

```bash
"${REPO}/.venv/bin/python" -m pip install pyogrio pyarrow
```

Pyogrio wheels include the GDAL library used by Pyogrio on supported
platforms. If pip builds Pyogrio from source instead of installing a wheel,
install a compatible system GDAL first and then reinstall Pyogrio.

Verify the installed writer stack with:

```bash
"${REPO}/.venv/bin/python" -c "import pyogrio, pyarrow; print('pyogrio', pyogrio.__version__); print('gdal', pyogrio.__gdal_version_string__); print('pyarrow', pyarrow.__version__); print('FlatGeobuf', pyogrio.list_drivers().get('FlatGeobuf'))"
```

The FlatGeobuf driver should report read/write support, usually `rw`.

This repository has been verified with:

```text
pyogrio 0.12.1
GDAL 3.11.4
pyarrow 24.0.0
FlatGeobuf rw
```

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

To fully verify Prompt 06 FlatGeobuf behavior, including a real
`exports/occurrences.fgb` write instead of the dependency-isolated backend
tests, install the FlatGeobuf writer dependencies above and run:

```bash
"${REPO}/.venv/bin/python" -m pytest "${REPO}/tests/test_flatgeobuf_writer.py" -q
```

Expected result when Pyogrio, GDAL and PyArrow are available: all FlatGeobuf
writer tests pass with no dependency skip.

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

The `inspect` command parses local DwC-A `meta.xml` structure. The `convert`
and `validate` commands remain stubs until later MVP milestones.
