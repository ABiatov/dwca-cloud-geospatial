"""Core package for the DwC-A cloud geospatial converter."""

from importlib.metadata import PackageNotFoundError, version

from dwca_cloud_geospatial.inspection import inspect_dwca
from dwca_cloud_geospatial.occurrence import (
    OccurrenceReadResult,
    OccurrenceSourceRecord,
    iter_occurrence_rows,
    read_occurrence_rows,
)

try:
    __version__ = version("dwca-cloud-geospatial")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "__version__",
    "inspect_dwca",
    "OccurrenceReadResult",
    "OccurrenceSourceRecord",
    "iter_occurrence_rows",
    "read_occurrence_rows",
]
