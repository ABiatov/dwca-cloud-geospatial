"""Manifest, metadata and report writers for static output bundles."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
from itertools import chain
import json
from pathlib import Path, PurePosixPath
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from dwca_cloud_geospatial.flatgeobuf import (
    FLATGEOBUF_PROJECTION_COLUMNS,
    FlatGeobufWriteResult,
)
from dwca_cloud_geospatial.geoparquet import (
    GEOPARQUET_PROJECTION_COLUMNS,
    GeoParquetWriteResult,
)
from dwca_cloud_geospatial.gbif import GbifDownloadMetadata
from dwca_cloud_geospatial.inspection import ArchiveInspection
from dwca_cloud_geospatial.normalization import (
    NORMALIZED_FIELD_TERMS,
    QUALITY_FLAG_CODES,
    OccurrenceNormalizationResult,
    RejectedOccurrenceRecord,
)
from dwca_cloud_geospatial.occurrence import OccurrenceReadResult, OccurrenceSourceRecord


BUNDLE_SCHEMA_VERSION = "0.1.0"
VIEWER_CONTRACT_VERSION = "0.1.0"
OCCURRENCE_SCHEMA_VERSION = "0.1.0"
DEFAULT_VIEWER_MAP_TITLE = "Custom map title, edit it in manifest.json"

MANIFEST_RELATIVE_PATH = Path("manifest.json")
SOURCE_METADATA_RELATIVE_PATH = Path("metadata/source.json")
PROCESSING_METADATA_RELATIVE_PATH = Path("metadata/processing.json")
REJECTED_RECORDS_RELATIVE_PATH = Path("reports/rejected_records.csv")

REJECTED_RECORD_COLUMNS: tuple[str, ...] = (
    "source_file",
    "source_row_number",
    "source_record_id",
    "occurrence_id",
    "scientific_name",
    "decimal_longitude",
    "decimal_latitude",
    "event_date",
    "reason_code",
    "reason_message",
    "source_data_row_number",
)

DISPLAY_FIELD_CANDIDATES: tuple[str, ...] = (
    "scientific_name",
    "verbatim_scientific_name",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "taxon_rank",
    "iucn_red_list_category",
    "event_date",
    "event_year",
    "basis_of_record",
    "degree_of_establishment",
    "decimal_longitude",
    "decimal_latitude",
    "coordinate_uncertainty_in_meters",
    "country_code",
    "locality",
    "identified_by",
    "dataset_name",
    "license",
    "references",
    "rights_holder",
    "source_record_id",
    "source_file",
    "source_row_number",
    "source_data_row_number",
    "quality_flags",
)

FILTER_FIELD_CANDIDATES: tuple[str, ...] = (
    "scientific_name",
    "kingdom",
    "event_year",
    "basis_of_record",
    "iucn_red_list_category",
    "quality_flags",
)

_GBIF_DATASET_KEY_TERMS = (
    "http://rs.gbif.org/terms/1.0/datasetKey",
    "http://rs.gbif.org/terms/1.0/dataset_key",
)
_GBIF_DOWNLOAD_KEY_TERMS = (
    "http://rs.gbif.org/terms/1.0/downloadKey",
    "http://rs.gbif.org/terms/1.0/download_key",
)
_OBIS_DATASET_ID_TERMS = (
    "http://rs.iobis.org/obis/terms/dataset_id",
    "http://rs.iobis.org/obis/terms/datasetID",
)
_OBIS_RESOURCE_ID_TERMS = ("http://rs.iobis.org/obis/terms/resource_id",)


@dataclass(frozen=True)
class BundleMetadataWriteResult:
    """Paths and summaries for written bundle metadata files."""

    output_directory: Path
    manifest_path: Path
    source_metadata_path: Path
    processing_metadata_path: Path
    rejected_records_path: Path | None
    file_inventory: tuple[dict[str, Any], ...]
    counts: dict[str, int]


@dataclass(frozen=True)
class BundleWriterOptions:
    """Options controlling manifest and metadata writer behavior."""

    bundle_id: str | None = None
    title: str | None = None
    created_at: datetime | str | None = None
    generator_name: str = "dwca-cloud-geospatial"
    generator_version: str = "0.0.0+unknown"
    generator_commit: str | None = None
    viewer_map_title: str | None = DEFAULT_VIEWER_MAP_TITLE
    configuration: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.generator_version == "0.0.0+unknown":
            object.__setattr__(self, "generator_version", _package_version())


def write_bundle_metadata(
    *,
    output_directory: str | Path,
    occurrence_result: OccurrenceReadResult,
    normalization_result: OccurrenceNormalizationResult,
    flatgeobuf_result: FlatGeobufWriteResult | None = None,
    geoparquet_result: GeoParquetWriteResult | None = None,
    rejected_records_path: str | Path | None = None,
    options: BundleWriterOptions | None = None,
    gbif_download_metadata: GbifDownloadMetadata | None = None,
    extra_warnings: Iterable[Mapping[str, Any]] = (),
) -> BundleMetadataWriteResult:
    """Write manifest, metadata JSON and optional rejected-record report."""

    writer_options = options or BundleWriterOptions()
    output_root = Path(output_directory)
    created_at = _created_at(writer_options.created_at)

    source_metadata = build_source_metadata(
        occurrence_result=occurrence_result,
        normalization_result=normalization_result,
        gbif_download_metadata=gbif_download_metadata,
    )
    source_summary = _source_summary(source_metadata)
    title = writer_options.title or source_summary["title"] or output_root.name
    bundle_id = writer_options.bundle_id or _default_bundle_id(
        output_root=output_root,
        created_at=created_at,
    )

    counts = _processing_counts(
        normalization_result=normalization_result,
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
    )
    processing_metadata = build_processing_metadata(
        occurrence_result=occurrence_result,
        normalization_result=normalization_result,
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
        options=writer_options,
        created_at=created_at,
        counts=counts,
        gbif_download_metadata=gbif_download_metadata,
        extra_warnings=extra_warnings,
    )

    source_path = output_root / SOURCE_METADATA_RELATIVE_PATH
    processing_path = output_root / PROCESSING_METADATA_RELATIVE_PATH
    _write_json(source_path, source_metadata)
    _write_json(processing_path, processing_metadata)

    rejected_path = (
        Path(rejected_records_path)
        if rejected_records_path is not None
        else write_rejected_records_csv(
            normalization_result.rejected_records,
            output_root / REJECTED_RECORDS_RELATIVE_PATH,
        )
    )

    inventory = _file_inventory(
        output_root=output_root,
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
        rejected_records_path=rejected_path,
        rejected_record_count=normalization_result.counts.rejected_records,
    )
    layers = _layers(
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
        bounds=(
            _accepted_bounds(normalization_result.accepted_records)
            or (flatgeobuf_result.bounds if flatgeobuf_result else None)
            or (geoparquet_result.bounds if geoparquet_result else None)
        ),
    )
    viewer = _viewer_defaults(
        layers=layers,
        flatgeobuf_result=flatgeobuf_result,
        map_title=writer_options.viewer_map_title,
    )
    manifest = {
        "bundle_schema_version": BUNDLE_SCHEMA_VERSION,
        "viewer_contract_version": VIEWER_CONTRACT_VERSION,
        "occurrence_schema_version": OCCURRENCE_SCHEMA_VERSION,
        "id": bundle_id,
        "title": title,
        "created_at": created_at,
        "generator": {
            "name": writer_options.generator_name,
            "version": writer_options.generator_version,
            "commit": writer_options.generator_commit,
        },
        "source": source_summary,
        "files": inventory,
        "layers": layers,
        "viewer": viewer,
        "counts": {
            "source_records": counts["source_records"],
            "accepted_records": counts["accepted_records"],
            "rejected_records": counts["rejected_records"],
            "occurrence_records": counts["accepted_records"],
        },
    }
    manifest_path = output_root / MANIFEST_RELATIVE_PATH
    _write_json(manifest_path, manifest)

    return BundleMetadataWriteResult(
        output_directory=output_root,
        manifest_path=manifest_path,
        source_metadata_path=source_path,
        processing_metadata_path=processing_path,
        rejected_records_path=rejected_path,
        file_inventory=tuple(inventory),
        counts=counts,
    )


def build_source_metadata(
    *,
    occurrence_result: OccurrenceReadResult,
    normalization_result: OccurrenceNormalizationResult,
    gbif_download_metadata: GbifDownloadMetadata | None = None,
) -> dict[str, Any]:
    """Build ``metadata/source.json`` content from parser and EML metadata."""

    inspection = occurrence_result.inspection
    eml = _read_eml_metadata(inspection)
    records = occurrence_result.records
    dataset = {
        "title": eml["title"],
        "description": eml["description"],
        "publisher": eml["publisher"] or _first_accepted_value(
            normalization_result, "publisher"
        ),
        "homepage": eml["homepage"],
        "doi": eml["doi"],
        "citation": eml["citation"],
    }
    gbif_license = gbif_download_metadata.license if gbif_download_metadata else None
    rights = {
        "license": gbif_license
        or eml["license"]
        or _first_accepted_value(normalization_result, "license"),
        "rights_holder": eml["rights_holder"]
        or _first_accepted_value(normalization_result, "rights_holder"),
        "rights": eml["rights"],
    }
    gbif = {
        "dataset_key": _first_source_value(occurrence_result, _GBIF_DATASET_KEY_TERMS),
        "download_key": (
            gbif_download_metadata.download_key
            if gbif_download_metadata and gbif_download_metadata.download_key
            else _first_source_value(occurrence_result, _GBIF_DOWNLOAD_KEY_TERMS)
        ),
        "doi": gbif_download_metadata.doi if gbif_download_metadata else None,
        "citation": gbif_download_metadata.citation if gbif_download_metadata else None,
        "license": gbif_license,
    }
    obis = {
        "dataset_id": _first_source_value(occurrence_result, _OBIS_DATASET_ID_TERMS),
        "resource_id": _first_source_value(occurrence_result, _OBIS_RESOURCE_ID_TERMS),
        "doi": None,
        "citation": None,
        "license": None,
    }
    return {
        "source_archive": {
            "path": _provenance_path(inspection.source_path),
            "name": inspection.source_path.name,
            "kind": inspection.archive_kind,
            "bytes": inspection.source_size_bytes,
            "sha256": inspection.source_sha256,
        },
        "dwca": _dwca_metadata(inspection),
        "dataset": dataset,
        "rights": rights,
        "gbif": gbif,
        "obis": obis,
        "source_files": _source_files(inspection),
    }


def build_processing_metadata(
    *,
    occurrence_result: OccurrenceReadResult,
    normalization_result: OccurrenceNormalizationResult,
    flatgeobuf_result: FlatGeobufWriteResult | None,
    geoparquet_result: GeoParquetWriteResult | None,
    options: BundleWriterOptions,
    created_at: str,
    counts: dict[str, int],
    gbif_download_metadata: GbifDownloadMetadata | None = None,
    extra_warnings: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build ``metadata/processing.json`` content."""

    configuration = _effective_configuration(
        options.configuration,
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
    )
    warnings = [
        *_processing_warnings(normalization_result, flatgeobuf_result),
        *[dict(warning) for warning in extra_warnings],
    ]
    return {
        "created_at": created_at,
        "generator": {
            "name": options.generator_name,
            "version": options.generator_version,
            "commit": options.generator_commit,
            "runtime": {"python_package": "dwca_cloud_geospatial"},
        },
        "input": {
            "path": _provenance_path(occurrence_result.inspection.source_path),
            "archive_kind": occurrence_result.inspection.archive_kind,
            "sha256": occurrence_result.inspection.source_sha256,
            "source_file": occurrence_result.source_file,
        },
        "source_provenance": {
            "gbif": _gbif_download_metadata_dict(gbif_download_metadata),
        },
        "configuration": configuration,
        "configuration_hash": _configuration_hash(configuration),
        "output_decisions": _output_decisions(
            flatgeobuf_result=flatgeobuf_result,
            geoparquet_result=geoparquet_result,
        ),
        "field_mapping": _field_mapping(),
        "quality_rules": {
            "version": OCCURRENCE_SCHEMA_VERSION,
            "coordinate_crs": "OGC:CRS84",
            "coordinate_order": "longitude_latitude",
            "reject_zero_zero": True,
            "quality_flag_codes": list(QUALITY_FLAG_CODES),
        },
        "counts": {**counts, "warning_count": len(warnings)},
        "type_conversion_failures": [
            failure.to_dict()
            for failure in normalization_result.type_conversion_failures
        ],
        "warnings": warnings,
        "validation": {
            "status": "not_run",
            "errors": [],
            "warnings": [],
            "checked_files": [],
        },
        "parser_diagnostics": [
            asdict(diagnostic) for diagnostic in occurrence_result.diagnostics
        ],
    }


