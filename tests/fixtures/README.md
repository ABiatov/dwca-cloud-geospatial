# Test Fixtures

Tests should address fixtures through absolute paths derived from
`tests/conftest.py`, not through the process working directory.

Fixture data in this directory is intentionally small and local. Tests that need
real DwC-A ZIP inputs should keep those archives here, not under ignored example
data directories.
