from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR, OUTPUT_BUNDLE_FIXTURES_DIR
import pytest

from dwca_cloud_geospatial.bundle import (
    MANIFEST_RELATIVE_PATH,
    REJECTED_RECORDS_RELATIVE_PATH,
    BundleWriterOptions,
    write_bundle_metadata,
)
from dwca_cloud_geospatial.flatgeobuf import (
    DEFAULT_FLATGEOBUF_RELATIVE_PATH,
    write_flatgeobuf_occurrences,
)
from dwca_cloud_geospatial.geoparquet import (
    BBOX_COLUMN,
    DEFAULT_GEOPARQUET_RELATIVE_PATH,
    GeoParquetWriterOptions,
    write_geoparquet_occurrences,
)
from dwca_cloud_geospatial.normalization import normalize_occurrence_records
from dwca_cloud_geospatial.occurrence import read_occurrence_rows
from dwca_cloud_geospatial.validation import FAILED, validate_output_bundle


NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
QUALITY_RULES_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "quality_rules"


def _read_and_normalize(fixture_path: Path):
    read_result = read_occurrence_rows(fixture_path)
    assert not read_result.has_errors
    normalization_result = normalize_occurrence_records(read_result.records)
    return read_result, normalization_result


def _load_manifest(bundle_root: Path) -> dict:
    return json.loads((bundle_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))


def _write_manifest(bundle_root: Path, manifest: dict) -> None:
    (bundle_root / MANIFEST_RELATIVE_PATH).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refresh_manifest_entry(bundle_root: Path, relative_path: Path) -> None:
    manifest = _load_manifest(bundle_root)
    path_text = relative_path.as_posix()
    for entry in manifest["files"]:
        if entry["path"] == path_text:
            path = bundle_root / relative_path
            entry["bytes"] = path.stat().st_size
            entry["sha256"] = _sha256(path)
            break
    _write_manifest(bundle_root, manifest)


def _build_geoparquet_bundle(
    bundle_root: Path,
    *,
    fixture_path: Path = QUALITY_RULES_FIXTURE_DIR,
    bundle_id: str = "validation-geoparquet",
) -> None:
    pytest.importorskip("pyarrow", reason="PyArrow is required for validation fixtures.")
    read_result, normalization_result = _read_and_normalize(fixture_path)
    writer_options = GeoParquetWriterOptions(large_output_mode=bundle_id.endswith("-large"))
    geoparquet_result = write_geoparquet_occurrences(
        normalization_result.accepted_records,
        bundle_root,
        options=writer_options,
    )
    write_bundle_metadata(
        output_directory=bundle_root,
        occurrence_result=read_result,
        normalization_result=normalization_result,
        geoparquet_result=geoparquet_result,
        options=BundleWriterOptions(
            bundle_id=bundle_id,
            created_at="2026-06-13T12:00:00Z",
            configuration={"formats": ["geoparquet"]},
        ),
    )


def test_valid_geoparquet_bundle_passes_with_structured_result(tmp_path: Path) -> None:
    assert OUTPUT_BUNDLE_FIXTURES_DIR.exists()
    _build_geoparquet_bundle(tmp_path)

    result = validate_output_bundle(tmp_path)

    assert not result.has_errors
    assert result.status in {"passed", "passed_with_warnings"}
    assert "manifest.json" in result.checked_files
    assert "data/occurrences.parquet" in result.checked_files
    assert any(check.name == "geoparquet_pyarrow" and check.status == "passed" for check in result.checks)
    assert result.to_dict()["status"] == result.status


def test_valid_bundle_with_rejected_report_reconciles_counts(tmp_path: Path) -> None:
    _build_geoparquet_bundle(
        tmp_path,
        fixture_path=NORMALIZATION_FIXTURE_DIR,
        bundle_id="validation-rejected-report",
    )

    result = validate_output_bundle(tmp_path)

    assert not result.has_errors
    assert "reports/rejected_records.csv" in result.checked_files
    assert any(check.name == "rejected_report" and check.status == "passed" for check in result.checks)


