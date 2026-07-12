from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import DWCA_FIXTURES_DIR, MINIMAL_OCCURRENCE_FIXTURE_DIR
from dwca_cloud_geospatial.bundle import (
    DEFAULT_VIEWER_APP_DESCRIPTION,
    DEFAULT_VIEWER_MAP_TITLE,
    MANIFEST_RELATIVE_PATH,
)
from dwca_cloud_geospatial.conversion import (
    ConversionError,
    ConversionOptions,
    convert_dwca_archive,
)
from dwca_cloud_geospatial.flatgeobuf import (
    DEFAULT_FLATGEOBUF_RELATIVE_PATH,
    DEFAULT_GEOPACKAGE_RELATIVE_PATH,
)
from dwca_cloud_geospatial.geoparquet import (
    DEFAULT_GEOPARQUET_RELATIVE_PATH,
    GeoParquetWriterOptions,
)
from dwca_cloud_geospatial.gbif import GbifDownloadOptions
from dwca_cloud_geospatial.validation import validate_output_bundle


VALID_OCCURRENCE_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "valid"
NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
CHECKLIST_FIXTURES = (
    DWCA_FIXTURES_DIR / "dwca-appendixiibernconventionua-v1.2.zip",
)


class FileCreatingFlatGeobufBackend:
    def write(
        self,
        *,
        path: Path,
        rows: tuple[dict[str, Any], ...],
        geometry_wkb: tuple[bytes, ...],
        layer_options: dict[str, str],
    ) -> None:
        path.write_bytes(
            json.dumps(
                {
                    "rows": len(rows),
                    "geometry": len(geometry_wkb),
                    "layer_options": layer_options,
                },
                sort_keys=True,
            ).encode("utf-8")
        )


