from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR, OUTPUT_BUNDLE_FIXTURES_DIR
import pytest

from dwca_cloud_geospatial.bundle import (
    PROCESSING_METADATA_RELATIVE_PATH,
    REJECTED_RECORDS_RELATIVE_PATH,
    SOURCE_METADATA_RELATIVE_PATH,
    BundleWriterOptions,
    write_bundle_metadata,
)
from dwca_cloud_geospatial.flatgeobuf import (
    DEFAULT_FLATGEOBUF_RELATIVE_PATH,
    FLATGEOBUF_PROJECTION_COLUMNS,
    GEOMETRY_COLUMN,
    FlatGeobufLargeOutputWarning,
    FlatGeobufWriterOptions,
    write_flatgeobuf_occurrences,
)
from dwca_cloud_geospatial.geoparquet import (
    DEFAULT_GEOPARQUET_RELATIVE_PATH,
    GEOPARQUET_COMPRESSION,
    GEOPARQUET_CRS,
    GEOPARQUET_DEFAULT_ROW_GROUP_SIZE,
    GEOPARQUET_PROJECTION_COLUMNS,
    GEOPARQUET_VERSION,
    GEOMETRY_ENCODING,
    GEOMETRY_TYPE as GEOPARQUET_GEOMETRY_TYPE,
    GeoParquetWriteResult,
)
from dwca_cloud_geospatial.gbif import GbifDownloadMetadata
from dwca_cloud_geospatial.normalization import normalize_occurrence_records
from dwca_cloud_geospatial.occurrence import read_occurrence_rows


NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
QUALITY_RULES_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "quality_rules"


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


def _read_and_normalize(fixture_path: Path):
    read_result = read_occurrence_rows(fixture_path)
    assert not read_result.has_errors
    normalization_result = normalize_occurrence_records(read_result.records)
    return read_result, normalization_result


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_flatgeobuf_only_default_bundle_omits_rejected_report_and_geoparquet(
    tmp_path: Path,
) -> None:
    assert OUTPUT_BUNDLE_FIXTURES_DIR.exists()
    read_result, normalization_result = _read_and_normalize(QUALITY_RULES_FIXTURE_DIR)
    flatgeobuf_result = write_flatgeobuf_occurrences(
        normalization_result.accepted_records,
        tmp_path,
        backend=FileCreatingFlatGeobufBackend(),
    )

    result = write_bundle_metadata(
        output_directory=tmp_path,
        occurrence_result=read_result,
        normalization_result=normalization_result,
        flatgeobuf_result=flatgeobuf_result,
        options=BundleWriterOptions(
            bundle_id="test-flatgeobuf-only",
            created_at="2026-06-13T12:00:00Z",
        ),
    )

    assert result.rejected_records_path is None
    assert not (tmp_path / REJECTED_RECORDS_RELATIVE_PATH).exists()
    assert not (tmp_path / DEFAULT_GEOPARQUET_RELATIVE_PATH).exists()

    manifest = _load_json(result.manifest_path)
    source = _load_json(result.source_metadata_path)
    processing = _load_json(result.processing_metadata_path)

    assert manifest["id"] == "test-flatgeobuf-only"
    assert manifest["title"] == "Quality rules fixture"
    assert manifest["source"]["gbif_dataset_key"] is None
    assert manifest["source"]["obis_dataset_id"] is None
    assert manifest["counts"] == {
        "source_records": 20,
        "accepted_records": 20,
        "rejected_records": 0,
        "occurrence_records": 20,
    }
    assert [file_entry["path"] for file_entry in manifest["files"]] == [
        SOURCE_METADATA_RELATIVE_PATH.as_posix(),
        PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
        DEFAULT_FLATGEOBUF_RELATIVE_PATH.as_posix(),
    ]
    assert manifest["layers"] == [
        {
            "id": "occurrences",
            "title": "Occurrences",
            "type": "point",
            "source_format": "flatgeobuf",
            "path": DEFAULT_FLATGEOBUF_RELATIVE_PATH.as_posix(),
            "geometry": {
                "column": "geometry",
                "crs": "OGC:CRS84",
                "coordinate_order": "longitude_latitude",
            },
            "record_count": 20,
            "bounds": [20.0, 10.0, 22.0, 12.0],
        }
    ]
    assert set(manifest["viewer"]["display_fields"]).issubset(
        set(FLATGEOBUF_PROJECTION_COLUMNS)
    )
    assert set(manifest["viewer"]["filter_fields"]).issubset(
        set(FLATGEOBUF_PROJECTION_COLUMNS)
    )
    assert "taxon_id" not in manifest["viewer"]["display_fields"]

    file_entries = {entry["path"]: entry for entry in manifest["files"]}
    for relative_path, entry in file_entries.items():
        path = tmp_path / relative_path
        assert entry["bytes"] == path.stat().st_size
        assert entry["sha256"] == _sha256(path)
    assert file_entries[DEFAULT_FLATGEOBUF_RELATIVE_PATH.as_posix()]["record_count"] == 20

    assert source["dataset"]["title"] == "Quality rules fixture"
    assert source["source_archive"]["kind"] == "directory"
    assert source["source_files"][0] == {"path": "metadata.xml", "role": "metadata"}
    assert processing["counts"]["flatgeobuf_records"] == 20
    assert processing["counts"]["geoparquet_records"] == 0
    assert processing["counts"]["warning_count"] == len(processing["warnings"]) == 2
    assert processing["validation"]["status"] == "not_run"
    assert "class" in processing["field_mapping"]["normalized_fields"]
    assert "class_" not in processing["field_mapping"]["normalized_fields"]


