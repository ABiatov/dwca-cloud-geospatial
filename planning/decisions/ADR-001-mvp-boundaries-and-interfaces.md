# ADR-001: MVP Boundaries and User Interfaces

Status: Accepted

Date: 2026-06-04

## Context

The project is preparing a practical submission for the 2026 Ebbe Nielsen Challenge while keeping the repository reusable as a standalone DwC-A conversion component and as a future building block for `ABiatov/biodiversity-viewer-serverless`.

The intended product should let users convert already downloaded Darwin Core Archive files into portable geospatial outputs and a simple static viewer without requiring deep technical expertise.

## Decision

The MVP will prioritize a reliable local converter for already downloaded DwC-A archives.

The core implementation will live in a separate Python library layer, referred to here as `core`. This layer must not depend on the GUI or static viewer implementation. CLI, GUI and future integrations should call the same core conversion APIs.

The MVP output formats are:

- GeoParquet for analytical geospatial data.
- FlatGeobuf for lightweight geospatial exchange and simple viewer loading.
- JSON metadata, manifest and processing reports.
- A thin static viewer that reads generated metadata and geospatial outputs.

PMTiles is moved to MVP+. The project records PMTiles as an intended output, but implementation should wait until the GeoParquet/FlatGeobuf converter and thin viewer are reliable.

The MVP will not download archives from GBIF, OBIS or other APIs. Users provide an already downloaded DwC-A archive as input.

When source metadata is present in the archive or adjacent metadata, the converter must preserve GBIF/OBIS-relevant provenance fields in output metadata and expose them in the viewer where practical. This includes DOI, citation, dataset keys, download keys and license information when available.

User-facing interfaces for the MVP are:

- CLI commands for repeatable workflows.
- Python library/API for integrators.
- A primitive GUI using `tkinter`.

Installation strategy for the MVP is:

- `pipx` for simple cross-platform command-line installation.
- Python package/library usage for integrators.

Standalone desktop binaries for macOS, Windows and Linux are deferred until the core converter, CLI, library API, GUI and viewer are working and there is enough time before the Challenge submission.

## Consequences

The output bundle and metadata schema become the main reuse contract between this repository, the static viewer and future `biodiversity-viewer-serverless` work.

The GUI should remain a thin wrapper around the core library instead of owning conversion behavior.

GBIF/OBIS acquisition can be added later as an optional feature, but it must not become a required runtime dependency for the baseline conversion workflow.

The viewer should display source/provenance metadata when available, but it should not require live GBIF or OBIS API access to operate.

## Deferred

- PMTiles generation and tiled map optimization.
- GBIF/OBIS archive fetching.
- Standalone packaged desktop apps or binaries.
- Advanced browser-side querying of GeoParquet.

## Follow-Up Work

- Define the output bundle manifest and metadata schema.
- Define the initial `core` Python API boundaries.
- Define the CLI command surface.
- Define the `tkinter` GUI scope and progress/error reporting.
- Define the static viewer contract for metadata display and FlatGeobuf loading.
