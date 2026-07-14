from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR, REPOSITORY_ROOT
from dwca_cloud_geospatial.conversion import ConversionOptions, convert_dwca_archive
from dwca_cloud_geospatial.validation import validate_output_bundle


VIEWER_DIR = REPOSITORY_ROOT / "viewer"
NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
VIEWER_ICON_ASSET_PATHS = (
    "assets/pic/pic-info-64.png",
    "assets/pic/pic-filter-64.png",
    "assets/pic/pic-list-64.png",
    "assets/pic/pic-download-64.png",
    "assets/pic/pic-copy-32.png",
)


def _load_manifest(bundle: Path) -> dict:
    return json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))


def _assert_viewer_icon_assets_copied(bundle: Path) -> None:
    for asset_path in VIEWER_ICON_ASSET_PATHS:
        assert (bundle / asset_path).exists()


def test_static_viewer_files_exist_and_reference_declared_browser_assets() -> None:
    index = (VIEWER_DIR / "index.html").read_text(encoding="utf-8")
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")
    styles = (VIEWER_DIR / "styles.css").read_text(encoding="utf-8")
    readme = (VIEWER_DIR / "README.md").read_text(encoding="utf-8")

    assert (VIEWER_DIR / "styles.css").exists()
    assert "maplibre-gl@4.7.1" in index
    assert "flatgeobuf@4.3.3" in index
    assert "app.js" in index
    assert 'id="map-title-header"' in index
    assert 'id="map-title"' in index
    assert 'id="app-description-button"' in index
    assert 'id="app-description-dialog"' in index
    assert 'id="app-description-content"' in index
    assert 'id="app-description-close"' in index
    assert 'role="dialog"' in index
    assert 'aria-modal="true"' in index
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
    assert "showPointPopup" in script
    assert "function copyTextToClipboard" in script
    assert "function legacyCopyText" in script
    assert "https://www.gbif.org/occurrence/" in script
    assert "target = \"_blank\"" in script
    assert "live GBIF" not in index
    assert "live OBIS" not in index
    assert ".empty-state[hidden]" in styles
    assert ".map-title-header[hidden]" in styles
    assert "grid-row: 1" in styles
    assert "grid-row: 2" in styles
    assert "grid-row: 3" in styles
    assert ".popup-scroll" in styles
    assert "display: none" in styles
    assert "http://localhost:8000/viewer/?bundle=../scratch/sample-bundle/" in readme


def test_static_viewer_uses_manifest_app_description_for_header_button_and_modal() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")
    styles = (VIEWER_DIR / "styles.css").read_text(encoding="utf-8")

    assert "function viewerAppDescription(manifest)" in script
    assert "viewer.appDescription" in script
    assert "String(description).trim()" in script
    assert "function renderAppHeader" in script
    assert 'byId("app-description-button")' in script
    assert 'byId("app-description-dialog")' in script
    assert 'byId("app-description-content")' in script
    assert "descriptionButton.hidden = !description" in script
    assert "header.hidden = !title && !description" in script
    assert "titleNode.hidden = !title" in script
    assert "function openAppDescriptionDialog" in script
    assert "function closeAppDescriptionDialog" in script
    assert 'event.key === "Escape"' in script
    assert "event.target === dialog" in script
    assert ".app-description-modal[hidden]" in styles
    assert ".app-description-content" in styles
    assert "overflow: auto" in styles

    helper_body = script[
        script.index("function viewerAppDescription(manifest)") :
        script.index("function isSafeAppDescriptionUrl")
    ]
    assert "manifest.title" not in helper_body
    assert "source" not in helper_body
    assert "dataset" not in helper_body
    assert "layer" not in helper_body


