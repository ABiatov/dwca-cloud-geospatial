from __future__ import annotations

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR
from dwca_cloud_geospatial.normalization import (
    COORDINATE_OUT_OF_RANGE,
    INVALID_LATITUDE,
    INVALID_LONGITUDE,
    MISSING_COORDINATES,
    ZERO_ZERO_COORDINATE,
    normalize_occurrence_records,
)
from dwca_cloud_geospatial.occurrence import read_occurrence_rows


NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"


def test_valid_coordinates_become_normalized_occurrence_records() -> None:
    read_result = read_occurrence_rows(NORMALIZATION_FIXTURE_DIR)
    result = normalize_occurrence_records(read_result.records)

    assert not read_result.has_errors
    assert result.counts.source_records == 7
    assert result.counts.parsed_records == 7
    assert result.counts.accepted_records == 2
    assert result.counts.rejected_records == 5
    assert len(result.accepted_records) + len(result.rejected_records) == 7

    record = result.accepted_records[0]
    assert record.source_record_id == "occ-accepted"
    assert record.source_file == "occurrence.txt"
    assert record.source_row_number == 2
    assert record.source_data_row_number == 1
    assert record.occurrence_id == "occ-accepted"
    assert record.scientific_name == "Example species"
    assert record.basis_of_record == "HUMAN_OBSERVATION"
    assert record.decimal_latitude == 38.7223
    assert record.decimal_longitude == -9.1393
    assert record.coordinate_uncertainty_in_meters == 25.0
    assert record.geodetic_datum == "WGS84"
    assert record.country_code == "PT"
    assert record.dataset_name == "Sample dataset"
    assert record.license == "CC-BY-4.0"
    assert record.gbif_id == "12345"
    assert record.dataset_key == "dataset-key-1"
    assert record.obis_id == "obis-1"
    assert record.iucn_red_list_category == "LC"
    assert record.quality_flags is None
    assert record.has_quality_flags is False
    assert record.raw_decimal_latitude == "38.7223"
    assert record.raw_decimal_longitude == "-9.1393"
    assert "scientificName" not in record.to_dict()


def test_event_date_is_normalized_and_year_is_derived_when_practical() -> None:
    read_result = read_occurrence_rows(NORMALIZATION_FIXTURE_DIR)
    result = normalize_occurrence_records(read_result.records)

    dated_record = result.accepted_records[0]
    assert dated_record.raw_event_date == "2020-05-17T12:30:00Z"
    assert dated_record.event_date == "2020-05-17"
    assert dated_record.event_year == 2020

    year_only_record = result.accepted_records[1]
    assert year_only_record.source_record_id == "occ-year-only"
    assert year_only_record.raw_event_date is None
    assert year_only_record.event_date is None
    assert year_only_record.event_year == 1999


def test_coordinate_failures_become_rejected_records_with_reason_codes() -> None:
    read_result = read_occurrence_rows(NORMALIZATION_FIXTURE_DIR)
    result = normalize_occurrence_records(read_result.records)

    reasons_by_id = {
        rejected.occurrence_id: rejected.reason_code
        for rejected in result.rejected_records
    }
    assert reasons_by_id == {
        "occ-missing-coordinate": MISSING_COORDINATES,
        "occ-invalid-latitude": INVALID_LATITUDE,
        "occ-invalid-longitude": INVALID_LONGITUDE,
        "occ-out-of-range": COORDINATE_OUT_OF_RANGE,
        "occ-zero-zero": ZERO_ZERO_COORDINATE,
    }

    rejected = result.rejected_records[0]
    assert rejected.source_file == "occurrence.txt"
    assert rejected.source_row_number == 4
    assert rejected.source_data_row_number == 3
    assert rejected.source_record_id == "occ-missing-coordinate"
    assert rejected.scientific_name == "Missing coordinate species"
    assert rejected.decimal_latitude == "12.3"
    assert rejected.decimal_longitude is None
    assert rejected.event_date == "2021-01-01"
    assert rejected.reason_message
