"""FlatGeobuf occurrence writer for accepted normalized records."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
import struct
import warnings
from typing import Any, Protocol

from dwca_cloud_geospatial.normalization import NormalizedOccurrenceRecord


DEFAULT_FLATGEOBUF_RELATIVE_PATH = Path("data/occurrences.fgb")
DEFAULT_GEOPACKAGE_RELATIVE_PATH = Path("data/occurrences.gpkg")
FLATGEOBUF_CRS = "OGC:CRS84"
FLATGEOBUF_DRIVER = "FlatGeobuf"
GEOPACKAGE_DRIVER = "GPKG"
GEOPACKAGE_LAYER = "occurrences"
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
class GeoPackageWriteResult:
    """Result metadata for the persistent GeoPackage staging artifact."""

    path: Path
    relative_path: Path
    record_count: int
    columns: tuple[str, ...]
    geometry_column: str
    geometry_type: str
    crs: str
    layer: str
    writer_backend: str


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
    staging_result: GeoPackageWriteResult | None = None
    generated_from_geopackage: bool = False
    helper_strategy: str | None = None


@dataclass(frozen=True)
class FlatGeobufWriterOptions:
    """Options controlling FlatGeobuf writer behavior."""

    relative_path: Path = DEFAULT_FLATGEOBUF_RELATIVE_PATH
    geopackage_relative_path: Path = DEFAULT_GEOPACKAGE_RELATIVE_PATH
    geopackage_layer: str = GEOPACKAGE_LAYER
    spatial_index: bool = True
    large_feature_count_threshold: int = LARGE_OUTPUT_FEATURE_COUNT_WARNING_THRESHOLD
    large_spatial_index_warning_bytes: int = LARGE_OUTPUT_SPATIAL_INDEX_WARNING_BYTES
    spatial_index_bytes_per_feature: int = SPATIAL_INDEX_BYTES_PER_FEATURE_ESTIMATE
    export_batch_size: int = 65_536


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


class GeoPackageFlatGeobufBackend(Protocol):
    """Backend boundary for GeoPackage-staged FlatGeobuf writes."""

    writer_backend_name: str
    helper_strategy: str

    def write_geopackage_batch(
        self,
        *,
        path: Path,
        layer: str,
        rows: Sequence[MappingRow],
        geometry_wkb: Sequence[bytes],
        append: bool,
    ) -> None:
        """Write one bounded batch into the persistent GeoPackage layer."""

    def export_flatgeobuf_from_geopackage(
        self,
        *,
        geopackage_path: Path,
        geopackage_layer: str,
        flatgeobuf_path: Path,
        layer_options: dict[str, str],
        batch_size: int,
    ) -> None:
        """Create the final FlatGeobuf from the staged GeoPackage."""


MappingRow = dict[str, Any]


def write_flatgeobuf_occurrences(
    records: Iterable[NormalizedOccurrenceRecord],
    output_directory: str | Path,
    *,
    options: FlatGeobufWriterOptions | None = None,
    backend: FlatGeobufBackend | None = None,
) -> FlatGeobufWriteResult:
    """Write accepted occurrence records to ``data/occurrences.fgb``.

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
        helper_strategy="pyogrio.write_arrow",
    )


def write_flatgeobuf_occurrences_via_geopackage(
    record_batches: Iterable[Iterable[NormalizedOccurrenceRecord]],
    output_directory: str | Path,
    *,
    options: FlatGeobufWriterOptions | None = None,
    backend: GeoPackageFlatGeobufBackend | None = None,
) -> FlatGeobufWriteResult:
    """Write FlatGeobuf through bounded GeoPackage staging batches.

    ``record_batches`` should yield already-normalized accepted records in
    bounded chunks. The persistent GeoPackage remains in the output bundle and
    is then streamed through Pyogrio/GDAL into indexed FlatGeobuf.
    """

    writer = GeoPackageStagedFlatGeobufWriter(
        output_directory,
        options=options,
        backend=backend,
    )
    for batch in record_batches:
        writer.write_batch(batch)
    return writer.finish()