def test_static_viewer_sanitizes_manifest_app_description_html() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")
    expected_tags = [
        "p",
        "b",
        "i",
        "h2",
        "h3",
        "h4",
        "a",
        "img",
        "br",
        "ol",
        "ul",
        "li",
        "table",
        "tr",
        "td",
        "iframe",
        "center",
        "small",
    ]

    assert "const APP_DESCRIPTION_ALLOWED_TAGS = Object.freeze([" in script
    allowlist_body = script[
        script.index("const APP_DESCRIPTION_ALLOWED_TAGS = Object.freeze([") :
        script.index("]);", script.index("const APP_DESCRIPTION_ALLOWED_TAGS"))
    ]
    for tag in expected_tags:
        assert f'"{tag}"' in allowlist_body
    assert allowlist_body.count('"') // 2 == len(expected_tags)
    assert "const APP_DESCRIPTION_DROP_CONTENT_TAGS = new Set([\"script\", \"style\"])" in script
    assert "new DOMParser().parseFromString(String(html), \"text/html\")" in script
    assert "document.createElement(tagName)" in script
    assert "APP_DESCRIPTION_ALLOWED_TAG_SET.has(tagName)" in script
    assert "appendSanitizedChildren(fragment)" in script
    assert "onload" not in script
    assert "onclick" not in script
    assert "copySafeAttribute(source, target, \"title\")" in script
    assert "copySafeAttribute(source, target, \"alt\")" in script
    assert "copySafeAttribute(source, target, \"allow\")" in script
    assert "copyDimensionAttribute(source, target, \"width\")" in script
    assert "copyDimensionAttribute(source, target, \"height\")" in script
    assert "copyLoadingAttribute(source, target)" in script
    assert "allowfullscreen" in script
    assert "target = \"_blank\"" in script
    assert "rel = \"noopener\"" in script
    assert "function isSafeAppDescriptionUrl" in script
    assert "[\"http:\", \"https:\"].includes" in script
    assert "url.startsWith(\"//\")" in script
    assert "url.startsWith(\"/\")" in script
    assert 'tagName === "img" || tagName === "iframe"' in script


def test_static_viewer_implements_no_flatgeobuf_and_artifact_only_states() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert "No FlatGeobuf map layer is available for this bundle." in script
    assert "generate the bundle with the FlatGeobuf output format selected" in script
    assert "source_format === \"flatgeobuf\"" in script
    assert "source_format === \"geoparquet\"" not in script
    assert "artifactDescription" not in script
    assert "MVP browser point layer when declared in manifest.layers" not in script
    assert "not loaded as the MVP browser map layer" not in script
    assert "browser loading is not part of the MVP viewer contract" not in script
    assert "new Uint8Array(await response.arrayBuffer())" in script
    assert "flatgeobuf.deserialize(bytes)" in script
    assert "flatgeobuf.deserialize(url.href)" not in script


def test_static_viewer_uses_manifest_viewer_map_title_for_conditional_header() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert "function viewerMapTitle(manifest)" in script
    assert "viewer.map_title" in script
    assert "String(title).trim()" in script
    assert "function renderAppHeader" in script
    assert 'byId("map-title-header")' in script
    assert 'byId("map-title")' in script
    assert "titleNode.textContent = title" in script
    assert "titleNode.hidden = !title" in script

    helper_body = script[
        script.index("function viewerMapTitle(manifest)") :
        script.index("function viewerAppDescription")
    ]
    assert "manifest.title" not in helper_body
    assert "source" not in helper_body
    assert "dataset" not in helper_body
    assert "layer" not in helper_body


def test_static_viewer_resolves_manifest_visibility_safely_and_gates_controls() -> None:
    index = (VIEWER_DIR / "index.html").read_text(encoding="utf-8")
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")
    styles = (VIEWER_DIR / "styles.css").read_text(encoding="utf-8")

    assert "function viewerVisibility(manifest)" in script
    assert "function viewerElementVisible(path, manifest = state.manifest)" in script
    assert 'node.is_visible === false' in script
    assert 'path.split(".")' in script
    assert "function applyManifestVisibility()" in script
    assert 'viewerElementVisible(`panel-${panelName}`)' in script
    assert 'viewerElementVisible("popup")' in script
    assert 'byId("control-strip").hidden = !hasSidebarLauncher' in script
    assert "control-strip-hidden" in styles
    for element_id in (
        "control-strip",
        "panel-info-header",
        "panel-info-counts",
        "panel-info-provenance",
        "bottom-toggle-bar",
        "bottom-feature-details",
        "bottom-processing",
    ):
        assert f'id="{element_id}"' in index