def _gbif_download_metadata_dict(
    metadata: GbifDownloadMetadata | None,
) -> dict[str, str | None]:
    return {
        "download_key": metadata.download_key if metadata else None,
        "doi": metadata.doi if metadata else None,
        "citation": metadata.citation if metadata else None,
        "license": metadata.license if metadata else None,
    }


def write_rejected_records_csv(
    rejected_records: Iterable[RejectedOccurrenceRecord],
    path: str | Path,
) -> Path | None:
    """Write ``reports/rejected_records.csv`` when rejected rows exist."""

    iterator = iter(rejected_records)
    first_record = next(iterator, None)
    if first_record is None:
        return None

    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=REJECTED_RECORD_COLUMNS)
        writer.writeheader()
        for record in chain((first_record,), iterator):
            row = record.to_dict()
            writer.writerow({column: row.get(column) for column in REJECTED_RECORD_COLUMNS})
    return csv_path


class RejectedRecordsCsvWriter:
    """Lazy CSV writer for rejected records emitted by chunked normalization."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.record_count = 0
        self._file_obj: Any | None = None
        self._writer: csv.DictWriter | None = None

    @property
    def written_path(self) -> Path | None:
        return self.path if self.record_count else None

    def write_many(self, rejected_records: Iterable[RejectedOccurrenceRecord]) -> None:
        for record in rejected_records:
            self.write(record)

    def write(self, record: RejectedOccurrenceRecord) -> None:
        if self._writer is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file_obj = self.path.open("w", encoding="utf-8", newline="")
            self._writer = csv.DictWriter(
                self._file_obj,
                fieldnames=REJECTED_RECORD_COLUMNS,
            )
            self._writer.writeheader()
        row = record.to_dict()
        self._writer.writerow(
            {column: row.get(column) for column in REJECTED_RECORD_COLUMNS}
        )
        self.record_count += 1

    def close(self) -> None:
        if self._file_obj is not None:
            self._file_obj.close()
            self._file_obj = None
            self._writer = None


def _created_at(value: datetime | str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _package_version() -> str:
    try:
        return version("dwca-cloud-geospatial")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def _default_bundle_id(*, output_root: Path, created_at: str) -> str:
    digest = hashlib.sha256(f"{output_root.resolve()}|{created_at}".encode("utf-8"))
    return f"dwca-geo-{digest.hexdigest()[:12]}"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _processing_counts(
    *,
    normalization_result: OccurrenceNormalizationResult,
    flatgeobuf_result: FlatGeobufWriteResult | None,
    geoparquet_result: GeoParquetWriteResult | None,
) -> dict[str, int]:
    counts = normalization_result.counts
    return {
        "source_records": counts.source_records,
        "parsed_records": counts.parsed_records,
        "accepted_records": counts.accepted_records,
        "rejected_records": counts.rejected_records,
        "warning_count": counts.warning_count,
        "geoparquet_records": geoparquet_result.record_count if geoparquet_result else 0,
        "flatgeobuf_records": flatgeobuf_result.record_count if flatgeobuf_result else 0,
        "geopackage_records": (
            flatgeobuf_result.staging_result.record_count
            if flatgeobuf_result and flatgeobuf_result.staging_result
            else 0
        ),
    }


def _file_inventory(
    *,
    output_root: Path,
    flatgeobuf_result: FlatGeobufWriteResult | None,
    geoparquet_result: GeoParquetWriteResult | None,
    rejected_records_path: Path | None,
    rejected_record_count: int,
) -> list[dict[str, Any]]:
    inventory = [
        _file_entry(
            output_root=output_root,
            relative_path=SOURCE_METADATA_RELATIVE_PATH,
            role="metadata",
            media_type="application/json",
            record_count=None,
        ),
        _file_entry(
            output_root=output_root,
            relative_path=PROCESSING_METADATA_RELATIVE_PATH,
            role="metadata",
            media_type="application/json",
            record_count=None,
        ),
    ]
    if geoparquet_result is not None:
        inventory.append(
            _file_entry(
                output_root=output_root,
                relative_path=geoparquet_result.relative_path,
                role="geoparquet",
                media_type="application/vnd.apache.parquet",
                record_count=geoparquet_result.record_count,
            )
        )
    if flatgeobuf_result is not None and flatgeobuf_result.staging_result is not None:
        inventory.append(
            _file_entry(
                output_root=output_root,
                relative_path=flatgeobuf_result.staging_result.relative_path,
                role="geopackage",
                media_type="application/geopackage+sqlite3",
                record_count=flatgeobuf_result.staging_result.record_count,
            )
        )
    if flatgeobuf_result is not None:
        inventory.append(
            _file_entry(
                output_root=output_root,
                relative_path=flatgeobuf_result.relative_path,
                role="flatgeobuf",
                media_type="application/octet-stream",
                record_count=flatgeobuf_result.record_count,
            )
        )
    if rejected_records_path is not None:
        inventory.append(
            _file_entry(
                output_root=output_root,
                relative_path=REJECTED_RECORDS_RELATIVE_PATH,
                role="report",
                media_type="text/csv",
                record_count=rejected_record_count,
            )
        )
    return inventory


def _file_entry(
    *,
    output_root: Path,
    relative_path: Path,
    role: str,
    media_type: str,
    record_count: int | None,
) -> dict[str, Any]:
    path = output_root / relative_path
    return {
        "path": relative_path.as_posix(),
        "role": role,
        "media_type": media_type,
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": _sha256_file(path) if path.exists() else None,
        "record_count": record_count,
    }


def _layers(
    *,
    flatgeobuf_result: FlatGeobufWriteResult | None,
    geoparquet_result: GeoParquetWriteResult | None,
    bounds: tuple[float, float, float, float] | None,
) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    if flatgeobuf_result is not None:
        layers.append(
            _layer(
                layer_id="occurrences",
                source_format="flatgeobuf",
                relative_path=flatgeobuf_result.relative_path,
                record_count=flatgeobuf_result.record_count,
                bounds=bounds,
            )
        )
    if geoparquet_result is not None:
        layers.append(
            _layer(
                layer_id="occurrences_geoparquet",
                source_format="geoparquet",
                relative_path=geoparquet_result.relative_path,
                record_count=geoparquet_result.record_count,
                bounds=geoparquet_result.bounds,
            )
        )
    return layers


def _layer(
    *,
    layer_id: str,
    source_format: str,
    relative_path: Path,
    record_count: int,
    bounds: tuple[float, float, float, float] | None,
) -> dict[str, Any]:
    return {
        "id": layer_id,
        "title": "Occurrences",
        "type": "point",
        "source_format": source_format,
        "path": relative_path.as_posix(),
        "geometry": {
            "column": "geometry",
            "crs": "OGC:CRS84",
            "coordinate_order": "longitude_latitude",
        },
        "record_count": record_count,
        "bounds": list(bounds) if bounds is not None else None,
    }


def _viewer_defaults(
    *,
    layers: list[dict[str, Any]],
    flatgeobuf_result: FlatGeobufWriteResult | None,
    map_title: str | None,
) -> dict[str, Any]:
    columns = (
        flatgeobuf_result.columns
        if flatgeobuf_result is not None
        else GEOPARQUET_PROJECTION_COLUMNS
    )
    column_set = set(columns)
    default_layer = layers[0]["id"] if layers else None
    initial_bounds = layers[0]["bounds"] if layers else None
    viewer = {
        "default_layer": default_layer,
        "initial_bounds": initial_bounds,
        "display_fields": [
            field for field in DISPLAY_FIELD_CANDIDATES if field in column_set
        ],
        "filter_fields": [
            field for field in FILTER_FIELD_CANDIDATES if field in column_set
        ],
    }
    normalized_title = _normalize_viewer_map_title(map_title)
    if normalized_title is not None:
        viewer["map_title"] = normalized_title
    return viewer


def _normalize_viewer_map_title(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _source_summary(source_metadata: Mapping[str, Any]) -> dict[str, Any]:
    dataset = source_metadata["dataset"]
    rights = source_metadata["rights"]
    gbif = source_metadata["gbif"]
    obis = source_metadata["obis"]
    return {
        "title": dataset["title"],
        "publisher": dataset["publisher"],
        "doi": dataset["doi"] or gbif["doi"] or obis["doi"],
        "citation": dataset["citation"] or gbif["citation"] or obis["citation"],
        "license": gbif["license"] or obis["license"] or rights["license"],
        "gbif_dataset_key": gbif["dataset_key"],
        "gbif_download_key": gbif["download_key"],
        "obis_dataset_id": obis["dataset_id"],
    }


def _effective_configuration(
    user_configuration: Mapping[str, Any] | None,
    *,
    flatgeobuf_result: FlatGeobufWriteResult | None,
    geoparquet_result: GeoParquetWriteResult | None,
) -> dict[str, Any]:
    configuration: dict[str, Any] = {
        "outputs": {
            "flatgeobuf": flatgeobuf_result is not None,
            "geoparquet": geoparquet_result is not None,
        },
        "flatgeobuf": {
            "relative_path": flatgeobuf_result.relative_path.as_posix()
            if flatgeobuf_result
            else None,
            "spatial_index": flatgeobuf_result.spatial_index
            if flatgeobuf_result
            else None,
            "generated_from_geopackage": flatgeobuf_result.generated_from_geopackage
            if flatgeobuf_result
            else False,
            "helper_strategy": flatgeobuf_result.helper_strategy
            if flatgeobuf_result
            else None,
        },
        "geopackage_staging": {
            "enabled": bool(
                flatgeobuf_result is not None and flatgeobuf_result.staging_result
            ),
            "relative_path": (
                flatgeobuf_result.staging_result.relative_path.as_posix()
                if flatgeobuf_result and flatgeobuf_result.staging_result
                else None
            ),
            "writer_backend": (
                flatgeobuf_result.staging_result.writer_backend
                if flatgeobuf_result and flatgeobuf_result.staging_result
                else None
            ),
            "layer": (
                flatgeobuf_result.staging_result.layer
                if flatgeobuf_result and flatgeobuf_result.staging_result
                else None
            ),
            "flatgeobuf_generated_from_geopackage": (
                flatgeobuf_result.generated_from_geopackage
                if flatgeobuf_result
                else False
            ),
            "gdal_ogr_helper_strategy": (
                flatgeobuf_result.helper_strategy if flatgeobuf_result else None
            ),
            "flatgeobuf_spatial_index": (
                flatgeobuf_result.spatial_index if flatgeobuf_result else None
            ),
        },
        "geoparquet": {
            "relative_path": geoparquet_result.relative_path.as_posix()
            if geoparquet_result
            else None,
            "row_group_size": geoparquet_result.row_group_size
            if geoparquet_result
            else None,
            "compression": geoparquet_result.compression if geoparquet_result else None,
            "large_output_mode": geoparquet_result.large_output_mode
            if geoparquet_result
            else False,
            "covering_bbox_column": {
                "enabled": geoparquet_result.covering_bbox_column
                if geoparquet_result
                else False,
                "strategy": "point_bbox_struct"
                if geoparquet_result and geoparquet_result.covering_bbox_column
                else None,
                "threshold": None,
            },
            "spatial_sorting": {
                "enabled": geoparquet_result.spatial_sorting
                if geoparquet_result
                else False,
                "strategy": geoparquet_result.spatial_sort_strategy
                if geoparquet_result
                else None,
                "threshold": None,
            },
            "partitioned_dataset": {
                "enabled": geoparquet_result.partitioned_dataset
                if geoparquet_result
                else False,
                "partition_key": geoparquet_result.partition_key
                if geoparquet_result
                else None,
                "threshold": geoparquet_result.partition_threshold
                if geoparquet_result
                else None,
            },
        },
    }
    if user_configuration:
        configuration["user"] = dict(user_configuration)
    return configuration


def _output_decisions(
    *,
    flatgeobuf_result: FlatGeobufWriteResult | None,
    geoparquet_result: GeoParquetWriteResult | None,
) -> dict[str, Any]:
    staging_result = flatgeobuf_result.staging_result if flatgeobuf_result else None
    return {
        "geopackage_staging_enabled": staging_result is not None,
        "geopackage_staging_relative_path": (
            staging_result.relative_path.as_posix() if staging_result else None
        ),
        "geopackage_staging_writer_backend": (
            staging_result.writer_backend if staging_result else None
        ),
        "flatgeobuf_generated_from_geopackage": (
            flatgeobuf_result.generated_from_geopackage if flatgeobuf_result else False
        ),
        "gdal_ogr_helper_strategy": (
            flatgeobuf_result.helper_strategy if flatgeobuf_result else None
        ),
        "flatgeobuf_spatial_index": (
            flatgeobuf_result.spatial_index if flatgeobuf_result else None
        ),
        "geoparquet_written": geoparquet_result is not None,
    }


def _configuration_hash(configuration: Mapping[str, Any]) -> str:
    encoded = json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _field_mapping() -> dict[str, Any]:
    mappings = {}
    for field, terms in NORMALIZED_FIELD_TERMS.items():
        output_field = "class" if field == "class_" else field
        mappings[output_field] = list(terms)
    return {
        "version": OCCURRENCE_SCHEMA_VERSION,
        "normalized_fields": mappings,
    }


def _processing_warnings(
    normalization_result: OccurrenceNormalizationResult,
    flatgeobuf_result: FlatGeobufWriteResult | None,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for warning in normalization_result.warnings:
        payload = warning.to_dict()
        payload["stage"] = "normalization"
        warnings.append(payload)
    if flatgeobuf_result is not None:
        for warning in flatgeobuf_result.warnings:
            payload = warning.to_dict()
            payload.update(
                {
                    "stage": "flatgeobuf_writer",
                    "field": None,
                    "reason_code": None,
                    "failure_count": None,
                    "failure_rate": None,
                }
            )
            warnings.append(payload)
    return warnings


def _accepted_bounds(
    records: Iterable[Any],
) -> tuple[float, float, float, float] | None:
    bounds: tuple[float, float, float, float] | None = None
    for record in records:
        lon = record.decimal_longitude
        lat = record.decimal_latitude
        if bounds is None:
            bounds = (lon, lat, lon, lat)
        else:
            west, south, east, north = bounds
            bounds = (min(west, lon), min(south, lat), max(east, lon), max(north, lat))
    return bounds


def _dwca_metadata(inspection: ArchiveInspection) -> dict[str, Any]:
    metadata = inspection.metadata
    core = metadata.core if metadata else None
    return {
        "meta_path": inspection.meta_path,
        "metadata_file": metadata.metadata_file if metadata else None,
        "archive_kind": inspection.archive_kind,
        "core": _table_summary(core),
        "occurrence_core": _table_summary(metadata.occurrence_core)
        if metadata and metadata.occurrence_core
        else None,
        "extensions": [
            _table_summary(extension) for extension in metadata.extensions
        ]
        if metadata
        else [],
        "coordinate_terms_present": metadata.coordinate_terms_present
        if metadata
        else {},
    }


def _provenance_path(path: Path) -> str:
    resolved_path = path.resolve()
    cwd = Path.cwd().resolve()
    try:
        return resolved_path.relative_to(cwd).as_posix()
    except ValueError:
        return str(resolved_path)


def _table_summary(table: Any) -> dict[str, Any] | None:
    if table is None:
        return None
    return {
        "role": table.role,
        "row_type": table.row_type,
        "files": list(table.files),
        "id_index": table.id_index,
        "coreid_index": table.coreid_index,
        "field_count": len(table.fields),
        "fields": [
            {
                "term": field.term,
                "index": field.index,
                "default": field.default,
                "delimited_by": field.delimited_by,
            }
            for field in table.fields
        ],
        "text_format": asdict(table.text_format),
    }


def _source_files(inspection: ArchiveInspection) -> list[dict[str, Any]]:
    metadata = inspection.metadata
    if metadata is None:
        return []
    files: list[dict[str, Any]] = []
    if metadata.metadata_file:
        files.append({"path": metadata.metadata_file, "role": "metadata"})
    if metadata.core:
        files.extend(
            {"path": file_path, "role": "core", "row_type": metadata.core.row_type}
            for file_path in metadata.core.files
        )
    for extension in metadata.extensions:
        files.extend(
            {
                "path": file_path,
                "role": "extension",
                "row_type": extension.row_type,
            }
            for file_path in extension.files
        )
    return files


def _read_eml_metadata(inspection: ArchiveInspection) -> dict[str, str | None]:
    empty = {
        "title": None,
        "description": None,
        "publisher": None,
        "homepage": None,
        "doi": None,
        "citation": None,
        "license": None,
        "rights_holder": None,
        "rights": None,
    }
    metadata_file = inspection.metadata.metadata_file if inspection.metadata else None
    if metadata_file is None or not _is_safe_archive_path(metadata_file):
        return empty

    try:
        if inspection.archive_kind == "directory":
            eml_bytes = (inspection.source_path / metadata_file).read_bytes()
        elif inspection.archive_kind == "zip":
            member = _zip_declared_member(inspection, metadata_file)
            with zipfile.ZipFile(inspection.source_path) as archive:
                eml_bytes = archive.read(member)
        else:
            return empty
    except (KeyError, OSError, zipfile.BadZipFile):
        return empty

    try:
        root = ET.fromstring(eml_bytes)
    except ET.ParseError:
        return empty

    dataset = _first_descendant(root, "dataset")
    if dataset is None:
        dataset = root
    title = _text_at(dataset, ("title",)) or _text_at(root, ("title",))
    description = (
        _text_at(dataset, ("abstract", "para"))
        or _text_at(dataset, ("description", "para"))
        or _text_at(dataset, ("abstract",))
        or _text_at(dataset, ("description",))
    )
    publisher = (
        _text_at(dataset, ("publisher", "organizationName"))
        or _text_at(dataset, ("creator", "organizationName"))
        or _text_at(dataset, ("creator", "individualName", "surName"))
    )
    homepage = (
        _text_at(dataset, ("distribution", "online", "url"))
        or _text_at(dataset, ("online", "url"))
        or _text_at(dataset, ("url",))
    )
    rights = _text_at(dataset, ("intellectualRights", "para")) or _text_at(
        dataset, ("intellectualRights",)
    )
    return {
        "title": title,
        "description": description,
        "publisher": publisher,
        "homepage": homepage,
        "doi": _doi_from_dataset(dataset),
        "citation": _text_at(dataset, ("citation",)),
        "license": _text_at(dataset, ("licensed", "licenseName")),
        "rights_holder": publisher,
        "rights": rights,
    }


def _zip_declared_member(inspection: ArchiveInspection, declared_file: str) -> str:
    if inspection.meta_path and "/" in inspection.meta_path:
        return f"{inspection.meta_path.rsplit('/', 1)[0]}/{declared_file}"
    return declared_file


def _doi_from_dataset(dataset: ET.Element) -> str | None:
    for element in _descendants(dataset, "alternateIdentifier"):
        text = _element_text(element)
        if text and ("doi" in text.lower() or "/" in text):
            return text
    return _text_at(dataset, ("doi",))


def _first_accepted_value(
    normalization_result: OccurrenceNormalizationResult, field: str
) -> str | None:
    summary_values = normalization_result.first_accepted_values or {}
    value = summary_values.get(field)
    if value:
        return value
    for record in normalization_result.accepted_records:
        value = getattr(record, field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_source_value(
    occurrence_result: OccurrenceReadResult,
    terms: Iterable[str],
) -> str | None:
    summary_values = occurrence_result.first_source_values or {}
    for term in terms:
        value = summary_values.get(term)
        if value:
            return value
    for record in occurrence_result.records:
        for term in terms:
            value = record.value_for_term(term)
            if value and value.strip():
                return value.strip()
    return None


def _text_at(root: ET.Element, path: tuple[str, ...]) -> str | None:
    element = root
    for local_name in path:
        next_element = _first_child(element, local_name)
        if next_element is None:
            return None
        element = next_element
    return _element_text(element)


def _first_descendant(root: ET.Element, local_name: str) -> ET.Element | None:
    for element in _descendants(root, local_name):
        return element
    return None


def _descendants(root: ET.Element, local_name: str) -> Iterable[ET.Element]:
    for element in root.iter():
        if _local_name(element.tag) == local_name:
            yield element


def _first_child(root: ET.Element, local_name: str) -> ET.Element | None:
    for child in root:
        if _local_name(child.tag) == local_name:
            return child
    return None


def _element_text(element: ET.Element) -> str | None:
    text = " ".join(part.strip() for part in element.itertext() if part.strip())
    return text or None


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _is_safe_archive_path(path: str) -> bool:
    if not path or "\\" in path or path.startswith(("/", "\\")):
        return False
    if "//" in path or path.split("/", 1)[0].endswith(":"):
        return False
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute():
        return False
    return all(part not in ("", ".", "..") for part in pure_path.parts)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
