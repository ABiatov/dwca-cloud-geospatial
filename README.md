# DwC-A to Cloud-Optimized Geospatial Formats

Convert Darwin Core Archive (DwC-A) biodiversity datasets into cloud-friendly geospatial formats, starting with GeoParquet and FlatGeobuf and later PMTiles, with a lightweight MapLibre viewer for static publishing and reuse.

This project is an early standalone component of the [Biodiversity Viewer Serverless](https://github.com/ABiatov/biodiversity-viewer-serverless) roadmap.

## Project Status

This repository is at the initial prototype stage. The first goal is to prove a simple, reproducible workflow:

1. Read a Darwin Core Archive dataset.
2. Extract occurrence records with coordinates.
3. Convert the data into cloud-friendly geospatial formats.
4. Publish the generated files as static assets.
5. Explore the result in a browser-based MapLibre viewer.

APIs, file layouts and command-line interfaces should be treated as experimental until the first tagged release.

Checklist DwC-A archives with `Taxon` cores can be inspected, but the MVP
conversion workflow targets occurrence archives that declare coordinate terms.

Default conversion writes indexed FlatGeobuf at `data/occurrences.fgb`.
FlatGeobuf generation now uses a bounded parser/normalizer handoff into a
persistent GeoPackage staging artifact at `data/occurrences.gpkg`, then asks
Pyogrio/GDAL to create the indexed FlatGeobuf with `SPATIAL_INDEX=YES`.
Explicit GeoParquet conversion can also run in a core-API large-output mode
that streams occurrence batches, writes a GeoParquet `bbox` covering column
and applies bounded grid spatial ordering.

The accepted MVP development plan is documented in [docs/development_plan.md](docs/development_plan.md).
The accepted static viewer contract is documented in
[docs/viewer_contract.md](docs/viewer_contract.md): MVP map display uses
declared FlatGeobuf point layers, GeoPackage artifacts are retained for
metadata/download, and GeoParquet-only bundles remain valid with a graceful
no-map-layer metadata/provenance state.

## Developer Quick Start

For development, prefer an in-repository virtual environment at `.venv/`.
Do not install project development dependencies into Conda `base` or the
system Python unless you are intentionally managing a separate throwaway
environment.

Use an explicit repository path in local commands:

```bash
export REPO="/Users/Alevtina/Documents/GitHub/dwca-cloud-geospatial"
python -m venv "${REPO}/.venv"
source "${REPO}/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e "${REPO}[dev]"
python -m pytest "${REPO}/tests"
dwca-cloud-geospatial --help
```

Default FlatGeobuf conversion requires the optional writer dependencies,
including Pyogrio/GDAL support for both `GPKG` and `FlatGeobuf`:

```bash
python -m pip install -e "${REPO}[dev,flatgeobuf]"
```

The Python import package is `dwca_cloud_geospatial`; the console command is
`dwca-cloud-geospatial`. The `inspect` command parses local DwC-A `meta.xml`
structure, `convert` writes local output bundles, and `validate` checks
generated bundle structure and geospatial outputs.

`convert` copies the minimal static viewer into each output bundle as
`index.html`, `styles.css`, `app.js` and `README.md`. After generating a
bundle, serve the repository or output parent as static files:

```bash
python -m http.server 8000 --directory "${REPO}"
```

```text
http://localhost:8000/scratch/sample-bundle/index.html
```

More setup details are documented in [docs/developer_setup.md](docs/developer_setup.md).
Converter usage is documented in [docs/converter.md](docs/converter.md).
For non-CLI users, a primitive Tkinter entry point is available as
`dwca-cloud-geospatial-gui`; it calls the same core conversion and validation
APIs as the CLI.

GBIF occurrence download DOI/citation provenance can be supplied manually or
resolved through explicit conversion-time enrichment. CLI and core conversion
remain no-network by default; pass `--gbif-enrich` to opt in. The GUI exposes
the same lookup as a visible `GBIF DOI citation lookup` checkbox selected by
default, and users can clear it for a no-network GUI conversion. Generated
bundles stay static: the copied viewer does not call GBIF, OBIS or a project
backend.

## MVP Outputs

- FlatGeobuf for the default lightweight geospatial exchange and viewer output.
- Persistent GeoPackage staging artifact at `data/occurrences.gpkg` whenever
  FlatGeobuf is generated.
- GeoParquet for analytical workflows when explicitly selected.
- Bounded parser/normalizer/writer handoff for default FlatGeobuf staging and
  GeoParquet large-output bundles.
- Metadata describing source files, processing parameters and generated outputs.
- Optional GBIF occurrence download DOI/citation provenance in
  `metadata/source.json`, `manifest.json` and processing provenance metadata.
- A minimal static MapLibre viewer copied into each generated bundle.

## MVP+ Planned Outputs

- PMTiles for tiled map visualization after the GeoParquet/FlatGeobuf converter and thin viewer are reliable.

## Why This Exists

Biodiversity datasets are often published in Darwin Core Archive format, which is excellent for data exchange but not always convenient for direct web mapping, static hosting or browser-based exploration.

This project explores a lightweight path from biodiversity data archives to portable geospatial files that can be hosted cheaply, reused by other tools and inspected without running a geospatial server.

## License

This project is licensed under the GNU Affero General Public License v3.0.
