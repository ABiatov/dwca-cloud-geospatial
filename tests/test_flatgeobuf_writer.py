from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR
import pytest

from dwca_cloud_geospatial.flatgeobuf import (
    DEFAULT_FLATGEOBUF_RELATIVE_PATH,
    DEFAULT_GEOPACKAGE_RELATIVE_PATH,
    FLATGEOBUF_CRS,
    FLATGEOBUF_PROJECTION_COLUMNS,
    GEOMETRY_COLUMN,
    SPATIAL_INDEX_OPTION,
    FlatGeobufDependencyError,
    FlatGeobufLargeOutputWarning,
    FlatGeobufWriterOptions,
    estimate_spatial_index_memory_bytes,
    project_flatgeobuf_record,
    write_flatgeobuf_occurrences,
    write_flatgeobuf_occurrences_via_geopackage,
)
from dwca_cloud_geospatial.normalization import normalize_occurrence_records
from dwca_cloud_geospatial.occurrence import read_occurrence_rows


NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
QUALITY_RULES_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "quality_rules"


class CapturingFlatGeobufBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def write(
        self,
        *,
        path: Path,
        rows: tuple[dict[str, Any], ...],
        geometry_wkb: tuple[bytes, ...],
        layer_options: dict[str, str],
    ) -> None:
        self.calls.append(
            {
                "path": path,
                "rows": rows,
                "geometry_wkb": geometry_wkb,
                "layer_options": layer_options,
            }
        )


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


def test_flatgeobuf_projection_uses_required_normalized_columns() -> None:
    accepted_records, _rejected_records = _accepted_records()
    projected = project_flatgeobuf_record(accepted_records[0])

    assert tuple(projected) == FLATGEOBUF_PROJECTION_COLUMNS
    assert "class" in projected
    assert "class_" not in projected
    assert "scientificName" not in projected
    assert "decimalLongitude" not in projected
    assert projected["source_record_id"] == "occ-accepted"
    assert projected["decimal_longitude"] == -9.1393
    assert projected["decimal_latitude"] == 38.7223
    assert projected["quality_flags"] is None
    assert projected["has_quality_flags"] is False


def test_write_flatgeobuf_uses_default_path_spatial_index_and_point_wkb(
    tmp_path: Path,
) -> None:
    accepted_records, rejected_records = _accepted_records()
    rejected_ids = {record.occurrence_id for record in rejected_records}
    backend = CapturingFlatGeobufBackend()

    result = write_flatgeobuf_occurrences(
        accepted_records,
        tmp_path,
        backend=backend,
    )

    assert result.relative_path == DEFAULT_FLATGEOBUF_RELATIVE_PATH
    assert result.path == tmp_path / "data" / "occurrences.fgb"
    assert result.record_count == len(accepted_records) == 2
    assert result.columns == FLATGEOBUF_PROJECTION_COLUMNS
    assert result.geometry_column == GEOMETRY_COLUMN
    assert result.crs == FLATGEOBUF_CRS
    assert result.spatial_index is True
    assert result.warnings == ()

    assert len(backend.calls) == 1
    call = backend.calls[0]
    assert call["path"] == tmp_path / "data" / "occurrences.fgb"
    assert call["layer_options"] == {SPATIAL_INDEX_OPTION: "YES"}
    assert len(call["rows"]) == 2
    assert all(row["occurrence_id"] not in rejected_ids for row in call["rows"])
    assert _decode_point_wkb(call["geometry_wkb"][0]) == (-9.1393, 38.7223)
    assert _decode_point_wkb(call["geometry_wkb"][1]) == (-8.2, 40.1)


def test_quality_flags_are_preserved_in_flatgeobuf_projection(tmp_path: Path) -> None:
    accepted_records, _rejected_records = _accepted_records(QUALITY_RULES_FIXTURE_DIR)
    backend = CapturingFlatGeobufBackend()

    write_flatgeobuf_occurrences(accepted_records, tmp_path, backend=backend)

    rows_by_id = {row["occurrence_id"]: row for row in backend.calls[0]["rows"]}
    assert rows_by_id["q-no-flags"]["quality_flags"] is None
    assert rows_by_id["q-no-flags"]["has_quality_flags"] is False
    assert rows_by_id["q-multiple-flags"]["quality_flags"] == (
        "missing_event_date|missing_coordinate_uncertainty"
    )
    assert rows_by_id["q-multiple-flags"]["has_quality_flags"] is True


def test_large_indexed_output_warning_is_structured_and_emitted(
    tmp_path: Path,
) -> None:
    accepted_records, _rejected_records = _accepted_records()
    backend = CapturingFlatGeobufBackend()
    options = FlatGeobufWriterOptions(
        large_feature_count_threshold=2,
        large_spatial_index_warning_bytes=10_000_000,
    )

    with pytest.warns(FlatGeobufLargeOutputWarning, match="Indexed FlatGeobuf"):
        result = write_flatgeobuf_occurrences(
            accepted_records,
            tmp_path,
            options=options,
            backend=backend,
        )

    assert len(result.warnings) == 1
    assert result.warnings[0].code == "large_indexed_flatgeobuf_write"
    assert result.warnings[0].feature_count == 2
    assert result.warnings[0].estimated_spatial_index_bytes == (
        estimate_spatial_index_memory_bytes(2)
    )
    assert len(backend.calls) == 1


