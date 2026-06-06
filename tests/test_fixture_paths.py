from __future__ import annotations

from pathlib import Path

from conftest import (
    DWCA_FIXTURES_DIR,
    FIXTURES_DIR,
    MINIMAL_OCCURRENCE_FIXTURE_DIR,
    OUTPUT_BUNDLE_FIXTURES_DIR,
    REPOSITORY_ROOT,
)


def test_fixture_paths_are_explicit_absolute_paths() -> None:
    fixture_paths = [
        FIXTURES_DIR,
        DWCA_FIXTURES_DIR,
        MINIMAL_OCCURRENCE_FIXTURE_DIR,
        OUTPUT_BUNDLE_FIXTURES_DIR,
    ]

    for fixture_path in fixture_paths:
        assert fixture_path.is_absolute()
        assert fixture_path.exists()
        assert fixture_path.is_relative_to(REPOSITORY_ROOT)


def test_minimal_occurrence_fixture_has_layout_marker() -> None:
    marker_path = MINIMAL_OCCURRENCE_FIXTURE_DIR / "README.md"

    assert marker_path == Path(
        REPOSITORY_ROOT,
        "tests",
        "fixtures",
        "dwca",
        "minimal_occurrence",
        "README.md",
    )
    assert marker_path.exists()
