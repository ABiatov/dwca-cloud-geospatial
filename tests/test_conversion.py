from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR, REPOSITORY_ROOT
from dwca_cloud_geospatial.bundle import MANIFEST_RELATIVE_PATH
from dwca_cloud_geospatial.conversion import (
    ConversionError,
    ConversionOptions,
    convert_dwca_archive,
)
from dwca_cloud_geospatial.flatgeobuf import DEFAULT_FLATGEOBUF_RELATIVE_PATH
from dwca_cloud_geospatial.geoparquet import (
    DEFAULT_GEOPARQUET_RELATIVE_PATH,
    GeoParquetWriterOptions,
)
from dwca_cloud_geospatial.validation import validate_output_bundle


VALID_OCCURRENCE_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "valid"
NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
CHECKLIST_FIXTURES = (
    REPOSITORY_ROOT
    / "examples"
    / "dwca"
    / "dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip",
    REPOSITORY_ROOT / "examples" / "dwca" / "dwca-appendixiibernconventionua-v1.2.zip",
    REPOSITORY_ROOT / "examples" / "dwca" / "dwca-kharkivredliastua-v1.0.zip",
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
    assert (tmp_path / "bundle" / DEFAULT_FLATGEOBUF_RELATIVE_PATH).exists()
    assert not (tmp_path / "bundle" / DEFAULT_GEOPARQUET_RELATIVE_PATH).exists()

    manifest = json.loads(
        (tmp_path / "bundle" / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert [entry["path"] for entry in manifest["files"]] == [
        "metadata/source.json",
        "metadata/processing.json",
        "exports/occurrences.fgb",
    ]


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
    assert processing["counts"]["source_records"] == 7
    assert processing["counts"]["accepted_records"] == 2
    assert processing["counts"]["rejected_records"] == 5

    validation = validate_output_bundle(tmp_path / "bundle")
    assert not validation.has_errors
