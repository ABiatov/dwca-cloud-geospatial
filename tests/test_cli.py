from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR, REPOSITORY_ROOT
from dwca_cloud_geospatial.cli import build_parser, main


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
    assert (output / "manifest.json").exists()
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
    assert (output / "data" / "occurrences.parquet").exists()


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
