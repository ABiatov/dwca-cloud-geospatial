from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPOSITORY_ROOT / "tests" / "fixtures"
DWCA_FIXTURES_DIR = FIXTURES_DIR / "dwca"
MINIMAL_OCCURRENCE_FIXTURE_DIR = DWCA_FIXTURES_DIR / "minimal_occurrence"
OUTPUT_BUNDLE_FIXTURES_DIR = FIXTURES_DIR / "output_bundles"