def test_large_output_warning_is_not_emitted_without_spatial_index(
    tmp_path: Path,
) -> None:
    accepted_records, _rejected_records = _accepted_records()
    backend = CapturingFlatGeobufBackend()
    options = FlatGeobufWriterOptions(
        spatial_index=False,
        large_feature_count_threshold=1,
    )

    result = write_flatgeobuf_occurrences(
        accepted_records,
        tmp_path,
        options=options,
        backend=backend,
    )

    assert result.warnings == ()
    assert result.spatial_index is False
    assert backend.calls[0]["layer_options"] == {SPATIAL_INDEX_OPTION: "NO"}


def test_real_flatgeobuf_write_when_optional_dependencies_are_available(
    tmp_path: Path,
) -> None:
    pyogrio = pytest.importorskip(
        "pyogrio",
        reason="Pyogrio/GDAL is required for real FlatGeobuf writer validation.",
    )
    pytest.importorskip(
        "pyarrow",
        reason="PyArrow is required for the production Pyogrio Arrow writer.",
    )
    if not hasattr(pyogrio, "write_arrow"):
        pytest.skip("Installed Pyogrio does not provide write_arrow.")

    accepted_records, _rejected_records = _accepted_records()
    try:
        result = write_flatgeobuf_occurrences(accepted_records, tmp_path)
    except FlatGeobufDependencyError as exc:
        pytest.skip(str(exc))

    assert result.path.exists()
    info = pyogrio.read_info(result.path, force_feature_count=True, force_total_bounds=True)
    assert info["driver"] == "FlatGeobuf"
    assert info["geometry_type"] == "Point"
    assert info["features"] == len(accepted_records)
    assert set(FLATGEOBUF_PROJECTION_COLUMNS).issubset(set(info["fields"]))
    assert info["total_bounds"] is not None
    west, south, east, north = info["total_bounds"]
    assert math.isclose(west, -9.1393)
    assert math.isclose(south, 38.7223)
    assert math.isclose(east, -8.2)
    assert math.isclose(north, 40.1)


def test_real_geopackage_staged_flatgeobuf_write_reconciles_records(
    tmp_path: Path,
) -> None:
    pyogrio = pytest.importorskip(
        "pyogrio",
        reason="Pyogrio/GDAL is required for GeoPackage-staged FlatGeobuf.",
    )
    pytest.importorskip("pyarrow", reason="PyArrow is required for Pyogrio Arrow.")
    drivers = pyogrio.list_drivers()
    if drivers.get("GPKG") is None or drivers.get("FlatGeobuf") is None:
        pytest.skip("GDAL must expose both GPKG and FlatGeobuf drivers.")

    accepted_records, _rejected_records = _accepted_records()
    result = write_flatgeobuf_occurrences_via_geopackage(
        (accepted_records[:1], accepted_records[1:]),
        tmp_path,
    )

    assert result.path == tmp_path / DEFAULT_FLATGEOBUF_RELATIVE_PATH
    assert result.path.exists()
    assert result.spatial_index is True
    assert result.generated_from_geopackage is True
    assert result.helper_strategy == "pyogrio.open_arrow_to_write_arrow"
    assert result.staging_result is not None
    assert result.staging_result.path == tmp_path / DEFAULT_GEOPACKAGE_RELATIVE_PATH
    assert result.staging_result.path.exists()
    assert result.staging_result.record_count == result.record_count == 2

    gpkg_info = pyogrio.read_info(
        result.staging_result.path,
        layer="occurrences",
        force_feature_count=True,
    )
    fgb_info = pyogrio.read_info(result.path, force_feature_count=True)
    assert gpkg_info["features"] == fgb_info["features"] == 2
    assert set(FLATGEOBUF_PROJECTION_COLUMNS).issubset(set(gpkg_info["fields"]))
    assert set(FLATGEOBUF_PROJECTION_COLUMNS).issubset(set(fgb_info["fields"]))

    gpkg_rows = pyogrio.read_arrow(result.staging_result.path, layer="occurrences")[1]
    fgb_rows = pyogrio.read_arrow(result.path)[1]
    comparable = (
        "source_record_id",
        "quality_flags",
        "has_quality_flags",
        "decimal_longitude",
        "decimal_latitude",
    )
    gpkg_set = {
        tuple(row[column] for column in comparable)
        for row in gpkg_rows.select(list(comparable)).to_pylist()
    }
    fgb_set = {
        tuple(row[column] for column in comparable)
        for row in fgb_rows.select(list(comparable)).to_pylist()
    }
    assert gpkg_set == fgb_set
