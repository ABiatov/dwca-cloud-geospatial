from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from conftest import DWCA_FIXTURES_DIR, MINIMAL_OCCURRENCE_FIXTURE_DIR
from dwca_cloud_geospatial.inspection import (
    DECIMAL_LATITUDE_TERM,
    DECIMAL_LONGITUDE_TERM,
    OCCURRENCE_ROW_TYPE,
    inspect_dwca,
)


VALID_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "valid"
MISSING_META_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "missing_meta"
MALFORMED_META_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "malformed_meta"
EXAMPLE_ZIP = DWCA_FIXTURES_DIR / "0038004-260519110011954.zip"


def test_valid_unpacked_archive_inspection_parses_meta_xml() -> None:
    inspection = inspect_dwca(VALID_FIXTURE_DIR)

    assert not inspection.has_errors
    assert inspection.archive_kind == "directory"
    assert inspection.meta_path == "meta.xml"
    assert inspection.metadata is not None

    metadata = inspection.metadata
    assert metadata.has_occurrence_core
    assert metadata.occurrence_core is not None
    assert metadata.occurrence_core.row_type == OCCURRENCE_ROW_TYPE
    assert metadata.occurrence_core.files == ("occurrence.txt",)
    assert metadata.occurrence_core.id_index == 0
    assert metadata.occurrence_core.text_format.fields_terminated_by == "\t"
    assert metadata.occurrence_core.text_format.fields_enclosed_by is None
    assert metadata.occurrence_core.text_format.ignore_header_lines == 1
    assert metadata.coordinate_terms_present == {
        DECIMAL_LATITUDE_TERM: True,
        DECIMAL_LONGITUDE_TERM: True,
    }

    latitude = metadata.occurrence_core.field_for_term(DECIMAL_LATITUDE_TERM)
    longitude = metadata.occurrence_core.field_for_term(DECIMAL_LONGITUDE_TERM)
    datum = metadata.occurrence_core.field_for_term(
        "http://rs.tdwg.org/dwc/terms/geodeticDatum"
    )

    assert latitude is not None
    assert longitude is not None
    assert datum is not None
    assert latitude.index == 2
    assert longitude.index == 3
    assert datum.index is None
    assert datum.default == "WGS84"


def test_example_zip_archive_can_be_inspected_without_extraction() -> None:
    inspection = inspect_dwca(EXAMPLE_ZIP)

    assert not inspection.has_errors
    assert inspection.archive_kind == "zip"
    assert inspection.source_size_bytes is not None
    assert inspection.source_sha256 is not None
    assert inspection.meta_path == "meta.xml"
    assert inspection.metadata is not None
    assert inspection.metadata.has_occurrence_core
    assert inspection.metadata.occurrence_core is not None
    assert inspection.metadata.occurrence_core.field_for_term(DECIMAL_LATITUDE_TERM).index == 97
    assert inspection.metadata.occurrence_core.field_for_term(DECIMAL_LONGITUDE_TERM).index == 98


def test_missing_meta_xml_reports_source_context() -> None:
    inspection = inspect_dwca(MISSING_META_FIXTURE_DIR)

    assert inspection.has_errors
    assert inspection.metadata is None
    assert inspection.diagnostics[0].code == "missing_meta_xml"
    assert inspection.diagnostics[0].source == str(MISSING_META_FIXTURE_DIR)
    assert inspection.diagnostics[0].context == "meta.xml"


def test_malformed_meta_xml_reports_metadata_context() -> None:
    inspection = inspect_dwca(MALFORMED_META_FIXTURE_DIR)

    assert inspection.has_errors
    assert inspection.metadata is None
    assert inspection.diagnostics[0].code == "malformed_metadata"
    assert inspection.diagnostics[0].source == "meta.xml"


def test_zip_path_traversal_entry_is_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../meta.xml", "<archive />")

    inspection = inspect_dwca(archive_path)

    assert inspection.has_errors
    assert inspection.metadata is None
    assert inspection.diagnostics[0].code == "unsafe_zip_entry_path"
    assert inspection.diagnostics[0].context == "../meta.xml"
