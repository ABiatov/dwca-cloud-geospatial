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

## GeoParquet Writer Dependencies

The Prompt 07 GeoParquet writer production path uses PyArrow directly. Install
the GeoParquet writer dependency into the same in-repository `.venv/` with:

```bash
source "${REPO}/.venv/bin/activate"
python -m pip install -e "${REPO}[dev,geoparquet]"
```

The full writer-capable development install remains:

```bash
source "${REPO}/.venv/bin/activate"
python -m pip install -e "${REPO}[dev,flatgeobuf]"
```

The `flatgeobuf` extra includes PyArrow because the FlatGeobuf production
backend also writes Arrow tables, so the documented Prompt 06 full install is
enough to run the Prompt 07 GeoParquet writer tests as well.

Verify the installed GeoParquet writer stack with:

```bash
"${REPO}/.venv/bin/python" -c "import pyarrow; print('pyarrow', pyarrow.__version__)"
```

This repository has been verified with PyArrow `24.0.0`.

## Optional Validation Dependencies

The Prompt 09 bundle validator should always run required GeoParquet checks
through PyArrow when GeoParquet files are declared. Additional GeoParquet-aware
checks use optional tools when installed:

- `geoparquet-io` for spec-aware inspection/validation.
- DuckDB for analytical Parquet reads, metadata inspection and future
  row-group/bbox checks.
- Pyogrio/GDAL as a best-effort geospatial reader check when the local GDAL
  build supports Parquet/GeoParquet.

The `validation` extra pins `pyproj==3.7.0` for the verified local Python
3.13/macOS `.venv/` workflow. During validation setup, newer `pyproj` releases
may fall back to a source build and fail with `proj executable not found` when
a system PROJ installation is unavailable.

Install the optional validation toolchain into the same `.venv/` with:

```bash
source "${REPO}/.venv/bin/activate"
python -m pip install -e "${REPO}[dev,validation]"
```

For the full local writer and validation workflow, use:

```bash
source "${REPO}/.venv/bin/activate"
python -m pip install -e "${REPO}[dev,flatgeobuf,validation]"
```

Verify the optional validation tools with:

```bash
"${REPO}/.venv/bin/python" -c "import pyarrow, duckdb, pyproj; print('pyarrow', pyarrow.__version__); print('duckdb', duckdb.__version__); print('pyproj', pyproj.__version__)"
gpio --version
```

If `gpio` is unavailable or a local GDAL build cannot read GeoParquet, the
validator should report the affected check as dependency-dependent instead of
failing a bundle whose required PyArrow validation passes.

If validation installation still tries to build `pyproj` from source and fails
with a missing PROJ executable, install the verified binary wheel first and
then rerun the full extra install:

```bash
"${REPO}/.venv/bin/python" -m pip install --only-binary=:all: "pyproj==3.7.0"
"${REPO}/.venv/bin/python" -m pip install -e "${REPO}[dev,flatgeobuf,validation]"
```

The local validation stack has been verified with:

```text
geoparquet-io 1.3.0
duckdb 1.5.1
pyproj 3.7.0
pyarrow 24.0.0
pyogrio 0.12.1
GDAL 3.11.4
```

The Prompt 07 Pyogrio/GDAL GeoParquet reader test still skips in this local
stack because GDAL does not recognize GeoParquet/Parquet as a supported vector
read format. This is expected; Prompt 09 should use `geoparquet-io` and DuckDB
for optional GeoParquet-aware validation when available.

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

To verify Prompt 07 GeoParquet behavior, including a real
`data/occurrences.parquet` write, install PyArrow with either writer extra
above and run:

```bash
"${REPO}/.venv/bin/python" -m pytest "${REPO}/tests/test_geoparquet_writer.py" -q
```

Expected result when PyArrow is available: the PyArrow GeoParquet tests pass.
The GeoParquet-aware Pyogrio/GDAL reader check may skip when the local GDAL
build does not provide Parquet/GeoParquet read support.

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