def test_explicit_geoparquet_bundle_inventory_and_rejected_report(
    tmp_path: Path,
) -> None:
    read_result, normalization_result = _read_and_normalize(NORMALIZATION_FIXTURE_DIR)
    with pytest.warns(FlatGeobufLargeOutputWarning, match="Indexed FlatGeobuf"):
        flatgeobuf_result = write_flatgeobuf_occurrences(
            normalization_result.accepted_records,
            tmp_path,
            options=FlatGeobufWriterOptions(large_feature_count_threshold=2),
            backend=FileCreatingFlatGeobufBackend(),
        )
    geoparquet_path = tmp_path / DEFAULT_GEOPARQUET_RELATIVE_PATH
    geoparquet_path.parent.mkdir(parents=True, exist_ok=True)
    geoparquet_path.write_bytes(b"placeholder parquet bytes")
    geoparquet_result = GeoParquetWriteResult(
        path=geoparquet_path,
        relative_path=DEFAULT_GEOPARQUET_RELATIVE_PATH,
        record_count=len(normalization_result.accepted_records),
        columns=GEOPARQUET_PROJECTION_COLUMNS,
        geometry_column=GEOMETRY_COLUMN,
        geometry_type=GEOPARQUET_GEOMETRY_TYPE,
        geometry_encoding=GEOMETRY_ENCODING,
        crs=GEOPARQUET_CRS,
        coordinate_order="longitude_latitude",
        bounds=(-9.1393, 38.7223, -8.2, 40.1),
        row_group_size=GEOPARQUET_DEFAULT_ROW_GROUP_SIZE,
        compression=GEOPARQUET_COMPRESSION,
        geoparquet_version=GEOPARQUET_VERSION,
    )

    result = write_bundle_metadata(
        output_directory=tmp_path,
        occurrence_result=read_result,
        normalization_result=normalization_result,
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
        options=BundleWriterOptions(
            bundle_id="test-geoparquet",
            title="Explicit GeoParquet bundle",
            created_at="2026-06-13T12:00:00Z",
            configuration={"formats": ["flatgeobuf", "geoparquet"]},
        ),
    )

    manifest = _load_json(result.manifest_path)
    processing = _load_json(result.processing_metadata_path)
    source = _load_json(result.source_metadata_path)

    assert result.rejected_records_path == tmp_path / REJECTED_RECORDS_RELATIVE_PATH
    assert result.rejected_records_path.exists()
    assert manifest["title"] == "Explicit GeoParquet bundle"
    assert manifest["counts"]["source_records"] == 7
    assert manifest["counts"]["accepted_records"] == 2
    assert manifest["counts"]["rejected_records"] == 5
    assert [file_entry["path"] for file_entry in manifest["files"]] == [
        SOURCE_METADATA_RELATIVE_PATH.as_posix(),
        PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
        DEFAULT_GEOPARQUET_RELATIVE_PATH.as_posix(),
        DEFAULT_FLATGEOBUF_RELATIVE_PATH.as_posix(),
        REJECTED_RECORDS_RELATIVE_PATH.as_posix(),
    ]
    inventory = {entry["path"]: entry for entry in manifest["files"]}
    assert inventory[DEFAULT_GEOPARQUET_RELATIVE_PATH.as_posix()]["record_count"] == 2
    assert inventory[REJECTED_RECORDS_RELATIVE_PATH.as_posix()]["record_count"] == 5
    assert all(entry["bytes"] is not None for entry in manifest["files"])
    assert all(entry["sha256"] is not None for entry in manifest["files"])

    layers_by_format = {layer["source_format"]: layer for layer in manifest["layers"]}
    assert set(layers_by_format) == {"flatgeobuf", "geoparquet"}
    assert layers_by_format["flatgeobuf"]["path"] == "data/occurrences.fgb"
    assert layers_by_format["geoparquet"]["path"] == "data/occurrences.parquet"
    assert manifest["viewer"]["default_layer"] == "occurrences"

    assert processing["counts"]["flatgeobuf_records"] == 2
    assert processing["counts"]["geoparquet_records"] == 2
    assert processing["counts"]["warning_count"] == len(processing["warnings"]) == 1
    assert {warning["code"] for warning in processing["warnings"]} == {
        "large_indexed_flatgeobuf_write",
    }
    writer_warning = [
        warning
        for warning in processing["warnings"]
        if warning["code"] == "large_indexed_flatgeobuf_write"
    ][0]
    assert writer_warning["stage"] == "flatgeobuf_writer"
    assert writer_warning["feature_count"] == 2
    assert writer_warning["field"] is None
    assert processing["configuration"]["user"] == {
        "formats": ["flatgeobuf", "geoparquet"]
    }
    assert processing["configuration"]["geoparquet"]["covering_bbox_column"] == {
        "enabled": False,
        "strategy": None,
        "threshold": None,
    }

    assert source["gbif"]["dataset_key"] == "dataset-key-1"
    assert source["gbif"]["download_key"] is None
    assert source["obis"]["dataset_id"] is None

    with result.rejected_records_path.open(encoding="utf-8", newline="") as file_obj:
        rows = list(csv.DictReader(file_obj))
    assert len(rows) == 5
    assert rows[0]["reason_code"] == "missing_coordinates"
    assert rows[0]["source_data_row_number"] == "3"


