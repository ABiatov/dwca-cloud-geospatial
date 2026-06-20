from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR, REPOSITORY_ROOT
from dwca_cloud_geospatial.conversion import ConversionOptions, convert_dwca_archive
from dwca_cloud_geospatial.validation import validate_output_bundle


VIEWER_DIR = REPOSITORY_ROOT / "viewer"
NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"


def _load_manifest(bundle: Path) -> dict:
    return json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))


def test_static_viewer_files_exist_and_reference_declared_browser_assets() -> None:
    index = (VIEWER_DIR / "index.html").read_text(encoding="utf-8")
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")
    styles = (VIEWER_DIR / "styles.css").read_text(encoding="utf-8")
    readme = (VIEWER_DIR / "README.md").read_text(encoding="utf-8")

    assert (VIEWER_DIR / "styles.css").exists()
    assert "maplibre-gl@4.7.1" in index
    assert "flatgeobuf@4.3.3" in index
    assert "app.js" in index
    assert "manifest.json" in script
    assert "metadata/source.json" in script
    assert "metadata/processing.json" in script
    assert "https://tile.openstreetmap.org/{z}/{x}/{y}.png" in script
    assert "OpenStreetMap" in script
    assert "KINGDOM_COLOR_EXPRESSION" in script
    assert "\"Animalia\"" in script
    assert "\"Plantae\"" in script
    assert "occurrence-selected" in script
    assert "setFilter(\"occurrence-selected\"" in script
    assert "https://www.gbif.org/occurrence/" in script
    assert "target = \"_blank\"" in script
    assert "live GBIF" not in index
    assert "live OBIS" not in index
    assert ".empty-state[hidden]" in styles
    assert "display: none" in styles
    assert "http://localhost:8000/viewer/?bundle=../scratch/sample-bundle/" in readme


def test_static_viewer_implements_no_flatgeobuf_and_artifact_only_states() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert "No FlatGeobuf map layer is available for this bundle." in script
    assert "generate the bundle with the FlatGeobuf output format selected" in script
    assert "source_format === \"flatgeobuf\"" in script
    assert "source_format === \"geoparquet\"" not in script
    assert "not loaded as the MVP browser map layer" in script
    assert "browser loading is not part of the MVP viewer contract" in script
    assert "new Uint8Array(await response.arrayBuffer())" in script
    assert "flatgeobuf.deserialize(bytes)" in script
    assert "flatgeobuf.deserialize(url.href)" not in script


def test_static_viewer_quality_flag_filters_use_exact_tokens() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert ".split(\"|\")" in script
    assert "tokens.includes(selectedToken)" in script
    assert "has_quality_flags" in script
    assert "missing_event" not in script


def test_static_viewer_smoke_inputs_cover_generated_flatgeobuf_bundle(
    tmp_path: Path,
) -> None:
    pyogrio = pytest.importorskip(
        "pyogrio",
        reason="Pyogrio/GDAL is required for generated FlatGeobuf smoke bundles.",
    )
    pytest.importorskip("pyarrow", reason="PyArrow is required for Pyogrio Arrow.")
    drivers = pyogrio.list_drivers()
    if drivers.get("GPKG") is None or drivers.get("FlatGeobuf") is None:
        pytest.skip("GDAL must expose both GPKG and FlatGeobuf drivers.")

    bundle = tmp_path / "flatgeobuf-bundle"
    convert_dwca_archive(
        NORMALIZATION_FIXTURE_DIR,
        bundle,
        options=ConversionOptions(chunk_size=2),
    )

    validation = validate_output_bundle(bundle)
    assert not validation.has_errors

    manifest = _load_manifest(bundle)
    file_roles = {entry["path"]: entry["role"] for entry in manifest["files"]}
    assert file_roles["data/occurrences.fgb"] == "flatgeobuf"
    assert file_roles["data/occurrences.gpkg"] == "geopackage"
    assert any(layer["source_format"] == "flatgeobuf" for layer in manifest["layers"])
    assert "quality_flags" in manifest["viewer"]["filter_fields"]
    assert (bundle / "index.html").exists()
    assert (bundle / "styles.css").exists()
    assert (bundle / "app.js").exists()
    assert (bundle / "metadata" / "source.json").exists()
    assert (bundle / "metadata" / "processing.json").exists()


def test_static_viewer_smoke_inputs_cover_generated_geoparquet_only_bundle(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pyarrow", reason="PyArrow is required for GeoParquet output.")

    bundle = tmp_path / "geoparquet-bundle"
    convert_dwca_archive(
        NORMALIZATION_FIXTURE_DIR,
        bundle,
        options=ConversionOptions(output_formats=("geoparquet",), chunk_size=2),
    )

    validation = validate_output_bundle(bundle)
    assert not validation.has_errors

    manifest = _load_manifest(bundle)
    file_roles = {entry["role"] for entry in manifest["files"]}
    layer_formats = {layer["source_format"] for layer in manifest["layers"]}
    assert "geoparquet" in file_roles
    assert "flatgeobuf" not in file_roles
    assert "geopackage" not in file_roles
    assert "flatgeobuf" not in layer_formats
    assert (bundle / "index.html").exists()
    assert (bundle / "metadata" / "source.json").exists()
    assert (bundle / "metadata" / "processing.json").exists()
