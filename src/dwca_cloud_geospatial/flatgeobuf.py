"""FlatGeobuf occurrence writer for accepted normalized records."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
import struct
import warnings
from typing import Any, Protocol

from dwca_cloud_geospatial.normalization import NormalizedOccurrenceRecord


DEFAULT_FLATGEOBUF_RELATIVE_PATH = Path("exports/occurrences.fgb")
FLATGEOBUF_CRS = "OGC:CRS84"
FLATGEOBUF_DRIVER = "FlatGeobuf"
GEOMETRY_COLUMN = "geometry"
GEOMETRY_TYPE = "Point"
SPATIAL_INDEX_OPTION = "SPATIAL_INDEX"

LARGE_OUTPUT_FEATURE_COUNT_WARNING_THRESHOLD = 1_000_000
LARGE_OUTPUT_SPATIAL_INDEX_WARNING_BYTES = 256 * 1024 * 1024
SPATIAL_INDEX_BYTES_PER_FEATURE_ESTIMATE = 64

FLATGEOBUF_PROJECTION_COLUMNS: tuple[str, ...] = (
    "source_record_id",
    "source_file",
    "source_row_number",
    "source_data_row_number",
    "occurrence_id",
    "scientific_name",
    "verbatim_scientific_name",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "taxon_rank",
    "basis_of_record",
    "degree_of_establishment",
    "iucn_red_list_category",
    "event_date",
    "event_year",
    "decimal_longitude",
    "decimal_latitude",
    "coordinate_uncertainty_in_meters",
    "country_code",
    "locality",
    "identified_by",
    "license",
    "references",
    "rights_holder",
    "dataset_name",
    "quality_flags",
    "has_quality_flags",
)

_STRING_COLUMNS = frozenset(
    column
    for column in FLATGEOBUF_PROJECTION_COLUMNS
    if column
    not in {
        "source_row_number",
        "source_data_row_number",
        "event_year",
        "decimal_longitude",
        "decimal_latitude",
        "coordinate_uncertainty_in_meters",
        "has_quality_flags",
    }
)
_INT64_COLUMNS = frozenset(
    ("source_row_number", "source_data_row_number", "event_year")
)
_FLOAT64_COLUMNS = frozenset(
    ("decimal_longitude", "decimal_latitude", "coordinate_uncertainty_in_meters")
)
_BOOL_COLUMNS = frozenset(("has_quality_flags",))


class FlatGeobufDependencyError(RuntimeError):
    """Raised when optional FlatGeobuf writer dependencies are unavailable."""


class FlatGeobufLargeOutputWarning(RuntimeWarning):
    """Warns that an indexed FlatGeobuf write may need substantial memory."""


@dataclass(frozen=True)
class FlatGeobufWriterWarning:
    """Structured non-fatal warning emitted by the FlatGeobuf writer."""

    code: str
    message: str
    feature_count: int
    estimated_spatial_index_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "feature_count": self.feature_count,
            "estimated_spatial_index_bytes": self.estimated_spatial_index_bytes,
        }


@dataclass(frozen=True)
class FlatGeobufWriteResult:
    """Result metadata for a completed FlatGeobuf occurrence write."""

    path: Path
    relative_path: Path
    record_count: int
    columns: tuple[str, ...]
    geometry_column: str
    geometry_type: str
    crs: str
    spatial_index: bool
    warnings: tuple[FlatGeobufWriterWarning, ...] = ()


@dataclass(frozen=True)
class FlatGeobufWriterOptions:
    """Options controlling FlatGeobuf writer behavior."""

    relative_path: Path = DEFAULT_FLATGEOBUF_RELATIVE_PATH
    spatial_index: bool = True
    large_feature_count_threshold: int = LARGE_OUTPUT_FEATURE_COUNT_WARNING_THRESHOLD
    large_spatial_index_warning_bytes: int = LARGE_OUTPUT_SPATIAL_INDEX_WARNING_BYTES
    spatial_index_bytes_per_feature: int = SPATIAL_INDEX_BYTES_PER_FEATURE_ESTIMATE


class FlatGeobufBackend(Protocol):
    """Backend boundary for dependency-isolated FlatGeobuf writes."""

    def write(
        self,
        *,
        path: Path,
        rows: Sequence[MappingRow],
        geometry_wkb: Sequence[bytes],
        layer_options: dict[str, str],
    ) -> None:
        """Write projected rows and WKB point geometries to ``path``."""


MappingRow = dict[str, Any]


def write_flatgeobuf_occurrences(
    records: Iterable[NormalizedOccurrenceRecord],
    output_directory: str | Path,
    *,
    options: FlatGeobufWriterOptions | None = None,
    backend: FlatGeobufBackend | None = None,
) -> FlatGeobufWriteResult:
    """Write accepted occurrence records to ``exports/occurrences.fgb``.

    The production backend uses Pyogrio/GDAL through Arrow when those optional
    dependencies are installed. Tests can inject a backend to validate the
    projection and writer options without requiring GDAL locally.
    """

    writer_options = options or FlatGeobufWriterOptions()
    output_root = Path(output_directory)
    relative_path = writer_options.relative_path
    path = output_root / relative_path

    rows = tuple(project_flatgeobuf_record(record) for record in records)
    if not rows:
        raise ValueError("FlatGeobuf output requires at least one accepted record.")

    geometry_wkb = tuple(
        _point_wkb(row["decimal_longitude"], row["decimal_latitude"]) for row in rows
    )
    writer_warnings = _large_output_warnings(
        feature_count=len(rows), options=writer_options
    )
    for writer_warning in writer_warnings:
        warnings.warn(writer_warning.message, FlatGeobufLargeOutputWarning, stacklevel=2)

    path.parent.mkdir(parents=True, exist_ok=True)
    write_backend = backend or _PyogrioArrowFlatGeobufBackend()
    write_backend.write(
        path=path,
        rows=rows,
        geometry_wkb=geometry_wkb,
        layer_options={
            SPATIAL_INDEX_OPTION: "YES" if writer_options.spatial_index else "NO"
        },
    )

    return FlatGeobufWriteResult(
        path=path,
        relative_path=relative_path,
        record_count=len(rows),
        columns=FLATGEOBUF_PROJECTION_COLUMNS,
        geometry_column=GEOMETRY_COLUMN,
        geometry_type=GEOMETRY_TYPE,
        crs=FLATGEOBUF_CRS,
        spatial_index=writer_options.spatial_index,
        warnings=writer_warnings,
    )


def project_flatgeobuf_record(record: NormalizedOccurrenceRecord) -> MappingRow:
    """Project one accepted record into the compact FlatGeobuf column set."""

    normalized = record.to_dict()
    return {column: normalized[column] for column in FLATGEOBUF_PROJECTION_COLUMNS}


def estimate_spatial_index_memory_bytes(
    feature_count: int,
    *,
    bytes_per_feature: int = SPATIAL_INDEX_BYTES_PER_FEATURE_ESTIMATE,
) -> int:
    """Estimate memory needed by GDAL's indexed FlatGeobuf write."""

    if feature_count < 0:
        raise ValueError("feature_count must be non-negative.")
    if bytes_per_feature < 0:
        raise ValueError("bytes_per_feature must be non-negative.")
    return feature_count * bytes_per_feature


