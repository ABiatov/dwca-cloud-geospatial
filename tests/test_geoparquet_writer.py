from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR
import pytest

from dwca_cloud_geospatial.flatgeobuf import project_flatgeobuf_record
from dwca_cloud_geospatial.geoparquet import (
    DEFAULT_GEOPARQUET_RELATIVE_PATH,
    GEOPARQUET_CRS,
    GEOPARQUET_DEFAULT_ROW_GROUP_SIZE,
    GEOPARQUET_PROJECTION_COLUMNS,
    GEOPARQUET_VERSION,
    GEOMETRY_COLUMN,
    GEOMETRY_ENCODING,
    GEOMETRY_TYPE,
    GeoParquetWriterOptions,
    project_geoparquet_record,
    write_geoparquet_occurrences,
)
from dwca_cloud_geospatial.normalization import normalize_occurrence_records
from dwca_cloud_geospatial.occurrence import read_occurrence_rows


NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
QUALITY_RULES_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "quality_rules"
REQUIRED_GEOPARQUET_FIELDS = {
    "occurrence_id",
    "source_record_id",
    "source_file",
    "source_row_number",
    "source_data_row_number",
    "scientific_name",
    "kingdom",
    "taxon_id",
    "basis_of_record",
    "iucn_red_list_category",
    "event_date",
    "event_year",
    "decimal_longitude",
    "decimal_latitude",
    "coordinate_uncertainty_in_meters",
    "geodetic_datum",
    "country_code",
    "locality",
    "recorded_by",
    "identified_by",
    "license",
    "rights_holder",
    "dataset_name",
    "dataset_key",
    "publisher",
    "quality_flags",
    "has_quality_flags",
    "geometry",
}


def _accepted_records(fixture_path: Path = NORMALIZATION_FIXTURE_DIR):
    read_result = read_occurrence_rows(fixture_path)
    assert not read_result.has_errors
    result = normalize_occurrence_records(read_result.records)
    return result.accepted_records, result.rejected_records


def _decode_point_wkb(wkb: bytes) -> tuple[float, float]:
    byte_order, geometry_type, longitude, latitude = struct.unpack("<bIdd", wkb)
    assert byte_order == 1
    assert geometry_type == 1
    return longitude, latitude


def _geo_metadata(path: Path) -> dict[str, Any]:
    pq = pytest.importorskip(
        "pyarrow.parquet",
        reason="PyArrow is required for GeoParquet metadata validation.",
    )
    metadata = pq.read_metadata(path)
    assert metadata.metadata is not None
    return json.loads(metadata.metadata[b"geo"])


def test_geoparquet_projection_uses_analytical_normalized_columns() -> None:
    accepted_records, _rejected_records = _accepted_records()
    projected = project_geoparquet_record(accepted_records[0])

    assert tuple(projected) == GEOPARQUET_PROJECTION_COLUMNS[:-1]
    assert "class" in projected
    assert "class_" not in projected
    assert "scientificName" not in projected
    assert "decimalLongitude" not in projected
    assert projected["source_record_id"] == "occ-accepted"
    assert projected["decimal_longitude"] == -9.1393
    assert projected["decimal_latitude"] == 38.7223
    assert projected["quality_flags"] is None
    assert projected["has_quality_flags"] is False


def test_write_geoparquet_uses_default_path_metadata_and_point_wkb(
    tmp_path: Path,
) -> None:
    pa = pytest.importorskip("pyarrow", reason="PyArrow is required.")
    pq = pytest.importorskip("pyarrow.parquet", reason="PyArrow is required.")
    accepted_records, rejected_records = _accepted_records()
    rejected_ids = {record.occurrence_id for record in rejected_records}

    result = write_geoparquet_occurrences(accepted_records, tmp_path)

    assert result.relative_path == DEFAULT_GEOPARQUET_RELATIVE_PATH
    assert result.path == tmp_path / "data" / "occurrences.parquet"
    assert result.record_count == len(accepted_records) == 2
    assert result.columns == GEOPARQUET_PROJECTION_COLUMNS
    assert result.geometry_column == GEOMETRY_COLUMN
    assert result.geometry_encoding == GEOMETRY_ENCODING
    assert result.geometry_type == GEOMETRY_TYPE
    assert result.crs == GEOPARQUET_CRS
    assert result.bounds == (-9.1393, 38.7223, -8.2, 40.1)
    assert result.row_group_size == GEOPARQUET_DEFAULT_ROW_GROUP_SIZE

    table = pq.read_table(result.path)
    assert table.num_rows == len(accepted_records)
    assert tuple(table.column_names) == GEOPARQUET_PROJECTION_COLUMNS
    assert REQUIRED_GEOPARQUET_FIELDS.issubset(set(table.column_names))
    rows = table.to_pylist()
    assert all(row["occurrence_id"] not in rejected_ids for row in rows)
    assert _decode_point_wkb(rows[0][GEOMETRY_COLUMN]) == (-9.1393, 38.7223)
    assert _decode_point_wkb(rows[1][GEOMETRY_COLUMN]) == (-8.2, 40.1)
    assert table.schema.field(GEOMETRY_COLUMN).type == pa.binary()

    file_metadata = pq.read_metadata(result.path)
    assert file_metadata.num_rows == len(accepted_records)
    assert file_metadata.row_group(0).column(0).compression == "ZSTD"

    geo = json.loads(file_metadata.metadata[b"geo"])
    geometry_metadata = geo["columns"][GEOMETRY_COLUMN]
    assert geo["version"] == GEOPARQUET_VERSION
    assert geo["primary_column"] == GEOMETRY_COLUMN
    assert geometry_metadata["encoding"] == GEOMETRY_ENCODING
    assert geometry_metadata["geometry_types"] == [GEOMETRY_TYPE]
    assert geometry_metadata["bbox"] == [-9.1393, 38.7223, -8.2, 40.1]
    assert geometry_metadata["crs"]["id"] == {"authority": "OGC", "code": "CRS84"}
    axes = geometry_metadata["crs"]["coordinate_system"]["axis"]
    assert [axis["abbreviation"] for axis in axes] == ["Lon", "Lat"]


