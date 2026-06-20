from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from dwca_cloud_geospatial.conversion import FLATGEOBUF_FORMAT, GEOPARQUET_FORMAT
from dwca_cloud_geospatial.gui import (
    GuiConversionRequest,
    build_conversion_options,
    conversion_warning_lines,
    format_conversion_summary,
    format_validation_summary,
    parse_chunk_size,
    selected_output_formats,
    validate_conversion_request,
    viewer_instructions,
)
from dwca_cloud_geospatial.validation import (
    BundleValidationCheck,
    BundleValidationIssue,
    BundleValidationResult,
)


def test_selected_output_formats_match_cli_defaults() -> None:
    assert selected_output_formats(flatgeobuf=True, geoparquet=False) == (
        FLATGEOBUF_FORMAT,
    )
    assert selected_output_formats(flatgeobuf=True, geoparquet=True) == (
        FLATGEOBUF_FORMAT,
        GEOPARQUET_FORMAT,
    )

    with pytest.raises(ValueError, match="Select at least one"):
        selected_output_formats(flatgeobuf=False, geoparquet=False)


def test_build_conversion_options_preserves_core_api_options(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    archive.write_text("placeholder", encoding="utf-8")
    output = tmp_path / "bundle"
    request = GuiConversionRequest(
        input_path=archive,
        output_directory=output,
        output_formats=(GEOPARQUET_FORMAT,),
        overwrite=True,
        geoparquet_large_output_mode=True,
        chunk_size=7,
    )

    options = build_conversion_options(request)

    assert options.output_formats == (GEOPARQUET_FORMAT,)
    assert options.overwrite is True
    assert options.geoparquet.large_output_mode is True
    assert options.gbif.enrich is True
    assert options.chunk_size == 7


def test_build_conversion_options_supports_disabling_gbif_enrichment(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "archive.zip"
    archive.write_text("placeholder", encoding="utf-8")
    request = GuiConversionRequest(
        input_path=archive,
        output_directory=tmp_path / "bundle",
        output_formats=(FLATGEOBUF_FORMAT,),
        gbif_enrich=False,
    )

    options = build_conversion_options(request)

    assert options.gbif.enrich is False


def test_existing_output_requires_overwrite_checkbox(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    archive.write_text("placeholder", encoding="utf-8")
    output = tmp_path / "bundle"
    output.mkdir()
    request = GuiConversionRequest(
        input_path=archive,
        output_directory=output,
        output_formats=(FLATGEOBUF_FORMAT,),
        overwrite=False,
    )

    with pytest.raises(ValueError, match="overwrite checkbox"):
        validate_conversion_request(request)


def test_geoparquet_large_output_mode_requires_geoparquet(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    archive.write_text("placeholder", encoding="utf-8")
    request = GuiConversionRequest(
        input_path=archive,
        output_directory=tmp_path / "bundle",
        output_formats=(FLATGEOBUF_FORMAT,),
        geoparquet_large_output_mode=True,
    )

    with pytest.raises(ValueError, match="requires GeoParquet output"):
        validate_conversion_request(request)


def test_parse_chunk_size_requires_positive_integer() -> None:
    assert parse_chunk_size("1000") == 1000
    with pytest.raises(ValueError, match="positive integer"):
        parse_chunk_size("0")
    with pytest.raises(ValueError, match="positive integer"):
        parse_chunk_size("abc")


def test_conversion_summary_separates_warnings_and_staging_artifacts() -> None:
    processing_path = Path("/tmp/bundle/metadata/processing.json")
    result = SimpleNamespace(
        input_path=Path("/tmp/archive.zip"),
        output_directory=Path("/tmp/bundle"),
        output_formats=(FLATGEOBUF_FORMAT,),
        accepted_record_count=2,
        rejected_record_count=1,
        metadata_result=SimpleNamespace(
            manifest_path=Path("/tmp/bundle/manifest.json"),
            processing_metadata_path=processing_path,
        ),
        normalization_result=SimpleNamespace(
            warnings=(
                SimpleNamespace(
                    code="optional_conversion_failure_rate",
                    message="Optional field failed conversion.",
                ),
            )
        ),
        flatgeobuf_result=SimpleNamespace(
            path=Path("/tmp/bundle/data/occurrences.fgb"),
            staging_result=SimpleNamespace(
                path=Path("/tmp/bundle/data/occurrences.gpkg")
            ),
            warnings=(
                SimpleNamespace(
                    code="large_indexed_flatgeobuf_write",
                    message="Indexed FlatGeobuf write may require substantial memory.",
                    feature_count=5_000_000,
                    estimated_spatial_index_bytes=320_000_000,
                ),
            ),
        ),
        geoparquet_result=None,
    )

    warning_lines = conversion_warning_lines(result)
    summary = format_conversion_summary(result)

    assert "optional_conversion_failure_rate" in warning_lines[0]
    assert "large_indexed_flatgeobuf_write" in warning_lines[1]
    assert "Non-fatal conversion warnings" in summary
    assert "GeoPackage staging artifact" in summary
    assert "occurrences.gpkg" in summary


def test_conversion_warning_lines_include_gbif_processing_warnings(
    tmp_path: Path,
) -> None:
    processing_path = tmp_path / "processing.json"
    processing_path.write_text(
        (
            '{"warnings": ['
            '{"code": "gbif_download_metadata_lookup_failed", '
            '"stage": "gbif_download_metadata", '
            '"message": "GBIF download citation request failed"}'
            "]}"
        ),
        encoding="utf-8",
    )
    result = SimpleNamespace(
        normalization_result=SimpleNamespace(warnings=()),
        flatgeobuf_result=None,
        metadata_result=SimpleNamespace(processing_metadata_path=processing_path),
    )

    warning_lines = conversion_warning_lines(result)

    assert warning_lines == [
        "gbif_download_metadata_lookup_failed: GBIF download citation request failed"
    ]


def test_validation_summary_separates_errors_warnings_and_skips(tmp_path: Path) -> None:
    result = BundleValidationResult(
        bundle_root=tmp_path / "bundle",
        status="failed",
        errors=(
            BundleValidationIssue(
                code="required_file_missing",
                message="Required file is missing.",
                severity="error",
                path="manifest.json",
            ),
        ),
        warnings=(
            BundleValidationIssue(
                code="optional_reader_unavailable",
                message="Optional reader unavailable.",
                severity="warning",
                check="geoparquet_io",
            ),
        ),
        checks=(
            BundleValidationCheck(
                name="geoparquet_io",
                status="skipped",
                path="data/occurrences.parquet",
                message="dependency not installed",
            ),
        ),
        checked_files=(),
    )

    summary = format_validation_summary(result)

    assert "Required validation errors: 1" in summary
    assert "Validation warnings: 1" in summary
    assert "Dependency-dependent skipped checks: 1" in summary
    assert "geoparquet_io" in summary


def test_viewer_instructions_distinguish_flatgeobuf_and_geoparquet_only() -> None:
    flatgeobuf_result = SimpleNamespace(
        output_directory=Path("/tmp/sample-bundle"),
        flatgeobuf_result=SimpleNamespace(),
    )
    geoparquet_result = SimpleNamespace(
        output_directory=Path("/tmp/geoparquet-bundle"),
        flatgeobuf_result=None,
    )

    flatgeobuf_text = viewer_instructions(flatgeobuf_result)
    geoparquet_text = viewer_instructions(geoparquet_result)

    assert "data/occurrences.fgb" in flatgeobuf_text
    assert "not the MVP browser map source" in flatgeobuf_text
    assert "GeoParquet-only bundle is valid" in geoparquet_text
    assert "no MVP browser map layer" in geoparquet_text
    assert "does not start a backend" in geoparquet_text