def test_missing_inventory_file_fails_with_actionable_error(tmp_path: Path) -> None:
    _build_geoparquet_bundle(tmp_path)
    (tmp_path / DEFAULT_GEOPARQUET_RELATIVE_PATH).unlink()

    result = validate_output_bundle(tmp_path)

    assert result.status == FAILED
    assert {error.code for error in result.errors} >= {"manifest_file_missing"}


def test_checksum_mismatch_fails_when_sha256_is_present(tmp_path: Path) -> None:
    _build_geoparquet_bundle(tmp_path)
    manifest = _load_manifest(tmp_path)
    for entry in manifest["files"]:
        if entry["path"] == DEFAULT_GEOPARQUET_RELATIVE_PATH.as_posix():
            entry["sha256"] = "0" * 64
            break
    _write_manifest(tmp_path, manifest)

    result = validate_output_bundle(tmp_path)

    assert result.status == FAILED
    assert "manifest_file_checksum_mismatch" in {error.code for error in result.errors}


def test_missing_geoparquet_required_column_fails(tmp_path: Path) -> None:
    pq = pytest.importorskip("pyarrow.parquet", reason="PyArrow is required.")
    _build_geoparquet_bundle(tmp_path)
    parquet_path = tmp_path / DEFAULT_GEOPARQUET_RELATIVE_PATH
    table = pq.read_table(parquet_path).drop(["scientific_name"])
    pq.write_table(table, parquet_path)
    _refresh_manifest_entry(tmp_path, DEFAULT_GEOPARQUET_RELATIVE_PATH)

    result = validate_output_bundle(tmp_path)

    assert result.status == FAILED
    assert "geoparquet_required_columns_missing" in {error.code for error in result.errors}


def test_count_mismatch_fails(tmp_path: Path) -> None:
    _build_geoparquet_bundle(tmp_path)
    manifest = _load_manifest(tmp_path)
    manifest["counts"]["accepted_records"] += 1
    _write_manifest(tmp_path, manifest)

    result = validate_output_bundle(tmp_path)

    assert result.status == FAILED
    assert "manifest_processing_count_mismatch" in {error.code for error in result.errors}


def test_rejected_csv_required_columns_are_validated(tmp_path: Path) -> None:
    _build_geoparquet_bundle(
        tmp_path,
        fixture_path=NORMALIZATION_FIXTURE_DIR,
        bundle_id="validation-invalid-rejected-report",
    )
    report_path = tmp_path / REJECTED_RECORDS_RELATIVE_PATH
    with report_path.open(encoding="utf-8", newline="") as file_obj:
        rows = list(csv.DictReader(file_obj))
    reduced_columns = [
        column
        for column in rows[0]
        if column not in {"reason_message", "source_data_row_number"}
    ]
    with report_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=reduced_columns)
        writer.writeheader()
        writer.writerows({column: row[column] for column in reduced_columns} for row in rows)
    _refresh_manifest_entry(tmp_path, REJECTED_RECORDS_RELATIVE_PATH)

    result = validate_output_bundle(tmp_path)

    assert result.status == FAILED
    assert "rejected_report_required_columns_missing" in {error.code for error in result.errors}


def test_viewer_fields_must_exist_in_inspected_data(tmp_path: Path) -> None:
    _build_geoparquet_bundle(tmp_path)
    manifest = _load_manifest(tmp_path)
    manifest["viewer"]["filter_fields"].append("missing_viewer_field")
    _write_manifest(tmp_path, manifest)

    result = validate_output_bundle(tmp_path)

    assert result.status == FAILED
    assert "manifest_viewer_field_missing_from_data" in {error.code for error in result.errors}


