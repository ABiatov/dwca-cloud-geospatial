"""GeoParquet occurrence writer for accepted normalized records."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import struct
from typing import Any

from dwca_cloud_geospatial.normalization import NormalizedOccurrenceRecord


DEFAULT_GEOPARQUET_RELATIVE_PATH = Path("data/occurrences.parquet")
GEOPARQUET_VERSION = "1.1.0"
GEOPARQUET_CRS = "OGC:CRS84"
GEOPARQUET_COMPRESSION = "zstd"
GEOPARQUET_DEFAULT_ROW_GROUP_SIZE = 100_000
GEOMETRY_COLUMN = "geometry"
GEOMETRY_TYPE = "Point"
GEOMETRY_ENCODING = "WKB"
COORDINATE_ORDER = "longitude_latitude"

GEOPARQUET_ATTRIBUTE_COLUMNS: tuple[str, ...] = (
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
    "taxon_id",
    "taxon_rank",
    "identified_by",
    "basis_of_record",
    "degree_of_establishment",
    "event_date",
    "event_year",
    "recorded_by",
    "decimal_longitude",
    "decimal_latitude",
    "coordinate_uncertainty_in_meters",
    "geodetic_datum",
    "country_code",
    "locality",
    "dataset_name",
    "dataset_key",
    "publisher",
    "license",
    "rights_holder",
    "references",
    "quality_flags",
    "has_quality_flags",
    "iucn_red_list_category",
    "catalog_number",
    "collection_code",
    "institution_code",
    "record_number",
    "organism_id",
    "gbif_id",
    "obis_id",
    "raw_decimal_longitude",
    "raw_decimal_latitude",
    "raw_event_date",
)
GEOPARQUET_PROJECTION_COLUMNS: tuple[str, ...] = (
    *GEOPARQUET_ATTRIBUTE_COLUMNS,
    GEOMETRY_COLUMN,
)

_STRING_COLUMNS = frozenset(
    column
    for column in GEOPARQUET_ATTRIBUTE_COLUMNS
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

MappingRow = dict[str, Any]
Bounds = tuple[float, float, float, float]


class GeoParquetDependencyError(RuntimeError):
    """Raised when PyArrow is unavailable for GeoParquet writing."""


@dataclass(frozen=True)
class GeoParquetWriteResult:
    """Result metadata for a completed GeoParquet occurrence write."""

    path: Path
    relative_path: Path
    record_count: int
    columns: tuple[str, ...]
    geometry_column: str
    geometry_type: str
    geometry_encoding: str
    crs: str
    coordinate_order: str
    bounds: Bounds
    row_group_size: int
    compression: str
    geoparquet_version: str


@dataclass(frozen=True)
class GeoParquetWriterOptions:
    """Options controlling GeoParquet writer behavior."""

    relative_path: Path = DEFAULT_GEOPARQUET_RELATIVE_PATH
    row_group_size: int = GEOPARQUET_DEFAULT_ROW_GROUP_SIZE
    compression: str = GEOPARQUET_COMPRESSION


def write_geoparquet_occurrences(
    records: Iterable[NormalizedOccurrenceRecord],
    output_directory: str | Path,
    *,
    options: GeoParquetWriterOptions | None = None,
) -> GeoParquetWriteResult:
    """Write accepted occurrence records to ``data/occurrences.parquet``.

    Records are projected and written in Arrow batches capped by
    ``row_group_size`` so callers do not need to materialize the whole
    occurrence collection before handing it to the writer.
    """

    writer_options = options or GeoParquetWriterOptions()
    if writer_options.row_group_size <= 0:
        raise ValueError("GeoParquet row_group_size must be positive.")

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise GeoParquetDependencyError(
            "Writing GeoParquet requires optional dependency pyarrow installed."
        ) from exc

    output_root = Path(output_directory)
    relative_path = writer_options.relative_path
    path = output_root / relative_path

    writer = None
    bounds: Bounds | None = None
    record_count = 0
    rows: list[MappingRow] = []
    geometry_wkb: list[bytes] = []
    schema = _arrow_schema(pa)

    def flush() -> None:
        nonlocal writer
        if not rows:
            return
        if writer is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            writer = pq.ParquetWriter(
                path,
                schema,
                compression=writer_options.compression,
                write_statistics=True,
                use_dictionary=True,
            )
        table = _arrow_table(pa, rows=rows, geometry_wkb=geometry_wkb, schema=schema)
        writer.write_table(table, row_group_size=writer_options.row_group_size)
        rows.clear()
        geometry_wkb.clear()

    try:
        for record in records:
            row = project_geoparquet_record(record)
            rows.append(row)
            geometry_wkb.append(
                _point_wkb(row["decimal_longitude"], row["decimal_latitude"])
            )
            bounds = _extend_bounds(
                bounds,
                longitude=row["decimal_longitude"],
                latitude=row["decimal_latitude"],
            )
            record_count += 1
            if len(rows) >= writer_options.row_group_size:
                flush()

        if record_count == 0 or bounds is None:
            raise ValueError("GeoParquet output requires at least one accepted record.")

        flush()
        if writer is None:
            raise AssertionError("GeoParquet writer was not initialized.")
        writer.add_key_value_metadata(
            {"geo": json.dumps(_geo_metadata(bounds), separators=(",", ":"))}
        )
    finally:
        if writer is not None:
            writer.close()

    return GeoParquetWriteResult(
        path=path,
        relative_path=relative_path,
        record_count=record_count,
        columns=GEOPARQUET_PROJECTION_COLUMNS,
        geometry_column=GEOMETRY_COLUMN,
        geometry_type=GEOMETRY_TYPE,
        geometry_encoding=GEOMETRY_ENCODING,
        crs=GEOPARQUET_CRS,
        coordinate_order=COORDINATE_ORDER,
        bounds=bounds,
        row_group_size=writer_options.row_group_size,
        compression=writer_options.compression,
        geoparquet_version=GEOPARQUET_VERSION,
    )


def project_geoparquet_record(record: NormalizedOccurrenceRecord) -> MappingRow:
    """Project one accepted record into the analytical GeoParquet column set."""

    normalized = record.to_dict()
    return {column: normalized[column] for column in GEOPARQUET_ATTRIBUTE_COLUMNS}


def _arrow_table(
    pa: Any,
    *,
    rows: Sequence[MappingRow],
    geometry_wkb: Sequence[bytes],
    schema: Any,
) -> Any:
    data: dict[str, list[Any]] = {
        column: [row[column] for row in rows] for column in GEOPARQUET_ATTRIBUTE_COLUMNS
    }
    data[GEOMETRY_COLUMN] = list(geometry_wkb)
    return pa.Table.from_pydict(data, schema=schema)


def _arrow_schema(pa: Any) -> Any:
    fields = [_arrow_field(pa, column) for column in GEOPARQUET_ATTRIBUTE_COLUMNS]
    fields.append(pa.field(GEOMETRY_COLUMN, pa.binary(), nullable=False))
    return pa.schema(fields)


def _arrow_field(pa: Any, column: str) -> Any:
    if column in _STRING_COLUMNS:
        return pa.field(column, pa.string())
    if column in _INT64_COLUMNS:
        return pa.field(column, pa.int64())
    if column in _FLOAT64_COLUMNS:
        return pa.field(column, pa.float64())
    if column in _BOOL_COLUMNS:
        return pa.field(column, pa.bool_())
    raise AssertionError(f"Unhandled GeoParquet column: {column}")


def _point_wkb(longitude: float, latitude: float) -> bytes:
    """Return little-endian WKB for a 2D point in longitude, latitude order."""

    return struct.pack("<bIdd", 1, 1, longitude, latitude)


def _extend_bounds(
    bounds: Bounds | None,
    *,
    longitude: float,
    latitude: float,
) -> Bounds:
    if bounds is None:
        return (longitude, latitude, longitude, latitude)
    west, south, east, north = bounds
    return (
        min(west, longitude),
        min(south, latitude),
        max(east, longitude),
        max(north, latitude),
    )


def _geo_metadata(bounds: Bounds) -> dict[str, Any]:
    return {
        "version": GEOPARQUET_VERSION,
        "primary_column": GEOMETRY_COLUMN,
        "columns": {
            GEOMETRY_COLUMN: {
                "encoding": GEOMETRY_ENCODING,
                "geometry_types": [GEOMETRY_TYPE],
                "crs": _ogc_crs84_projjson(),
                "edges": "planar",
                "bbox": list(bounds),
            }
        },
    }


def _ogc_crs84_projjson() -> dict[str, Any]:
    return {
        "$schema": "https://proj.org/schemas/v0.5/projjson.schema.json",
        "type": "GeographicCRS",
        "name": "WGS 84 longitude-latitude",
        "datum": {
            "type": "GeodeticReferenceFrame",
            "name": "World Geodetic System 1984",
            "ellipsoid": {
                "name": "WGS 84",
                "semi_major_axis": 6378137,
                "inverse_flattening": 298.257223563,
            },
        },
        "coordinate_system": {
            "subtype": "ellipsoidal",
            "axis": [
                {
                    "name": "Geodetic longitude",
                    "abbreviation": "Lon",
                    "direction": "east",
                    "unit": "degree",
                },
                {
                    "name": "Geodetic latitude",
                    "abbreviation": "Lat",
                    "direction": "north",
                    "unit": "degree",
                },
            ],
        },
        "id": {
            "authority": "OGC",
            "code": "CRS84",
        },
    }
