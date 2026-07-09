from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import DWCA_FIXTURES_DIR, MINIMAL_OCCURRENCE_FIXTURE_DIR
from dwca_cloud_geospatial.cli import build_parser, main
import dwca_cloud_geospatial.cli as cli_module


VALID_OCCURRENCE_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "valid"
NORMALIZATION_FIXTURE_DIR = MINIMAL_OCCURRENCE_FIXTURE_DIR / "normalization"
CHECKLIST_FIXTURES = (
    DWCA_FIXTURES_DIR / "dwca-appendixiibernconventionua-v1.2.zip",
)


def test_top_level_help_exits_successfully(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 0
    assert "Convert local Darwin Core Archive datasets" in captured.out
    assert "inspect" in captured.out
    assert "convert" in captured.out
    assert "validate" in captured.out


def test_parser_exposes_expected_subcommands() -> None:
    parser = build_parser()

    help_text = parser.format_help()

    assert "dwca-cloud-geospatial" in help_text
    assert "COMMAND" in help_text


def test_convert_help_documents_large_geoparquet_and_chunk_size(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["convert", "--help"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 0
    assert "--geoparquet-large-output" in captured.out
    assert "--chunk-size" in captured.out
    assert "--viewer-map-title" in captured.out


def test_convert_command_passes_gbif_citation_options_to_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_options = {}

    class DummyMetadataResult:
        manifest_path = tmp_path / "bundle" / "manifest.json"

    class DummyResult:
        input_path = VALID_OCCURRENCE_FIXTURE_DIR
        output_directory = tmp_path / "bundle"
        output_formats = ("flatgeobuf",)
        accepted_record_count = 1
        rejected_record_count = 0
        metadata_result = DummyMetadataResult()

    def fake_convert(archive: str, output: str, *, options):
        captured_options["archive"] = archive
        captured_options["output"] = output
        captured_options["options"] = options
        return DummyResult()

    monkeypatch.setattr(cli_module, "convert_dwca_archive", fake_convert)

    exit_code = main(
        [
            "convert",
            str(VALID_OCCURRENCE_FIXTURE_DIR),
            str(tmp_path / "bundle"),
            "--gbif-download-key",
            "0038004-260519110011954",
            "--gbif-doi",
            "https://doi.org/10.15468/dl.3xbk5b",
            "--gbif-citation",
            "GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b",
            "--gbif-license",
            "CC_BY_NC_4_0",
            "--gbif-enrich",
        ]
    )

    capsys.readouterr()
    options = captured_options["options"]
    assert exit_code == 0
    assert options.gbif.download_key == "0038004-260519110011954"
    assert options.gbif.doi == "https://doi.org/10.15468/dl.3xbk5b"
    assert options.gbif.citation.startswith("GBIF.org (4 June 2026)")
    assert options.gbif.license == "CC_BY_NC_4_0"
    assert options.gbif.enrich is True


def test_convert_command_passes_viewer_map_title_to_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_options = {}

    class DummyMetadataResult:
        manifest_path = tmp_path / "bundle" / "manifest.json"

    class DummyResult:
        input_path = VALID_OCCURRENCE_FIXTURE_DIR
        output_directory = tmp_path / "bundle"
        output_formats = ("flatgeobuf",)
        accepted_record_count = 1
        rejected_record_count = 0
        metadata_result = DummyMetadataResult()

    def fake_convert(archive: str, output: str, *, options):
        captured_options["options"] = options
        return DummyResult()

    monkeypatch.setattr(cli_module, "convert_dwca_archive", fake_convert)

    exit_code = main(
        [
            "convert",
            str(VALID_OCCURRENCE_FIXTURE_DIR),
            str(tmp_path / "bundle"),
            "--viewer-map-title",
            "Publisher-facing map title",
        ]
    )

    capsys.readouterr()
    options = captured_options["options"]
    assert exit_code == 0
    assert options.bundle.viewer_map_title == "Publisher-facing map title"


def test_convert_command_passes_large_geoparquet_options_to_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_options = {}

    class DummyMetadataResult:
        manifest_path = tmp_path / "bundle" / "manifest.json"

    class DummyResult:
        input_path = VALID_OCCURRENCE_FIXTURE_DIR
        output_directory = tmp_path / "bundle"
        output_formats = ("geoparquet",)
        accepted_record_count = 1
        rejected_record_count = 0
        metadata_result = DummyMetadataResult()

    def fake_convert(archive: str, output: str, *, options):
        captured_options["archive"] = archive
        captured_options["output"] = output
        captured_options["options"] = options
        return DummyResult()

    monkeypatch.setattr(cli_module, "convert_dwca_archive", fake_convert)

    exit_code = main(
        [
            "convert",
            str(VALID_OCCURRENCE_FIXTURE_DIR),
            str(tmp_path / "bundle"),
            "--format",
            "geoparquet",
            "--geoparquet-large-output",
            "--chunk-size",
            "2",
            "--overwrite",
        ]
    )

    capsys.readouterr()
    options = captured_options["options"]
    assert exit_code == 0
    assert options.output_formats == ("geoparquet",)
    assert options.overwrite is True
    assert options.geoparquet.large_output_mode is True
    assert options.chunk_size == 2


def test_convert_command_preserves_repeated_format_with_large_geoparquet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_options = {}

    class DummyMetadataResult:
        manifest_path = tmp_path / "bundle" / "manifest.json"

    class DummyResult:
        input_path = VALID_OCCURRENCE_FIXTURE_DIR
        output_directory = tmp_path / "bundle"
        output_formats = ("flatgeobuf", "geoparquet")
        accepted_record_count = 1
        rejected_record_count = 0
        metadata_result = DummyMetadataResult()

    def fake_convert(archive: str, output: str, *, options):
        captured_options["options"] = options
        return DummyResult()

    monkeypatch.setattr(cli_module, "convert_dwca_archive", fake_convert)

    exit_code = main(
        [
            "convert",
            str(VALID_OCCURRENCE_FIXTURE_DIR),
            str(tmp_path / "bundle"),
            "--format",
            "flatgeobuf",
            "--format",
            "geoparquet",
            "--geoparquet-large-output",
        ]
    )

    capsys.readouterr()
    options = captured_options["options"]
    assert exit_code == 0
    assert options.output_formats == ("flatgeobuf", "geoparquet")
    assert options.geoparquet.large_output_mode is True
    assert options.chunk_size == 10_000


@pytest.mark.parametrize("chunk_size", ["0", "-1", "abc"])
def test_convert_command_rejects_invalid_chunk_sizes(
    chunk_size: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "convert",
                str(VALID_OCCURRENCE_FIXTURE_DIR),
                str(tmp_path / "bundle"),
                "--chunk-size",
                chunk_size,
            ]
        )

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "chunk size must be a positive integer" in captured.err


def test_convert_command_rejects_large_geoparquet_without_geoparquet_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("conversion should not start")

    monkeypatch.setattr(cli_module, "convert_dwca_archive", fail_if_called)

    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "convert",
                str(VALID_OCCURRENCE_FIXTURE_DIR),
                str(tmp_path / "bundle"),
                "--geoparquet-large-output",
            ]
        )

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "requires GeoParquet output" in captured.err
    assert "--format geoparquet" in captured.err