def test_core_conversion_writes_default_flatgeobuf_bundle(tmp_path: Path) -> None:
    result = convert_dwca_archive(
        VALID_OCCURRENCE_FIXTURE_DIR,
        tmp_path / "bundle",
        options=ConversionOptions(flatgeobuf_backend=FileCreatingFlatGeobufBackend()),
    )

    assert result.output_formats == ("flatgeobuf",)
    assert result.accepted_record_count == 1
    assert result.rejected_record_count == 0
    assert result.flatgeobuf_result is not None
    assert result.geoparquet_result is None
    assert (tmp_path / "bundle" / MANIFEST_RELATIVE_PATH).exists()
    assert (tmp_path / "bundle" / "index.html").exists()
    assert (tmp_path / "bundle" / "styles.css").exists()
    assert (tmp_path / "bundle" / "app.js").exists()
    assert (tmp_path / "bundle" / "README.md").exists()
    bundle_readme = (tmp_path / "bundle" / "README.md").read_text(encoding="utf-8")
    assert "Generated DwC-A Geospatial Bundle" in bundle_readme
    assert "source copy of the minimal static MapLibre viewer" not in bundle_readme
    assert (tmp_path / "bundle" / DEFAULT_FLATGEOBUF_RELATIVE_PATH).exists()
    assert not (tmp_path / "bundle" / DEFAULT_GEOPARQUET_RELATIVE_PATH).exists()

    manifest = json.loads(
        (tmp_path / "bundle" / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert [entry["path"] for entry in manifest["files"]] == [
        "metadata/source.json",
        "metadata/processing.json",
        "data/occurrences.fgb",
    ]
    assert manifest["viewer"]["map_title"] == DEFAULT_VIEWER_MAP_TITLE
    assert manifest["viewer"]["appDescription"] == DEFAULT_VIEWER_APP_DESCRIPTION
    assert "index.html" not in {entry["path"] for entry in manifest["files"]}


def test_core_conversion_writes_manual_gbif_download_metadata_without_network(
    tmp_path: Path,
) -> None:
    result = convert_dwca_archive(
        VALID_OCCURRENCE_FIXTURE_DIR,
        tmp_path / "bundle",
        options=ConversionOptions(
            flatgeobuf_backend=FileCreatingFlatGeobufBackend(),
            gbif=GbifDownloadOptions(
                download_key="0038004-260519110011954",
                doi="https://doi.org/10.15468/dl.3xbk5b",
                citation=(
                    "GBIF.org (4 June 2026) GBIF Occurrence Download "
                    "https://doi.org/10.15468/dl.3xbk5b"
                ),
            ),
        ),
    )

    source = json.loads(
        result.metadata_result.source_metadata_path.read_text(encoding="utf-8")
    )
    manifest = json.loads(result.metadata_result.manifest_path.read_text(encoding="utf-8"))

    assert source["gbif"]["download_key"] == "0038004-260519110011954"
    assert source["gbif"]["doi"] == "10.15468/dl.3xbk5b"
    assert source["gbif"]["citation"] == (
        "GBIF.org (4 June 2026) GBIF Occurrence Download "
        "https://doi.org/10.15468/dl.3xbk5b"
    )
    assert manifest["source"]["doi"] == "10.15468/dl.3xbk5b"
    assert manifest["source"]["citation"] == source["gbif"]["citation"]


def test_core_conversion_enriches_gbif_doi_from_citation_endpoint(
    tmp_path: Path,
) -> None:
    class FakeGbifClient:
        def fetch_download_metadata(self, download_key: str):
            assert download_key == "0049663-260519110011954"
            return {
                "key": download_key,
                "created": "2026-06-10",
                "license": "CC_BY_4_0",
            }

        def fetch_download_citation(self, download_key: str) -> str:
            assert download_key == "0049663-260519110011954"
            return (
                "GBIF.org (10 June 2026) GBIF Occurrence Download "
                "https://doi.org/10.15468/dl.9t5b2m"
            )

    result = convert_dwca_archive(
        VALID_OCCURRENCE_FIXTURE_DIR,
        tmp_path / "bundle",
        options=ConversionOptions(
            flatgeobuf_backend=FileCreatingFlatGeobufBackend(),
            gbif=GbifDownloadOptions(
                download_key="0049663-260519110011954",
                enrich=True,
            ),
            gbif_client=FakeGbifClient(),
        ),
    )

    source = json.loads(
        result.metadata_result.source_metadata_path.read_text(encoding="utf-8")
    )
    manifest = json.loads(result.metadata_result.manifest_path.read_text(encoding="utf-8"))
    processing = json.loads(
        result.metadata_result.processing_metadata_path.read_text(encoding="utf-8")
    )

    expected_citation = (
        "GBIF.org (10 June 2026) GBIF Occurrence Download "
        "https://doi.org/10.15468/dl.9t5b2m"
    )
    assert source["gbif"]["download_key"] == "0049663-260519110011954"
    assert source["gbif"]["doi"] == "10.15468/dl.9t5b2m"
    assert source["gbif"]["citation"] == expected_citation
    assert source["gbif"]["license"] == "CC_BY_4_0"
    assert manifest["source"]["doi"] == "10.15468/dl.9t5b2m"
    assert manifest["source"]["citation"] == expected_citation
    assert processing["source_provenance"]["gbif"] == {
        "download_key": "0049663-260519110011954",
        "doi": "10.15468/dl.9t5b2m",
        "citation": expected_citation,
        "license": "CC_BY_4_0",
    }


def test_core_conversion_supports_explicit_geoparquet_output(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")

    result = convert_dwca_archive(
        NORMALIZATION_FIXTURE_DIR,
        tmp_path / "bundle",
        options=ConversionOptions(output_formats=("geoparquet",)),
    )

    assert result.output_formats == ("geoparquet",)
    assert result.flatgeobuf_result is None
    assert result.geoparquet_result is not None
    assert (tmp_path / "bundle" / "index.html").exists()
    assert (tmp_path / "bundle" / DEFAULT_GEOPARQUET_RELATIVE_PATH).exists()
    assert not (tmp_path / "bundle" / DEFAULT_FLATGEOBUF_RELATIVE_PATH).exists()

    validation = validate_output_bundle(tmp_path / "bundle")
    assert not validation.has_errors


def test_core_conversion_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(ConversionError, match="Output path already exists"):
        convert_dwca_archive(
            VALID_OCCURRENCE_FIXTURE_DIR,
            output,
            options=ConversionOptions(flatgeobuf_backend=FileCreatingFlatGeobufBackend()),
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_core_conversion_rejects_checklist_archive_with_occurrence_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConversionError) as excinfo:
        convert_dwca_archive(
            CHECKLIST_FIXTURES[0],
            tmp_path / "bundle",
            options=ConversionOptions(flatgeobuf_backend=FileCreatingFlatGeobufBackend()),
        )

    assert "not an occurrence DwC-A archive" in excinfo.value.message
    assert [diagnostic.code for diagnostic in excinfo.value.diagnostics] == [
        "missing_occurrence_core"
    ]


def test_large_geoparquet_conversion_streams_chunks_and_rejected_report(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pyarrow")

    result = convert_dwca_archive(
        NORMALIZATION_FIXTURE_DIR,
        tmp_path / "bundle",
        options=ConversionOptions(
            output_formats=("geoparquet",),
            geoparquet=GeoParquetWriterOptions(large_output_mode=True),
            chunk_size=2,
        ),
    )

    assert result.occurrence_result.records == ()
    assert result.normalization_result.accepted_records == ()
    assert result.normalization_result.rejected_records == ()
    assert result.accepted_record_count == 2
    assert result.rejected_record_count == 5
    assert result.geoparquet_result is not None
    assert result.geoparquet_result.covering_bbox_column is True
    assert result.geoparquet_result.spatial_sorting is True
    assert result.metadata_result.rejected_records_path is not None
    assert result.metadata_result.rejected_records_path.exists()

    processing = json.loads(
        (tmp_path / "bundle" / "metadata" / "processing.json").read_text(
            encoding="utf-8"
        )
    )
    assert processing["configuration"]["geoparquet"]["large_output_mode"] is True
    assert processing["configuration"]["geoparquet"]["covering_bbox_column"]["enabled"] is True
    assert processing["configuration"]["geoparquet"]["spatial_sorting"] == {
        "enabled": True,
        "strategy": "grid",
        "threshold": None,
    }
    assert processing["configuration"]["user"]["chunk_size"] == 2
    assert processing["counts"]["source_records"] == 7
    assert processing["counts"]["accepted_records"] == 2
    assert processing["counts"]["rejected_records"] == 5

    validation = validate_output_bundle(tmp_path / "bundle")
    assert not validation.has_errors


def test_default_flatgeobuf_conversion_uses_geopackage_staging_and_streamed_rejections(
    tmp_path: Path,
) -> None:
    pyogrio = pytest.importorskip(
        "pyogrio",
        reason="Pyogrio/GDAL is required for GeoPackage-staged FlatGeobuf conversion.",
    )
    pytest.importorskip("pyarrow", reason="PyArrow is required for Pyogrio Arrow.")
    drivers = pyogrio.list_drivers()
    if drivers.get("GPKG") is None or drivers.get("FlatGeobuf") is None:
        pytest.skip("GDAL must expose both GPKG and FlatGeobuf drivers.")

    result = convert_dwca_archive(
        NORMALIZATION_FIXTURE_DIR,
        tmp_path / "bundle",
        options=ConversionOptions(chunk_size=2),
    )

    assert result.output_formats == ("flatgeobuf",)
    assert result.occurrence_result.records == ()
    assert result.normalization_result.accepted_records == ()
    assert result.normalization_result.rejected_records == ()
    assert result.accepted_record_count == 2
    assert result.rejected_record_count == 5
    assert result.flatgeobuf_result is not None
    assert result.flatgeobuf_result.generated_from_geopackage is True
    assert result.flatgeobuf_result.spatial_index is True
    assert result.flatgeobuf_result.bounds is not None
    assert result.flatgeobuf_result.staging_result is not None
    assert (tmp_path / "bundle" / DEFAULT_GEOPACKAGE_RELATIVE_PATH).exists()
    assert (tmp_path / "bundle" / DEFAULT_FLATGEOBUF_RELATIVE_PATH).exists()
    assert (tmp_path / "bundle" / "index.html").exists()
    assert result.metadata_result.rejected_records_path is not None
    assert result.metadata_result.rejected_records_path.exists()

    manifest = json.loads(
        (tmp_path / "bundle" / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert [entry["path"] for entry in manifest["files"]] == [
        "metadata/source.json",
        "metadata/processing.json",
        "data/occurrences.gpkg",
        "data/occurrences.fgb",
        "reports/rejected_records.csv",
    ]
    inventory = {entry["path"]: entry for entry in manifest["files"]}
    assert manifest["layers"][0]["bounds"] == list(result.flatgeobuf_result.bounds)
    assert manifest["viewer"]["initial_bounds"] == manifest["layers"][0]["bounds"]
    assert inventory["data/occurrences.gpkg"]["role"] == "geopackage"
    assert inventory["data/occurrences.gpkg"]["media_type"] == (
        "application/geopackage+sqlite3"
    )
    assert inventory["data/occurrences.gpkg"]["record_count"] == 2
    assert inventory["data/occurrences.fgb"]["record_count"] == 2

    processing = json.loads(
        (tmp_path / "bundle" / "metadata" / "processing.json").read_text(
            encoding="utf-8"
        )
    )
    assert processing["counts"]["geopackage_records"] == 2
    assert processing["counts"]["flatgeobuf_records"] == 2
    assert processing["configuration"]["geopackage_staging"] == {
        "enabled": True,
        "relative_path": "data/occurrences.gpkg",
        "writer_backend": "pyogrio.write_arrow",
        "layer": "occurrences",
        "flatgeobuf_generated_from_geopackage": True,
        "gdal_ogr_helper_strategy": "pyogrio.open_arrow_to_write_arrow",
        "flatgeobuf_spatial_index": True,
    }
    assert processing["output_decisions"]["geopackage_staging_enabled"] is True
    assert processing["output_decisions"]["flatgeobuf_spatial_index"] is True

    gpkg_rows = pyogrio.read_arrow(
        tmp_path / "bundle" / DEFAULT_GEOPACKAGE_RELATIVE_PATH,
        layer="occurrences",
    )[1]
    fgb_rows = pyogrio.read_arrow(
        tmp_path / "bundle" / DEFAULT_FLATGEOBUF_RELATIVE_PATH
    )[1]
    comparable = [
        "source_record_id",
        "quality_flags",
        "has_quality_flags",
        "decimal_longitude",
        "decimal_latitude",
    ]
    assert {
        tuple(row[column] for column in comparable)
        for row in gpkg_rows.select(comparable).to_pylist()
    } == {
        tuple(row[column] for column in comparable)
        for row in fgb_rows.select(comparable).to_pylist()
    }

    validation = validate_output_bundle(tmp_path / "bundle")
    assert not validation.has_errors
    assert any(
        check.name == "geopackage_sqlite" and check.status == "passed"
        for check in validation.checks
    )
