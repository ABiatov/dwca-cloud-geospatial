from __future__ import annotations

import pytest

from conftest import MINIMAL_OCCURRENCE_FIXTURE_DIR
from dwca_cloud_geospatial.cli import COMMAND_NOT_IMPLEMENTED, build_parser, main


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
    exit_code = main(["inspect", str(MINIMAL_OCCURRENCE_FIXTURE_DIR / "valid")])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Occurrence core: yes" in captured.out
    assert "decimalLatitude=yes" in captured.out
    assert "Diagnostics: none" in captured.out


def test_placeholder_commands_return_clear_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["convert", "/explicit/path/to/archive.zip", "/explicit/path/to/output"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert COMMAND_NOT_IMPLEMENTED in captured.err
