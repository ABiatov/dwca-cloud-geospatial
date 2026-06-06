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

The accepted MVP development plan is documented in [docs/development_plan.md](docs/development_plan.md).

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

The Python import package is `dwca_cloud_geospatial`; the console command is
`dwca-cloud-geospatial`. The initial CLI is an `argparse` stub for the planned
`inspect`, `convert` and `validate` workflows. Converter behavior is deferred
to later MVP milestones.

More setup details are documented in [docs/developer_setup.md](docs/developer_setup.md).

## MVP Outputs

- GeoParquet for analytical workflows.
- FlatGeobuf for lightweight geospatial exchange.
- Metadata describing source files, processing parameters and generated outputs.
- A minimal static MapLibre viewer.

## MVP+ Planned Outputs

- PMTiles for tiled map visualization after the GeoParquet/FlatGeobuf converter and thin viewer are reliable.

## Why This Exists

Biodiversity datasets are often published in Darwin Core Archive format, which is excellent for data exchange but not always convenient for direct web mapping, static hosting or browser-based exploration.

This project explores a lightweight path from biodiversity data archives to portable geospatial files that can be hosted cheaply, reused by other tools and inspected without running a geospatial server.

## License

This project is licensed under the GNU Affero General Public License v3.0.