def test_quality_flag_tokens_and_has_flag_consistency_are_validated(
    tmp_path: Path,
) -> None:
    pa = pytest.importorskip("pyarrow", reason="PyArrow is required.")
    pq = pytest.importorskip("pyarrow.parquet", reason="PyArrow is required.")
    _build_geoparquet_bundle(tmp_path)
    parquet_path = tmp_path / DEFAULT_GEOPARQUET_RELATIVE_PATH
    table = pq.read_table(parquet_path)
    row_count = table.num_rows
    quality_index = table.column_names.index("quality_flags")
    has_flags_index = table.column_names.index("has_quality_flags")
    table = table.set_column(
        quality_index,
        "quality_flags",
        pa.array(["missing_event_date|"] + [None] * (row_count - 1), type=pa.string()),
    )
    table = table.set_column(
        has_flags_index,
        "has_quality_flags",
        pa.array([False] * row_count, type=pa.bool_()),
    )
    pq.write_table(table, parquet_path)
    _refresh_manifest_entry(tmp_path, DEFAULT_GEOPARQUET_RELATIVE_PATH)

    result = validate_output_bundle(tmp_path)

    error_codes = {error.code for error in result.errors}
    assert result.status == FAILED
    assert "quality_flags_token_invalid" in error_codes
    assert "has_quality_flags_mismatch" in error_codes


def test_large_geoparquet_bbox_covering_is_validated(tmp_path: Path) -> None:
    pa = pytest.importorskip("pyarrow", reason="PyArrow is required.")
    pq = pytest.importorskip("pyarrow.parquet", reason="PyArrow is required.")
    _build_geoparquet_bundle(tmp_path, bundle_id="validation-geoparquet-large")
    parquet_path = tmp_path / DEFAULT_GEOPARQUET_RELATIVE_PATH
    table = pq.read_table(parquet_path)
    bbox_index = table.column_names.index(BBOX_COLUMN)
    replacement = []
    for row in table.to_pylist():
        bbox = dict(row[BBOX_COLUMN])
        bbox["xmax"] = bbox["xmax"] + 1
        replacement.append(bbox)
    table = table.set_column(
        bbox_index,
        BBOX_COLUMN,
        pa.array(replacement, type=table.schema.field(BBOX_COLUMN).type),
    )
    pq.write_table(table, parquet_path)
    _refresh_manifest_entry(tmp_path, DEFAULT_GEOPARQUET_RELATIVE_PATH)

    result = validate_output_bundle(tmp_path)

    assert result.status == FAILED
    assert "geoparquet_bbox_point_mismatch" in {error.code for error in result.errors}


def test_nullable_gbif_and_obis_source_fields_are_accepted(tmp_path: Path) -> None:
    _build_geoparquet_bundle(tmp_path)

    result = validate_output_bundle(tmp_path)

    assert not result.has_errors
    source = json.loads((tmp_path / "metadata" / "source.json").read_text(encoding="utf-8"))
    assert source["gbif"]["dataset_key"] is None
    assert source["obis"]["dataset_id"] is None


def test_flatgeobuf_declarations_are_validated_when_dependencies_are_available(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pyogrio", reason="Pyogrio is required for FlatGeobuf validation.")
    pytest.importorskip("pyarrow", reason="PyArrow is required for FlatGeobuf writing.")
    read_result, normalization_result = _read_and_normalize(NORMALIZATION_FIXTURE_DIR)
    flatgeobuf_result = write_flatgeobuf_occurrences(
        normalization_result.accepted_records,
        tmp_path,
    )
    write_bundle_metadata(
        output_directory=tmp_path,
        occurrence_result=read_result,
        normalization_result=normalization_result,
        flatgeobuf_result=flatgeobuf_result,
        options=BundleWriterOptions(
            bundle_id="validation-flatgeobuf",
            created_at="2026-06-13T12:00:00Z",
        ),
    )

    result = validate_output_bundle(tmp_path)

    assert not result.has_errors
    assert "exports/occurrences.fgb" in result.checked_files
    assert any(check.name == "flatgeobuf_pyogrio" and check.status == "passed" for check in result.checks)