class GeoPackageStagedFlatGeobufWriter:
    """Incremental writer for GeoPackage-staged FlatGeobuf generation."""

    def __init__(
        self,
        output_directory: str | Path,
        *,
        options: FlatGeobufWriterOptions | None = None,
        backend: GeoPackageFlatGeobufBackend | None = None,
    ) -> None:
        self.options = options or FlatGeobufWriterOptions()
        if not self.options.spatial_index:
            raise ValueError(
                "GeoPackage-staged FlatGeobuf generation requires spatial_index=True."
            )

        output_root = Path(output_directory)
        self.flatgeobuf_path = output_root / self.options.relative_path
        self.geopackage_path = output_root / self.options.geopackage_relative_path
        self.geopackage_path.parent.mkdir(parents=True, exist_ok=True)
        self.flatgeobuf_path.parent.mkdir(parents=True, exist_ok=True)
        if self.geopackage_path.exists():
            self.geopackage_path.unlink()
        if self.flatgeobuf_path.exists():
            self.flatgeobuf_path.unlink()

        self.backend = backend or _PyogrioGeoPackageFlatGeobufBackend()
        self.record_count = 0
        self._finished = False

    def write_batch(self, records: Iterable[NormalizedOccurrenceRecord]) -> int:
        """Append one bounded accepted-record batch to the GeoPackage."""

        if self._finished:
            raise ValueError("Cannot write records after FlatGeobuf export is finished.")
        rows = tuple(project_flatgeobuf_record(record) for record in records)
        if not rows:
            return 0
        geometry_wkb = tuple(
            _point_wkb(row["decimal_longitude"], row["decimal_latitude"])
            for row in rows
        )
        self.backend.write_geopackage_batch(
            path=self.geopackage_path,
            layer=self.options.geopackage_layer,
            rows=rows,
            geometry_wkb=geometry_wkb,
            append=self.record_count > 0,
        )
        self.record_count += len(rows)
        return len(rows)

    def finish(self) -> FlatGeobufWriteResult:
        """Export indexed FlatGeobuf from the staged GeoPackage."""

        if self._finished:
            raise ValueError("FlatGeobuf export has already finished.")
        self._finished = True
        if self.record_count == 0:
            raise ValueError("FlatGeobuf output requires at least one accepted record.")

        writer_warnings = _large_output_warnings(
            feature_count=self.record_count, options=self.options
        )
        for writer_warning in writer_warnings:
            warnings.warn(
                writer_warning.message,
                FlatGeobufLargeOutputWarning,
                stacklevel=2,
            )

        self.backend.export_flatgeobuf_from_geopackage(
            geopackage_path=self.geopackage_path,
            geopackage_layer=self.options.geopackage_layer,
            flatgeobuf_path=self.flatgeobuf_path,
            layer_options={SPATIAL_INDEX_OPTION: "YES"},
            batch_size=self.options.export_batch_size,
        )

        staging_result = GeoPackageWriteResult(
            path=self.geopackage_path,
            relative_path=self.options.geopackage_relative_path,
            record_count=self.record_count,
            columns=FLATGEOBUF_PROJECTION_COLUMNS,
            geometry_column=GEOMETRY_COLUMN,
            geometry_type=GEOMETRY_TYPE,
            crs=FLATGEOBUF_CRS,
            layer=self.options.geopackage_layer,
            writer_backend=self.backend.writer_backend_name,
        )
        return FlatGeobufWriteResult(
            path=self.flatgeobuf_path,
            relative_path=self.options.relative_path,
            record_count=self.record_count,
            columns=FLATGEOBUF_PROJECTION_COLUMNS,
            geometry_column=GEOMETRY_COLUMN,
            geometry_type=GEOMETRY_TYPE,
            crs=FLATGEOBUF_CRS,
            spatial_index=True,
            warnings=writer_warnings,
            staging_result=staging_result,
            generated_from_geopackage=True,
            helper_strategy=self.backend.helper_strategy,
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


class _PyogrioGeoPackageFlatGeobufBackend:
    """Pyogrio/GDAL backend for persistent GeoPackage-staged FlatGeobuf."""

    writer_backend_name = "pyogrio.write_arrow"
    helper_strategy = "pyogrio.open_arrow_to_write_arrow"

    def write_geopackage_batch(
        self,
        *,
        path: Path,
        layer: str,
        rows: Sequence[MappingRow],
        geometry_wkb: Sequence[bytes],
        append: bool,
    ) -> None:
        try:
            import pyarrow as pa
            import pyogrio
        except ImportError as exc:
            raise FlatGeobufDependencyError(
                "Writing GeoPackage-staged FlatGeobuf requires optional "
                "dependencies pyogrio and pyarrow with GDAL GPKG and "
                "FlatGeobuf support installed."
            ) from exc

        _require_driver(pyogrio, GEOPACKAGE_DRIVER)
        table = _arrow_table(pa, rows=rows, geometry_wkb=geometry_wkb)
        pyogrio.write_arrow(
            table,
            str(path),
            layer=layer,
            driver=GEOPACKAGE_DRIVER,
            geometry_name=GEOMETRY_COLUMN,
            geometry_type=GEOMETRY_TYPE,
            crs=FLATGEOBUF_CRS,
            append=append,
        )

    def export_flatgeobuf_from_geopackage(
        self,
        *,
        geopackage_path: Path,
        geopackage_layer: str,
        flatgeobuf_path: Path,
        layer_options: dict[str, str],
        batch_size: int,
    ) -> None:
        try:
            import pyogrio
        except ImportError as exc:
            raise FlatGeobufDependencyError(
                "Exporting FlatGeobuf from GeoPackage requires optional "
                "dependency pyogrio with GDAL GPKG and FlatGeobuf support "
                "installed."
            ) from exc

        _require_driver(pyogrio, GEOPACKAGE_DRIVER)
        _require_driver(pyogrio, FLATGEOBUF_DRIVER)
        try:
            with pyogrio.open_arrow(
                geopackage_path,
                layer=geopackage_layer,
                batch_size=batch_size,
                use_pyarrow=True,
            ) as source:
                _metadata, reader = source
                pyogrio.write_arrow(
                    reader,
                    str(flatgeobuf_path),
                    driver=FLATGEOBUF_DRIVER,
                    geometry_name=GEOMETRY_COLUMN,
                    geometry_type=GEOMETRY_TYPE,
                    crs=FLATGEOBUF_CRS,
                    layer_options=layer_options,
                )
        except Exception as exc:
            raise FlatGeobufDependencyError(
                "GDAL/Pyogrio could not create indexed FlatGeobuf from the "
                f"GeoPackage staging file: {exc}"
            ) from exc


def _require_driver(pyogrio: Any, driver: str) -> None:
    driver_mode = pyogrio.list_drivers().get(driver)
    if driver_mode is None or "w" not in driver_mode:
        raise FlatGeobufDependencyError(
            f"The installed GDAL/Pyogrio stack does not provide writable "
            f"{driver} driver support."
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