def test_static_viewer_visibility_gates_named_children_without_hiding_unlisted_rows() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    for key in (
        "dataset_title",
        "description",
        "publisher",
        "doi",
        "citation",
        "license",
        "rights_holder",
        "source_archive",
        "archive_sha256",
        "gbif_dataset_key",
        "gbif_download_key",
        "generated",
        "converter",
        "validation",
    ):
        assert f'"{key}"' in script
    assert '[null, "Homepage", dataset.homepage]' in script
    assert '[null, "OBIS dataset id", obis.dataset_id' in script
    for key in (
        "scientific_name",
        "kingdom",
        "iucn_red_list_category",
        "event_year",
        "basis_of_record",
        "quality_flags",
    ):
        assert f'panel-filters.filter_groups.${{field}}' in script
    assert "function clearHiddenFilterState()" in script
    assert "VISIBILITY_ARTIFACT_PATHS" in script
    assert "function artifactVisibilityKey(path)" in script
    assert '["panel-download", "artifacts", visibilityKey]' in script
    assert 'const keys = Array.isArray(path) ? path : path.split(".");' in script
    assert ".ctrl-btn[hidden]" in (VIEWER_DIR / "styles.css").read_text(encoding="utf-8")
    assert "bottom-panels.bottom-toggle-bar" not in script
    assert "bottom-panels.bottom-panels-content.feature_details" in script
    assert "bottom-panels.bottom-panels-content.processing" in script


def test_static_viewer_orders_generated_file_links_for_review() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert (
        'const ARTIFACT_DISPLAY_ORDER = [\n'
        '    "data/occurrences.fgb",\n'
        '    "data/occurrences.gpkg",\n'
        '    "data/occurrences.parquet",\n'
        "    SOURCE_METADATA_PATH,\n"
        "    PROCESSING_METADATA_PATH,\n"
        "  ];"
    ) in script
    assert "function artifactDisplayRank" in script
    assert "left.index - right.index" in script


def test_static_viewer_formats_artifact_link_labels() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert 'return "source.json (metadata)";' in script
    assert 'return "processing.json (metadata)";' in script
    assert 'path.startsWith("data/") ? path.slice("data/".length) : path' in script
    assert "link.href = artifactUrl" in script
    assert "link.textContent = artifactLinkLabel(entry.path)" in script
    assert "link.textContent = entry.path" not in script


def test_static_viewer_renders_provenance_doi_links_safely() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert "function normalizeDoi" in script
    assert "function doiHref" in script
    assert "function appendCitationContent" in script
    assert "addProvenanceDefinition(list, label, value)" in script
    assert "https://doi.org/${doi}" in script
    assert "doi\\.org\\/(10\\.\\d{4,9}\\/\\S+)" in script
    assert "function escapeHTML" in script
    assert "innerHTML" not in script


def test_static_viewer_quality_flag_filters_use_exact_tokens() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert ".split(\"|\")" in script
    assert "tokens.includes(selectedToken)" in script
    assert "has_quality_flags" in script
    assert "missing_event" not in script


def test_static_viewer_uses_title_case_field_labels() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    assert 'iucn_red_list_category: "IUCN Red List Categories"' in script
    assert 'gbif: "GBIF"' in script
    assert 'id: "ID"' in script
    assert 'url: "URL"' in script
    assert "function fieldLabel(field)" in script
    assert "createFilterGroup(fieldLabel(field))" in script
    assert "addDefinition(list, fieldLabel(field), properties[field])" in script
    assert 'addLinkDefinition(list, "Source Record URL", occurrenceUrl, occurrenceUrl)' in script
    assert 'field.replaceAll("_", " ")' not in script


def test_static_viewer_orders_filters_for_review() -> None:
    script = (VIEWER_DIR / "app.js").read_text(encoding="utf-8")

    positions = [
        script.index('createFilterGroup("Scientific Name")'),
        script.index('createCategoricalFilter("kingdom")'),
        script.index('createCategoricalFilter("iucn_red_list_category")'),
        script.index('createFilterGroup("Event Year")'),
        script.index('createCategoricalFilter("basis_of_record")'),
        script.index("createQualityFilter()"),
    ]

    assert positions == sorted(positions)
    assert 'createFilterGroup("Quality Flags")' in script


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
    _assert_viewer_icon_assets_copied(bundle)
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
    assert (bundle / "styles.css").exists()
    assert (bundle / "app.js").exists()
    _assert_viewer_icon_assets_copied(bundle)
    assert (bundle / "metadata" / "source.json").exists()
    assert (bundle / "metadata" / "processing.json").exists()
