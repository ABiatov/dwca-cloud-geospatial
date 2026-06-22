# Developer Setup

Status: Active development setup

## Paths

Use an explicit repository path in commands instead of relying on the current
working directory:

```bash
gh repo clone ABiatov/dwca-cloud-geospatial
# or: git clone git@github.com:ABiatov/dwca-cloud-geospatial.git
cd dwca-cloud-geospatial
export REPO="$(pwd)"
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

## FlatGeobuf And GeoPackage-Staging Dependencies

The default FlatGeobuf production path uses Pyogrio with GDAL FlatGeobuf and
GeoPackage support plus PyArrow. Conversion writes accepted chunks into
`data/occurrences.gpkg`, then streams that GeoPackage through Pyogrio/GDAL into
indexed `data/occurrences.fgb` with `SPATIAL_INDEX=YES`. Install those
optional dependencies into the same in-repository `.venv/`:

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
"${REPO}/.venv/bin/python" -c "import shutil, pyogrio, pyarrow; print('pyogrio', pyogrio.__version__); print('gdal', pyogrio.__gdal_version_string__); print('pyarrow', pyarrow.__version__); print('GPKG', pyogrio.list_drivers().get('GPKG')); print('FlatGeobuf', pyogrio.list_drivers().get('FlatGeobuf')); print('ogr2ogr', shutil.which('ogr2ogr'))"
```

The `GPKG` and `FlatGeobuf` drivers should report read/write support, usually
`rw`. An `ogr2ogr` executable is not required for the current implementation;
the selected helper strategy is Pyogrio/GDAL `open_arrow` to `write_arrow`.

This repository has been verified with:

```text
pyogrio 0.12.1
GDAL 3.11.4
pyarrow 24.0.0
GPKG rw
FlatGeobuf rw
ogr2ogr None
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

The bundle validator runs required GeoParquet checks through PyArrow when
GeoParquet files are declared. Additional GeoParquet-aware checks use optional
tools when installed:

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

Verify the validation-only optional tools with:

```bash
"${REPO}/.venv/bin/python" -c "import importlib.metadata as m, pyarrow, duckdb; print('pyarrow', pyarrow.__version__); print('duckdb', duckdb.__version__); print('geoparquet-io', m.version('geoparquet-io')); print('pyproj', m.version('pyproj'))"
```

For the full writer and validation workflow, verify Pyogrio/GDAL as well:

```bash
"${REPO}/.venv/bin/python" -c "import pyogrio; print('pyogrio', pyogrio.__version__); print('gdal', pyogrio.__gdal_version_string__); print('GPKG', pyogrio.list_drivers().get('GPKG')); print('FlatGeobuf', pyogrio.list_drivers().get('FlatGeobuf'))"
```

The validator uses the `geoparquet-io` Python API when available; it does not
require a `gpio` executable to be present on `PATH`. If `geoparquet-io` is
unavailable or a local GDAL build cannot read GeoParquet, the validator should
report the affected check as dependency-dependent instead of failing a bundle
whose required PyArrow validation passes.

If validation installation still tries to build `pyproj` from source and fails
with a missing PROJ executable, install the verified binary wheel first and
then rerun the full extra install:

```bash
"${REPO}/.venv/bin/python" -m pip install --only-binary=:all: "pyproj==3.7.0"
"${REPO}/.venv/bin/python" -m pip install -e "${REPO}[dev,flatgeobuf,validation]"
```

The full local writer and validation stack has been verified with:

```text
geoparquet-io 1.3.0
duckdb 1.5.1
pyproj 3.7.0
pyarrow 24.0.0
pyogrio 0.12.1
GDAL 3.11.4
GPKG rw
FlatGeobuf rw
```

The Prompt 07 Pyogrio/GDAL GeoParquet reader test still skips in this local
stack because GDAL does not recognize GeoParquet/Parquet as a supported vector
read format. This is expected; the Prompt 09 validator uses `geoparquet-io`
and DuckDB for optional GeoParquet-aware validation when available.

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
`data/occurrences.fgb` write instead of the dependency-isolated backend
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

To verify Prompt 09 bundle validation behavior, install the validation extra
above and run:

```bash
"${REPO}/.venv/bin/python" -m pytest "${REPO}/tests/test_bundle_validation.py" -q
```

Expected result in the verified local stack: all bundle validation tests pass.
The full suite may still include dependency-dependent skips from older writer
tests when local GDAL cannot read GeoParquet.

To verify Prompt 10b large GeoParquet behavior, use the same PyArrow-capable
environment and run the writer, conversion and validation tests:

```bash
"${REPO}/.venv/bin/python" -m pytest \
  "${REPO}/tests/test_geoparquet_writer.py" \
  "${REPO}/tests/test_conversion.py" \
  "${REPO}/tests/test_bundle_validation.py" -q
