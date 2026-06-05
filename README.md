# DwC-A to Cloud-Optimized Geospatial Formats

Convert Darwin Core Archive (DwC-A) biodiversity datasets into cloud-friendly geospatial formats such as GeoParquet, FlatGeobuf and PMTiles, with a lightweight MapLibre viewer for static publishing and reuse.

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

## Planned Outputs

- GeoParquet for analytical workflows.
- FlatGeobuf for lightweight geospatial exchange.
- PMTiles for tiled map visualization.
- Metadata describing source files, processing parameters and generated outputs.
- A minimal static MapLibre viewer.

## Why This Exists

Biodiversity datasets are often published in Darwin Core Archive format, which is excellent for data exchange but not always convenient for direct web mapping, static hosting or browser-based exploration.

This project explores a lightweight path from biodiversity data archives to portable geospatial files that can be hosted cheaply, reused by other tools and inspected without running a geospatial server.

## License

This project is licensed under the GNU Affero General Public License v3.0.
