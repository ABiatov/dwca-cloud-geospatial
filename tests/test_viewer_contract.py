from __future__ import annotations

import json
from pathlib import Path

from conftest import OUTPUT_BUNDLE_FIXTURES_DIR, REPOSITORY_ROOT


VIEWER_CONTRACT_FIXTURE_DIR = OUTPUT_BUNDLE_FIXTURES_DIR / "viewer_contract"
VIEWER_FILTER_FIELDS = {
    "scientific_name",
    "kingdom",
    "event_year",
    "basis_of_record",
    "iucn_red_list_category",
    "quality_flags",
}


def _load_fixture(name: str) -> dict:
    path = VIEWER_CONTRACT_FIXTURE_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_viewer_contract_document_exists_and_records_mvp_boundaries() -> None:
    contract_path = REPOSITORY_ROOT / "docs" / "viewer_contract.md"
    contract = contract_path.read_text(encoding="utf-8")

    assert contract_path.exists()
    assert "source_format` is `flatgeobuf`" in contract
    assert "GeoPackage browser rendering is outside this contract." in contract
    assert "Do not attempt browser GeoParquet loading in the MVP." in contract
    assert "split on `|` and match exact tokens" in contract
    assert "`manifest.viewer.map_title`" in contract
    assert "Do not fall back to `metadata/source.json.dataset.title`" in contract
    assert "live GBIF API" in contract
    assert "live OBIS API" in contract


def test_deployment_document_records_static_mvp_review_boundaries() -> None:
    deployment_path = REPOSITORY_ROOT / "docs" / "deployment.md"
    deployment = deployment_path.read_text(encoding="utf-8")

    assert deployment_path.exists()
    assert "No Python backend" in deployment
    assert "`data/occurrences.gpkg`" in deployment
    assert "retained GeoPackage staging artifact" in deployment
    assert "No FlatGeobuf map layer is available for this bundle." in deployment
    assert "PMTiles generation is deferred to MVP+" in deployment
    assert "Checklist DwC-A archives with `Taxon` cores" in deployment
    assert "large_indexed_flatgeobuf_write" in deployment


def test_flatgeobuf_fixture_declares_geopackage_as_inventory_only() -> None:
    manifest = _load_fixture("flatgeobuf_with_geopackage_manifest.json")

    files_by_role = {entry["role"]: entry for entry in manifest["files"]}
    assert files_by_role["flatgeobuf"]["path"] == "data/occurrences.fgb"
    assert files_by_role["geopackage"]["path"] == "data/occurrences.gpkg"

    layer_formats = {layer["source_format"] for layer in manifest["layers"]}
    assert layer_formats == {"flatgeobuf"}
    assert manifest["viewer"]["default_layer"] == "occurrences"
    assert manifest["viewer"]["map_title"] == "Custom publisher-facing map title"
    assert set(manifest["viewer"]["filter_fields"]) == VIEWER_FILTER_FIELDS
    assert "class" in manifest["viewer"]["display_fields"]
    assert "class_" not in manifest["viewer"]["display_fields"]


def test_geoparquet_only_fixture_represents_valid_no_flatgeobuf_state() -> None:
    manifest = _load_fixture("geoparquet_only_manifest.json")

    file_roles = {entry["role"] for entry in manifest["files"]}
    layer_formats = {layer["source_format"] for layer in manifest["layers"]}
    assert "geoparquet" in file_roles
    assert "flatgeobuf" not in file_roles
    assert "geopackage" not in file_roles
    assert layer_formats == {"geoparquet"}
    assert not any(
        layer["source_format"] == "flatgeobuf" for layer in manifest["layers"]
    )
    assert "map_title" not in manifest["viewer"]
    assert set(manifest["viewer"]["filter_fields"]) == VIEWER_FILTER_FIELDS