def test_inspect_command_reports_archive_structure(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["inspect", str(VALID_OCCURRENCE_FIXTURE_DIR)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Occurrence core: yes" in captured.out
    assert "decimalLatitude=yes" in captured.out
    assert "Diagnostics: none" in captured.out


@pytest.mark.parametrize("archive", CHECKLIST_FIXTURES)
def test_inspect_json_succeeds_for_checklist_archives(
    archive: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["inspect", "--json", str(archive)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["metadata"]["core"]["row_type"] == "http://rs.tdwg.org/dwc/terms/Taxon"
    assert payload["diagnostics"] == []
    assert captured.err == ""


def test_convert_command_writes_default_flatgeobuf_bundle(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pyogrio")
    pytest.importorskip("pyarrow")

    output = tmp_path / "bundle"
    exit_code = main(["convert", str(VALID_OCCURRENCE_FIXTURE_DIR), str(output)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Formats: flatgeobuf" in captured.out
    assert "Accepted records: 1" in captured.out
    assert "Viewer:" in captured.out
    assert (output / "manifest.json").exists()
    assert (output / "index.html").exists()
    assert (output / "data" / "occurrences.fgb").exists()


def test_convert_command_rejects_checklist_archive(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["convert", str(CHECKLIST_FIXTURES[0]), str(tmp_path / "bundle")])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "not an occurrence DwC-A archive" in captured.err
    assert "missing_occurrence_core" in captured.err


def test_convert_command_rejects_existing_output_without_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "bundle"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    exit_code = main(["convert", str(VALID_OCCURRENCE_FIXTURE_DIR), str(output)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Pass --overwrite" in captured.err
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_convert_command_overwrite_replaces_existing_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pyarrow")
    output = tmp_path / "bundle"
    output.mkdir()
    (output / "sentinel.txt").write_text("replace", encoding="utf-8")

    exit_code = main(
        [
            "convert",
            str(NORMALIZATION_FIXTURE_DIR),
            str(output),
            "--format",
            "geoparquet",
            "--overwrite",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Formats: geoparquet" in captured.out
    assert not (output / "sentinel.txt").exists()
    assert (output / "manifest.json").exists()
    assert (output / "index.html").exists()
    assert (output / "data" / "occurrences.parquet").exists()


def test_convert_command_writes_large_geoparquet_with_chunk_size(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    output = tmp_path / "bundle"

    exit_code = main(
        [
            "convert",
            str(NORMALIZATION_FIXTURE_DIR),
            str(output),
            "--format",
            "geoparquet",
            "--geoparquet-large-output",
            "--chunk-size",
            "2",
            "--overwrite",
        ]
    )

    captured = capsys.readouterr()
    processing = json.loads(
        (output / "metadata" / "processing.json").read_text(encoding="utf-8")
    )
    parquet_file = pq.ParquetFile(output / "data" / "occurrences.parquet")
    table = parquet_file.read()
    geo_metadata = json.loads(
        parquet_file.metadata.metadata[b"geo"].decode("utf-8")
    )

    assert exit_code == 0
    assert "Formats: geoparquet" in captured.out
    assert processing["configuration"]["geoparquet"]["large_output_mode"] is True
    assert processing["configuration"]["geoparquet"]["covering_bbox_column"] == {
        "enabled": True,
        "strategy": "point_bbox_struct",
        "threshold": None,
    }
    assert processing["configuration"]["geoparquet"]["spatial_sorting"] == {
        "enabled": True,
        "strategy": "grid",
        "threshold": None,
    }
    assert processing["configuration"]["user"]["chunk_size"] == 2
    assert processing["counts"]["accepted_records"] == 2
    assert table.schema.field("bbox").type == pa.struct(
        [
            pa.field("xmin", pa.float64(), nullable=False),
            pa.field("ymin", pa.float64(), nullable=False),
            pa.field("xmax", pa.float64(), nullable=False),
            pa.field("ymax", pa.float64(), nullable=False),
        ]
    )
    assert geo_metadata["columns"]["geometry"]["covering"]["bbox"] == {
        "xmin": ["bbox", "xmin"],
        "ymin": ["bbox", "ymin"],
        "xmax": ["bbox", "xmax"],
        "ymax": ["bbox", "ymax"],
    }


def test_validate_command_reports_structured_results(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pyarrow")
    output = tmp_path / "bundle"
    assert (
        main(
            [
                "convert",
                str(NORMALIZATION_FIXTURE_DIR),
                str(output),
                "--format",
                "geoparquet",
            ]
        )
        == 0
    )
    capsys.readouterr()

    exit_code = main(["validate", "--json", str(output)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] in {"passed", "passed_with_warnings"}
    assert payload["errors"] == []
