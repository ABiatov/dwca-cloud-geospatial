"""Core package for the DwC-A cloud geospatial converter."""

from importlib.metadata import PackageNotFoundError, version

from dwca_cloud_geospatial.flatgeobuf import (
    DEFAULT_FLATGEOBUF_RELATIVE_PATH,
    FLATGEOBUF_PROJECTION_COLUMNS,
    FlatGeobufDependencyError,
    FlatGeobufLargeOutputWarning,
    FlatGeobufWriteResult,
    FlatGeobufWriterOptions,
    FlatGeobufWriterWarning,
    estimate_spatial_index_memory_bytes,
    project_flatgeobuf_record,
    write_flatgeobuf_occurrences,
)
from dwca_cloud_geospatial.geoparquet import (
    DEFAULT_GEOPARQUET_RELATIVE_PATH,
    GEOPARQUET_PROJECTION_COLUMNS,
    GeoParquetDependencyError,
    GeoParquetWriteResult,
    GeoParquetWriterOptions,
    project_geoparquet_record,
    write_geoparquet_occurrences,
)
from dwca_cloud_geospatial.inspection import inspect_dwca
from dwca_cloud_geospatial.occurrence import (
    OccurrenceReadResult,
    OccurrenceSourceRecord,
    iter_occurrence_rows,
    read_occurrence_rows,
)
from dwca_cloud_geospatial.normalization import (
    NormalizedOccurrenceRecord,
    OccurrenceNormalizationCounts,
    OccurrenceNormalizationResult,
    OccurrenceNormalizationWarning,
    RejectedOccurrenceRecord,
    TypeConversionFailure,
    normalize_occurrence_record,
    normalize_occurrence_records,
)

try:
    __version__ = version("dwca-cloud-geospatial")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "__version__",
    "DEFAULT_FLATGEOBUF_RELATIVE_PATH",
    "DEFAULT_GEOPARQUET_RELATIVE_PATH",
    "FLATGEOBUF_PROJECTION_COLUMNS",
    "GEOPARQUET_PROJECTION_COLUMNS",
    "FlatGeobufDependencyError",
    "FlatGeobufLargeOutputWarning",
    "FlatGeobufWriteResult",
    "FlatGeobufWriterOptions",
    "FlatGeobufWriterWarning",
    "GeoParquetDependencyError",
    "GeoParquetWriteResult",
    "GeoParquetWriterOptions",
    "estimate_spatial_index_memory_bytes",
    "inspect_dwca",
    "OccurrenceReadResult",
    "OccurrenceSourceRecord",
    "NormalizedOccurrenceRecord",
    "OccurrenceNormalizationCounts",
    "OccurrenceNormalizationResult",
    "OccurrenceNormalizationWarning",
    "RejectedOccurrenceRecord",
    "TypeConversionFailure",
    "iter_occurrence_rows",
    "normalize_occurrence_record",
    "normalize_occurrence_records",
    "project_flatgeobuf_record",
    "project_geoparquet_record",
    "read_occurrence_rows",
    "write_flatgeobuf_occurrences",
    "write_geoparquet_occurrences",
]