def _large_output_warnings(
    *,
    feature_count: int,
    options: FlatGeobufWriterOptions,
) -> tuple[FlatGeobufWriterWarning, ...]:
    if not options.spatial_index:
        return ()

    estimated_bytes = estimate_spatial_index_memory_bytes(
        feature_count,
        bytes_per_feature=options.spatial_index_bytes_per_feature,
    )
    if (
        feature_count < options.large_feature_count_threshold
        and estimated_bytes < options.large_spatial_index_warning_bytes
    ):
        return ()

    return (
        FlatGeobufWriterWarning(
            code="large_indexed_flatgeobuf_write",
            message=(
                "Indexed FlatGeobuf write may require substantial memory: "
                f"{feature_count} features, approximately {estimated_bytes} bytes "
                "for spatial-index construction."
            ),
            feature_count=feature_count,
            estimated_spatial_index_bytes=estimated_bytes,
        ),
    )


def _point_wkb(longitude: float, latitude: float) -> bytes:
    """Return little-endian WKB for a 2D point in longitude, latitude order."""

    return struct.pack("<bIdd", 1, 1, longitude, latitude)


class _PyogrioArrowFlatGeobufBackend:
    """Pyogrio/GDAL backend using Arrow tables and WKB point geometries."""

    def write(
        self,
        *,
        path: Path,
        rows: Sequence[MappingRow],
        geometry_wkb: Sequence[bytes],
        layer_options: dict[str, str],
    ) -> None:
        try:
            import pyarrow as pa
            import pyogrio
        except ImportError as exc:
            raise FlatGeobufDependencyError(
                "Writing FlatGeobuf requires optional dependencies pyogrio and "
                "pyarrow with GDAL FlatGeobuf support installed."
            ) from exc

        if not hasattr(pyogrio, "write_arrow"):
            raise FlatGeobufDependencyError(
                "The installed pyogrio version does not provide write_arrow."
            )

        table = _arrow_table(pa, rows=rows, geometry_wkb=geometry_wkb)
        pyogrio.write_arrow(
            table,
            str(path),
            driver=FLATGEOBUF_DRIVER,
            geometry_name=GEOMETRY_COLUMN,
            geometry_type=GEOMETRY_TYPE,
            crs=FLATGEOBUF_CRS,
            layer_options=layer_options,
        )


def _arrow_table(
    pa: Any,
    *,
    rows: Sequence[MappingRow],
    geometry_wkb: Sequence[bytes],
) -> Any:
    data: dict[str, list[Any]] = {
        column: [row[column] for row in rows] for column in FLATGEOBUF_PROJECTION_COLUMNS
    }
    data[GEOMETRY_COLUMN] = list(geometry_wkb)

    fields = [_arrow_field(pa, column) for column in FLATGEOBUF_PROJECTION_COLUMNS]
    fields.append(pa.field(GEOMETRY_COLUMN, pa.binary(), nullable=False))
    return pa.Table.from_pydict(data, schema=pa.schema(fields))


def _arrow_field(pa: Any, column: str) -> Any:
    if column in _STRING_COLUMNS:
        return pa.field(column, pa.string())
    if column in _INT64_COLUMNS:
        return pa.field(column, pa.int64())
    if column in _FLOAT64_COLUMNS:
        return pa.field(column, pa.float64())
    if column in _BOOL_COLUMNS:
        return pa.field(column, pa.bool_())
    raise AssertionError(f"Unhandled FlatGeobuf column: {column}")
