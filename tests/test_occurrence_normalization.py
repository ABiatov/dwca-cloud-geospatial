from __future__ import annotations

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR
from dwca_cloud_geospatial.normalization import (
    COORDINATE_OUT_OF_RANGE,
    INVALID_FLOAT,
    INVALID_INTEGER,
    INVALID_LATITUDE,
    INVALID_LONGITUDE,
    MISSING_COORDINATES,
    MISSING_REQUIRED_FIELD,
    NULL_VALUE_ACTION,
    RECORD_REJECTED_ACTION,
    ZERO_ZERO_COORDINATE,
    normalize_occurrence_records,
)
from dwca_cloud_geospatial.occurrence import OccurrenceSourceRecord, read_occurrence_rows


NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
QUALITY_RULES_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "quality_rules"


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


def test_iucn_red_list_category_accepts_iucn_namespace_term() -> None:
    record = OccurrenceSourceRecord(
        source_file="occurrence.txt",
        source_row_number=2,
        source_data_row_number=1,
        source_record_id=None,
        values_by_term={
            "http://rs.tdwg.org/dwc/terms/occurrenceID": "occ-iucn",
            "http://rs.tdwg.org/dwc/terms/scientificName": "IUCN namespace species",
            "http://rs.tdwg.org/dwc/terms/decimalLatitude": "20.057964",
            "http://rs.tdwg.org/dwc/terms/decimalLongitude": "-72.80522",
            "http://iucn.org/terms/iucnRedListCategory": "LC",
        },
        raw_values=(),
        field_metadata=(),
        relationship_keys={},
    )

    result = normalize_occurrence_records((record,))

    assert result.counts.accepted_records == 1
    assert result.accepted_records[0].iucn_red_list_category == "LC"


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

    failures_by_reason = {
        failure.reason_code: failure for failure in result.type_conversion_failures
    }
    assert failures_by_reason[MISSING_COORDINATES].field == "decimal_longitude"
    assert failures_by_reason[INVALID_LATITUDE].field == "decimal_latitude"
    assert failures_by_reason[INVALID_LONGITUDE].field == "decimal_longitude"
    assert failures_by_reason[COORDINATE_OUT_OF_RANGE].field == "decimal_latitude"
    assert failures_by_reason[ZERO_ZERO_COORDINATE].field == "coordinates"
    assert all(
        failure.action == RECORD_REJECTED_ACTION
        for failure in result.type_conversion_failures
    )


def test_quality_flags_are_nullable_pipe_delimited_exact_tokens() -> None:
    read_result = read_occurrence_rows(QUALITY_RULES_FIXTURE_DIR)
    result = normalize_occurrence_records(read_result.records)

    assert not read_result.has_errors
    assert result.counts.source_records == 20
    assert result.counts.accepted_records == 20
    assert result.counts.rejected_records == 0

    records_by_id = {
        record.occurrence_id: record for record in result.accepted_records
    }
    assert records_by_id["q-no-flags"].quality_flags is None
    assert records_by_id["q-no-flags"].has_quality_flags is False

    missing_date_tokens = records_by_id["q-missing-date"].quality_flags.split("|")
    assert missing_date_tokens == ["missing_event_date"]
    assert "missing_event" not in missing_date_tokens

    assert records_by_id["q-missing-uncertainty"].quality_flags.split("|") == [
        "missing_coordinate_uncertainty"
    ]
    assert records_by_id["q-missing-datum"].quality_flags.split("|") == [
        "missing_geodetic_datum"
    ]
    assert records_by_id["q-missing-name"].quality_flags.split("|") == [
        "missing_scientific_name"
    ]
    assert records_by_id["q-multiple-flags"].quality_flags.split("|") == [
        "missing_event_date",
        "missing_coordinate_uncertainty",
    ]

    for record in result.accepted_records:
        if record.quality_flags is None:
            continue
        for token in record.quality_flags.split("|"):
            assert token == token.lower()
            assert "|" not in token


def test_optional_conversion_failures_are_counted_and_warn_at_five_percent() -> None:
    read_result = read_occurrence_rows(QUALITY_RULES_FIXTURE_DIR)
    result = normalize_occurrence_records(read_result.records)

    records_by_id = {
        record.occurrence_id: record for record in result.accepted_records
    }
    invalid_uncertainty = records_by_id["q-invalid-uncertainty"]
    assert invalid_uncertainty.coordinate_uncertainty_in_meters is None
    assert invalid_uncertainty.quality_flags == "invalid_coordinate_uncertainty"

    invalid_year = records_by_id["q-invalid-year"]
    assert invalid_year.event_year is None
    assert invalid_year.quality_flags == "missing_event_date|invalid_event_year"

    failures = {
        (failure.field, failure.reason_code, failure.action): failure
        for failure in result.type_conversion_failures
    }
    uncertainty_failure = failures[
        ("coordinate_uncertainty_in_meters", INVALID_FLOAT, NULL_VALUE_ACTION)
    ]
    assert uncertainty_failure.failure_count == 1
    assert uncertainty_failure.failure_rate == 0.05

    year_failure = failures[("event_year", INVALID_INTEGER, NULL_VALUE_ACTION)]
    assert year_failure.failure_count == 1
    assert year_failure.failure_rate == 0.05

    warnings = {
        (warning.field, warning.reason_code): warning
        for warning in result.warnings
    }
    assert set(warnings) == {
        ("coordinate_uncertainty_in_meters", INVALID_FLOAT),
        ("event_year", INVALID_INTEGER),
    }
    assert result.counts.warning_count == len(result.warnings) == 2


def test_required_provenance_failures_reject_records() -> None:
    record = OccurrenceSourceRecord(
        source_file="",
        source_row_number=1,
        source_data_row_number=1,
        source_record_id="bad-provenance",
        values_by_term={
            "http://rs.tdwg.org/dwc/terms/occurrenceID": "bad-provenance",
            "http://rs.tdwg.org/dwc/terms/scientificName": "Bad provenance species",
            "http://rs.tdwg.org/dwc/terms/decimalLatitude": "10",
            "http://rs.tdwg.org/dwc/terms/decimalLongitude": "20",
        },
        raw_values=(),
        field_metadata=(),
        relationship_keys={},
    )

    result = normalize_occurrence_records([record])

    assert result.counts.accepted_records == 0
    assert result.counts.rejected_records == 1
    assert result.rejected_records[0].reason_code == MISSING_REQUIRED_FIELD
    assert result.type_conversion_failures[0].field == "source_file"
    assert result.type_conversion_failures[0].reason_code == MISSING_REQUIRED_FIELD
    assert result.type_conversion_failures[0].action == RECORD_REJECTED_ACTION