def test_quality_flags_are_preserved_in_geoparquet_projection(tmp_path: Path) -> None:
    pq = pytest.importorskip("pyarrow.parquet", reason="PyArrow is required.")
    accepted_records, _rejected_records = _accepted_records(QUALITY_RULES_FIXTURE_DIR)

    result = write_geoparquet_occurrences(accepted_records, tmp_path)

    rows_by_id = {
        row["occurrence_id"]: row for row in pq.read_table(result.path).to_pylist()
    }
    assert rows_by_id["q-no-flags"]["quality_flags"] is None
    assert rows_by_id["q-no-flags"]["has_quality_flags"] is False
    assert rows_by_id["q-multiple-flags"]["quality_flags"] == (
        "missing_event_date|missing_coordinate_uncertainty"
    )
    assert rows_by_id["q-multiple-flags"]["has_quality_flags"] is True
    for row in rows_by_id.values():
        assert row["has_quality_flags"] is (row["quality_flags"] is not None)


def test_configurable_row_group_size_controls_written_row_groups(
    tmp_path: Path,
) -> None:
    pq = pytest.importorskip("pyarrow.parquet", reason="PyArrow is required.")
    accepted_records, _rejected_records = _accepted_records()
    options = GeoParquetWriterOptions(row_group_size=1)

    result = write_geoparquet_occurrences(
        (record for record in accepted_records),
        tmp_path,
        options=options,
    )

    metadata = pq.read_metadata(result.path)
    assert result.row_group_size == 1
    assert metadata.num_row_groups == len(accepted_records)


def test_geoparquet_and_flatgeobuf_projections_share_accepted_record_set() -> None:
    accepted_records, _rejected_records = _accepted_records()

    geoparquet_ids = [
        project_geoparquet_record(record)["source_record_id"]
        for record in accepted_records
    ]
    flatgeobuf_ids = [
        project_flatgeobuf_record(record)["source_record_id"]
        for record in accepted_records
    ]

    assert geoparquet_ids == flatgeobuf_ids


def test_geoparquet_aware_reader_when_available(tmp_path: Path) -> None:
    pyogrio = pytest.importorskip(
        "pyogrio",
        reason="Pyogrio/GDAL is required for GeoParquet-aware validation.",
    )
    accepted_records, _rejected_records = _accepted_records()
    result = write_geoparquet_occurrences(accepted_records, tmp_path)

    try:
        info = pyogrio.read_info(
            result.path,
            force_feature_count=True,
            force_total_bounds=True,
        )
    except Exception as exc:  # pragma: no cover - depends on local GDAL drivers
        pytest.skip(f"GDAL GeoParquet read support is unavailable: {exc}")

    assert info["geometry_type"] == "Point"
    assert info["features"] == len(accepted_records)
    west, south, east, north = info["total_bounds"]
    assert math.isclose(west, -9.1393)
    assert math.isclose(south, 38.7223)
    assert math.isclose(east, -8.2)
    assert math.isclose(north, 40.1)


def test_geo_metadata_is_available_for_geoparquet_aware_validators(
    tmp_path: Path,
) -> None:
    accepted_records, _rejected_records = _accepted_records()
    result = write_geoparquet_occurrences(accepted_records, tmp_path)

    geo = _geo_metadata(result.path)

    assert geo["version"] == GEOPARQUET_VERSION
    assert geo["columns"][GEOMETRY_COLUMN]["crs"]["id"]["authority"] == "OGC"
