from __future__ import annotations

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR, REPOSITORY_ROOT
from dwca_cloud_geospatial.inspection import (
    DECIMAL_LATITUDE_TERM,
    DECIMAL_LONGITUDE_TERM,
)
from dwca_cloud_geospatial.occurrence import read_occurrence_rows


VALID_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "valid"
MALFORMED_ROW_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "malformed_row"
MULTI_FILE_CORE_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "multi_file_core"
CHECKLIST_EXAMPLE_ZIP = (
    REPOSITORY_ROOT
    / "examples"
    / "dwca"
    / "dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip"
)


def test_occurrence_rows_are_read_through_declared_field_terms() -> None:
    result = read_occurrence_rows(VALID_FIXTURE_DIR)

    assert not result.has_errors
    assert result.source_file == "occurrence.txt"
    assert result.rows_read == 1
    assert result.parse_failures == 0

    record = result.records[0]
    assert record.source_file == "occurrence.txt"
    assert record.source_row_number == 2
    assert record.source_data_row_number == 1
    assert record.source_record_id == "occ-1"
    assert record.relationship_keys == {"_id": "occ-1"}
    assert record.value_for_term("http://rs.tdwg.org/dwc/terms/scientificName") == (
        "Example species"
    )
    assert record.value_for_term(DECIMAL_LATITUDE_TERM) == "38.7223"
    assert record.value_for_term(DECIMAL_LONGITUDE_TERM) == "-9.1393"
    assert record.value_for_term("http://rs.tdwg.org/dwc/terms/geodeticDatum") == "WGS84"
    assert record.raw_values == ("occ-1", "Example species", "38.7223", "-9.1393")
    assert {field.term for field in record.field_metadata} >= {
        "http://rs.tdwg.org/dwc/terms/occurrenceID",
        DECIMAL_LATITUDE_TERM,
        DECIMAL_LONGITUDE_TERM,
    }


def test_checklist_archive_is_not_read_as_occurrence_rows() -> None:
    result = read_occurrence_rows(CHECKLIST_EXAMPLE_ZIP)

    assert result.inspection.metadata is not None
    assert not result.inspection.metadata.has_occurrence_core
    assert result.records == ()
    assert result.has_errors
    assert any(
        diagnostic.code == "missing_occurrence_core"
        for diagnostic in result.diagnostics
    )


def test_malformed_occurrence_row_reports_source_context() -> None:
    result = read_occurrence_rows(MALFORMED_ROW_FIXTURE_DIR)

    assert result.records == ()
    assert result.rows_read == 0
    assert result.parse_failures == 1

    diagnostic = result.diagnostics[-1]
    assert diagnostic.code == "occurrence_row_parse_error"
    assert diagnostic.source == str(MALFORMED_ROW_FIXTURE_DIR)
    assert diagnostic.context == "occurrence.txt:2"


def test_multi_file_occurrence_core_is_deferred() -> None:
    result = read_occurrence_rows(MULTI_FILE_CORE_FIXTURE_DIR)

    assert result.records == ()
    assert result.has_errors
    diagnostic_codes = {diagnostic.code for diagnostic in result.diagnostics}
    assert "unsupported_multiple_table_files" in diagnostic_codes
    assert "unsupported_multiple_occurrence_core_files" in diagnostic_codes