```

These tests cover GeoParquet large-output mode, FlatGeobuf GeoPackage staging,
chunked conversion, `bbox` covering column content, grid spatial ordering,
streaming rejected reports, GeoPackage/FlatGeobuf count reconciliation and
required PyArrow validation of bbox covering metadata.

To verify the static viewer smoke checks, run:

```bash
"${REPO}/.venv/bin/python" -m pytest "${REPO}/tests/test_static_viewer.py" -q
```

The static viewer source files live under:

```text
${REPO}/viewer/
```

`dwca-cloud-geospatial convert` copies those viewer runtime files into each
generated bundle root as `index.html`, `styles.css` and `app.js`, then writes
a generated bundle `README.md`.

For a local browser check, create a bundle under the repository root and serve
the repository as static files:

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial" convert \
  "${REPO}/tests/fixtures/dwca/minimal_occurrence/normalization" \
  "${REPO}/scratch/sample-bundle" \
  --overwrite
python -m http.server 8000 --directory "${REPO}"
```

Then open:

```text
http://localhost:8000/scratch/sample-bundle/index.html
```

The shared source viewer still supports the explicit bundle URL form when
needed:

```text
http://localhost:8000/viewer/?bundle=../scratch/sample-bundle/
```

Use `--format geoparquet` to verify the accepted no-FlatGeobuf state. The
viewer loads metadata, counts, processing warnings and artifact inventory for
GeoParquet-only bundles, but it does not attempt browser GeoParquet loading.
The viewer references MapLibre GL JS and FlatGeobuf JavaScript from public CDN
URLs in `viewer/index.html` and OpenStreetMap raster tiles from
`https://tile.openstreetmap.org/{z}/{x}/{y}.png` in `viewer/app.js`; mirror
or replace those assets for fully offline static hosting.

## CLI Help

After local installation, run:

```bash
dwca-cloud-geospatial --help
dwca-cloud-geospatial inspect --help
dwca-cloud-geospatial convert --help
dwca-cloud-geospatial validate --help
```

The primitive Tkinter GUI entry point is:

```bash
dwca-cloud-geospatial-gui
```

If `zsh` reports `command not found`, the virtual environment is not active
or the editable install has not been refreshed since the GUI script was added.
Activate `.venv/` first, or use the explicit script path:

```bash
source "${REPO}/.venv/bin/activate"
dwca-cloud-geospatial-gui
```

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial-gui"
```

or:

```bash
python -m dwca_cloud_geospatial.gui
```

Headless test runs do not require a GUI display; GUI-adjacent tests cover the
non-visual request validation and status-formatting helpers.

The GUI includes a `GBIF DOI citation lookup` checkbox selected by default.
It maps to CLI `--gbif-enrich` and may make read-only GBIF API requests during
conversion to populate occurrence download DOI/citation provenance. Clear the
checkbox for no-network GUI conversion.

In the GUI status panel, use the right-click context menu or the `Copy Text`
button to copy viewer instructions. `Ctrl+C` / `Cmd+C` copy shortcuts are a
known MVP limitation on the current Tk/macOS path.

Without installing the console script, the module entry point is:

```bash
PYTHONPATH="${REPO}/src" python -m dwca_cloud_geospatial --help
```

Without activating `.venv/`, use:

```bash
"${REPO}/.venv/bin/dwca-cloud-geospatial" --help
```

The `inspect` command parses local DwC-A `meta.xml` structure. The `convert`
command writes local output bundles and the `validate` command checks
generated bundle structure and geospatial outputs. Converter usage is
documented in `docs/converter.md`; static hosting and demo review steps are
documented in `docs/deployment.md`.