def test_bundle_metadata_preserves_manual_gbif_download_citation(
    tmp_path: Path,
) -> None:
    read_result, normalization_result = _read_and_normalize(QUALITY_RULES_FIXTURE_DIR)

    result = write_bundle_metadata(
        output_directory=tmp_path,
        occurrence_result=read_result,
        normalization_result=normalization_result,
        options=BundleWriterOptions(
            bundle_id="test-gbif-citation",
            created_at="2026-06-20T12:00:00Z",
        ),
        gbif_download_metadata=GbifDownloadMetadata(
            download_key="0038004-260519110011954",
            doi="10.15468/dl.3xbk5b",
            citation=(
                "GBIF.org (4 June 2026) GBIF Occurrence Download "
                "https://doi.org/10.15468/dl.3xbk5b"
            ),
        ),
    )

    source = _load_json(result.source_metadata_path)
    manifest = _load_json(result.manifest_path)
    processing = _load_json(result.processing_metadata_path)

    assert source["dataset"]["citation"] is None
    assert source["gbif"] == {
        "dataset_key": None,
        "download_key": "0038004-260519110011954",
        "doi": "10.15468/dl.3xbk5b",
        "citation": (
            "GBIF.org (4 June 2026) GBIF Occurrence Download "
            "https://doi.org/10.15468/dl.3xbk5b"
        ),
        "license": None,
    }
    assert manifest["source"]["doi"] == "10.15468/dl.3xbk5b"
    assert manifest["source"]["citation"] == source["gbif"]["citation"]
    assert processing["source_provenance"]["gbif"] == {
        "download_key": "0038004-260519110011954",
        "doi": "10.15468/dl.3xbk5b",
        "citation": source["gbif"]["citation"],
        "license": None,
    }
