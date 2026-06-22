"""Validation for generated static output bundles."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
from typing import Any

from dwca_cloud_geospatial.bundle import (
    BUNDLE_SCHEMA_VERSION,
    MANIFEST_RELATIVE_PATH,
    OCCURRENCE_SCHEMA_VERSION,
    PROCESSING_METADATA_RELATIVE_PATH,
    REJECTED_RECORDS_RELATIVE_PATH,
    REJECTED_RECORD_COLUMNS,
    SOURCE_METADATA_RELATIVE_PATH,
    VIEWER_CONTRACT_VERSION,
)
from dwca_cloud_geospatial.flatgeobuf import (
    FLATGEOBUF_PROJECTION_COLUMNS,
    GEOPACKAGE_LAYER,
    GEOMETRY_COLUMN as FLATGEOBUF_GEOMETRY_COLUMN,
)
from dwca_cloud_geospatial.geoparquet import (
    BBOX_COLUMN,
    GEOPARQUET_CRS,
    GEOPARQUET_PROJECTION_COLUMNS,
    GEOPARQUET_VERSION,
    GEOMETRY_COLUMN as GEOPARQUET_GEOMETRY_COLUMN,
    GEOMETRY_ENCODING,
    GEOMETRY_TYPE,
)


PASSED = "passed"
PASSED_WITH_WARNINGS = "passed_with_warnings"
FAILED = "failed"
SKIPPED = "skipped"

_QUALITY_FLAG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_CAMEL_CASE_PATTERN = re.compile(r"^[a-z]+[A-Z]")


@dataclass(frozen=True)
class BundleValidationIssue:
    """Structured validation error or warning."""

    code: str
    message: str
    severity: str
    path: str | None = None
    check: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BundleValidationCheck:
    """One validation check result for CLI, GUI and report consumers."""

    name: str
    status: str
    path: str | None = None
    tool: str | None = None
    tool_version: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BundleValidationResult:
    """Structured output-bundle validation result."""

    bundle_root: Path
    status: str
    errors: tuple[BundleValidationIssue, ...]
    warnings: tuple[BundleValidationIssue, ...]
    checks: tuple[BundleValidationCheck, ...]
    checked_files: tuple[str, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def skipped_checks(self) -> tuple[BundleValidationCheck, ...]:
        return tuple(check for check in self.checks if check.status == SKIPPED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_root": str(self.bundle_root),
            "status": self.status,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "checks": [check.to_dict() for check in self.checks],
            "checked_files": list(self.checked_files),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


class _ValidationCollector:
    def __init__(self, bundle_root: Path) -> None:
        self.bundle_root = bundle_root
        self.errors: list[BundleValidationIssue] = []
        self.warnings: list[BundleValidationIssue] = []
        self.checks: list[BundleValidationCheck] = []
        self.checked_files: set[str] = set()

    def error(
        self,
        *,
        code: str,
        message: str,
        path: str | None = None,
        check: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.errors.append(
            BundleValidationIssue(
                code=code,
                message=message,
                severity="error",
                path=path,
                check=check,
                details=details,
            )
        )

    def warning(
        self,
        *,
        code: str,
        message: str,
        path: str | None = None,
        check: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.warnings.append(
            BundleValidationIssue(
                code=code,
                message=message,
                severity="warning",
                path=path,
                check=check,
                details=details,
            )
        )

    def check(
        self,
        *,
        name: str,
        status: str,
        path: str | None = None,
        tool: str | None = None,
        tool_version: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.checks.append(
            BundleValidationCheck(
                name=name,
                status=status,
                path=path,
                tool=tool,
                tool_version=tool_version,
                message=message,
                details=details,
            )
        )
        if path is not None:
            self.checked_files.add(path)

    def result(self) -> BundleValidationResult:
        if self.errors:
            status = FAILED
        elif self.warnings or any(check.status == SKIPPED for check in self.checks):
            status = PASSED_WITH_WARNINGS
        else:
            status = PASSED
        return BundleValidationResult(
            bundle_root=self.bundle_root,
            status=status,
            errors=tuple(self.errors),
            warnings=tuple(self.warnings),
            checks=tuple(self.checks),
            checked_files=tuple(sorted(self.checked_files)),
        )


def validate_output_bundle(bundle_root: str | Path) -> BundleValidationResult:
    """Validate an output bundle directory against the MVP bundle contract."""

    root = Path(bundle_root)
    collector = _ValidationCollector(root)
    manifest = _load_required_json(
        root=root,
        relative_path=MANIFEST_RELATIVE_PATH,
        collector=collector,
        check_name="manifest_json",
    )
    source = _load_required_json(
        root=root,
        relative_path=SOURCE_METADATA_RELATIVE_PATH,
        collector=collector,
        check_name="source_metadata_json",
    )
    processing = _load_required_json(
        root=root,
        relative_path=PROCESSING_METADATA_RELATIVE_PATH,
        collector=collector,
        check_name="processing_metadata_json",
    )

    if manifest is None:
        return collector.result()

    _validate_schema_versions(manifest, collector)
    _validate_source_metadata(source, collector)
    _validate_processing_metadata(processing, collector)

    file_entries = _validate_file_inventory(root, manifest, collector)
    geospatial_columns: dict[str, set[str]] = {}
    geospatial_counts: dict[str, int] = {}

    for entry in file_entries:
        role = entry.get("role")
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            continue
        if role == "geoparquet":
            columns, row_count = _validate_geoparquet(root, entry, collector)
            if columns is not None:
                geospatial_columns[path_value] = columns
            if row_count is not None:
                geospatial_counts[path_value] = row_count
        elif role == "flatgeobuf":
            columns, row_count = _validate_flatgeobuf(root, entry, collector)
            if columns is not None:
                geospatial_columns[path_value] = columns
            if row_count is not None:
                geospatial_counts[path_value] = row_count
        elif role == "geopackage":
            columns, row_count = _validate_geopackage(root, entry, collector)
            if columns is not None:
                geospatial_columns[path_value] = columns
            if row_count is not None:
                geospatial_counts[path_value] = row_count
        elif path_value == REJECTED_RECORDS_RELATIVE_PATH.as_posix():
            report_count = _validate_rejected_report(root, entry, collector)
            if report_count is not None:
                geospatial_counts[path_value] = report_count

    _validate_layers(manifest, file_entries, geospatial_counts, collector)
    _validate_counts(manifest, processing, file_entries, geospatial_counts, collector)
    _validate_viewer_fields(manifest, geospatial_columns, collector)

    return collector.result()


def _load_required_json(
    *,
    root: Path,
    relative_path: Path,
    collector: _ValidationCollector,
    check_name: str,
) -> dict[str, Any] | None:
    relative = relative_path.as_posix()
    path = root / relative_path
    if not path.exists():
        collector.error(
            code="required_file_missing",
            message=f"Required bundle file is missing: {relative}",
            path=relative,
            check=check_name,
        )
        collector.check(name=check_name, status=FAILED, path=relative)
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        collector.error(
            code="invalid_json",
            message=f"Bundle JSON file could not be parsed: {exc}",
            path=relative,
            check=check_name,
        )
        collector.check(name=check_name, status=FAILED, path=relative)
        return None
    if not isinstance(payload, dict):
        collector.error(
            code="invalid_json_object",
            message="Bundle JSON file must contain a JSON object.",
            path=relative,
            check=check_name,
        )
        collector.check(name=check_name, status=FAILED, path=relative)
        return None
    collector.check(name=check_name, status=PASSED, path=relative)
    return payload


def _validate_schema_versions(
    manifest: dict[str, Any],
    collector: _ValidationCollector,
) -> None:
    expected = {
        "bundle_schema_version": BUNDLE_SCHEMA_VERSION,
        "viewer_contract_version": VIEWER_CONTRACT_VERSION,
        "occurrence_schema_version": OCCURRENCE_SCHEMA_VERSION,
    }
    for field, supported_version in expected.items():
        value = manifest.get(field)
        if value != supported_version:
            collector.error(
                code="unsupported_schema_version",
                message=(
                    f"Unsupported {field}: {value!r}; expected "
                    f"{supported_version!r}."
                ),
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="schema_versions",
                details={"field": field, "supported_version": supported_version},
            )
    collector.check(
        name="schema_versions",
        status=FAILED if any(error.check == "schema_versions" for error in collector.errors) else PASSED,
        path=MANIFEST_RELATIVE_PATH.as_posix(),
    )


def _validate_source_metadata(
    source: dict[str, Any] | None,
    collector: _ValidationCollector,
) -> None:
    if source is None:
        return
    required_sections = ("source_archive", "dwca", "dataset", "rights", "gbif", "obis")
    for section in required_sections:
        if not isinstance(source.get(section), dict):
            collector.error(
                code="source_metadata_section_missing",
                message=f"metadata/source.json must contain object section {section!r}.",
                path=SOURCE_METADATA_RELATIVE_PATH.as_posix(),
                check="source_metadata",
                details={"section": section},
            )
    for section, fields in {
        "gbif": ("dataset_key", "download_key", "doi", "citation", "license"),
        "obis": ("dataset_id", "resource_id", "doi", "citation", "license"),
    }.items():
        values = source.get(section)
        if not isinstance(values, dict):
            continue
        for field in fields:
            if field not in values:
                collector.error(
                    code="source_provenance_field_missing",
                    message=(
                        f"metadata/source.json {section}.{field} must be present; "
                        "null is valid when the value is unavailable."
                    ),
                    path=SOURCE_METADATA_RELATIVE_PATH.as_posix(),
                    check="source_metadata",
                    details={"section": section, "field": field},
                )
    collector.check(
        name="source_metadata",
        status=FAILED if any(error.check == "source_metadata" for error in collector.errors) else PASSED,
        path=SOURCE_METADATA_RELATIVE_PATH.as_posix(),
    )


def _validate_processing_metadata(
    processing: dict[str, Any] | None,
    collector: _ValidationCollector,
) -> None:
    if processing is None:
        return

    counts = processing.get("counts")
    warnings = processing.get("warnings")
    failures = processing.get("type_conversion_failures")
    if not isinstance(counts, dict):
        collector.error(
            code="processing_counts_missing",
            message="metadata/processing.json must contain a counts object.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
        )
        return
    if not isinstance(warnings, list):
        collector.error(
            code="processing_warnings_missing",
            message="metadata/processing.json must contain a warnings array.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
        )
        warnings = []
    if not isinstance(failures, list):
        collector.error(
            code="type_conversion_failures_missing",
            message=(
                "metadata/processing.json must contain a "
                "type_conversion_failures array."
            ),
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
        )
        failures = []

    if counts.get("warning_count") != len(warnings):
        collector.error(
            code="warning_count_mismatch",
            message=(
                "processing counts.warning_count must equal the number of "
                "processing warnings."
            ),
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
            details={
                "warning_count": counts.get("warning_count"),
                "actual_warnings": len(warnings),
            },
        )
    for index, warning in enumerate(warnings):
        _validate_processing_warning(warning, index, collector)
    parsed_records = _int_or_none(counts.get("parsed_records"))
    for index, failure in enumerate(failures):
        _validate_type_conversion_failure(failure, index, parsed_records, collector)

    collector.check(
        name="processing_metadata",
        status=FAILED if any(error.check == "processing_metadata" for error in collector.errors) else PASSED,
        path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
    )


def _validate_processing_warning(
    warning: Any,
    index: int,
    collector: _ValidationCollector,
) -> None:
    if not isinstance(warning, dict):
        collector.error(
            code="processing_warning_invalid",
            message="Processing warnings must be objects.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
            details={"index": index},
        )
        return
    for field in ("code", "message", "stage"):
        if not isinstance(warning.get(field), str) or not warning[field]:
            collector.error(
                code="processing_warning_field_invalid",
                message=f"Processing warning {index} must contain string {field!r}.",
                path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
                check="processing_metadata",
                details={"index": index, "field": field},
            )
    if warning.get("code") == "large_indexed_flatgeobuf_write":
        for nullable_field in ("field", "reason_code", "failure_count", "failure_rate"):
            if warning.get(nullable_field) is not None:
                collector.error(
                    code="flatgeobuf_warning_field_not_null",
                    message=(
                        "FlatGeobuf large indexed-write warnings must keep "
                        f"{nullable_field!r} null."
                    ),
                    path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
                    check="processing_metadata",
                    details={"index": index, "field": nullable_field},
                )
        for numeric_field in ("feature_count", "estimated_spatial_index_bytes"):
            if _int_or_none(warning.get(numeric_field)) is None:
                collector.error(
                    code="flatgeobuf_warning_metric_missing",
                    message=(
                        "FlatGeobuf large indexed-write warnings must include "
                        f"integer {numeric_field!r}."
                    ),
                    path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
                    check="processing_metadata",
                    details={"index": index, "field": numeric_field},
                )


def _validate_type_conversion_failure(
    failure: Any,
    index: int,
    parsed_records: int | None,
    collector: _ValidationCollector,
) -> None:
    if not isinstance(failure, dict):
        collector.error(
            code="type_conversion_failure_invalid",
            message="Type conversion failures must be objects.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
            details={"index": index},
        )
        return
    required = ("field", "reason_code", "failure_count", "failure_rate", "action")
    for field in required:
        if field not in failure:
            collector.error(
                code="type_conversion_failure_field_missing",
                message=f"Type conversion failure {index} is missing {field!r}.",
                path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
                check="processing_metadata",
                details={"index": index, "field": field},
            )
    failure_count = _int_or_none(failure.get("failure_count"))
    failure_rate = _float_or_none(failure.get("failure_rate"))
    if failure_count is None or failure_count < 0:
        collector.error(
            code="type_conversion_failure_count_invalid",
            message="Type conversion failure failure_count must be a non-negative integer.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
            details={"index": index},
        )
    if failure_rate is None or failure_rate < 0:
        collector.error(
            code="type_conversion_failure_rate_invalid",
            message="Type conversion failure failure_rate must be a non-negative number.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="processing_metadata",
            details={"index": index},
        )
    if parsed_records and failure_count is not None and failure_rate is not None:
        expected_rate = failure_count / parsed_records
        if abs(failure_rate - expected_rate) > 1e-12:
            collector.error(
                code="type_conversion_failure_rate_mismatch",
                message=(
                    "Type conversion failure failure_rate must equal "
                    "failure_count / parsed_records."
                ),
                path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
                check="processing_metadata",
                details={
                    "index": index,
                    "failure_rate": failure_rate,
                    "expected_rate": expected_rate,
                },
            )


def _validate_file_inventory(
    root: Path,
    manifest: dict[str, Any],
    collector: _ValidationCollector,
) -> list[dict[str, Any]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        collector.error(
            code="manifest_files_invalid",
            message="manifest.json files must be an array.",
            path=MANIFEST_RELATIVE_PATH.as_posix(),
            check="file_inventory",
        )
        collector.check(name="file_inventory", status=FAILED, path=MANIFEST_RELATIVE_PATH.as_posix())
        return []

    valid_entries: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            collector.error(
                code="manifest_file_entry_invalid",
                message="Each manifest file inventory entry must be an object.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="file_inventory",
                details={"index": index},
            )
            continue
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            collector.error(
                code="manifest_file_path_invalid",
                message="Each manifest file inventory entry must contain a relative path.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="file_inventory",
                details={"index": index},
            )
            continue
        if relative in seen_paths:
            collector.error(
                code="manifest_file_duplicate",
                message=f"manifest.files contains duplicate path: {relative}",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="file_inventory",
                details={"path": relative},
            )
        seen_paths.add(relative)
        if not _is_safe_relative_path(relative):
            collector.error(
                code="manifest_file_path_unsafe",
                message=f"manifest file path must be relative and safe: {relative}",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="file_inventory",
                details={"path": relative},
            )
            continue

        path = root / relative
        if not path.exists():
            collector.error(
                code="manifest_file_missing",
                message=f"manifest.files declares a file that does not exist: {relative}",
                path=relative,
                check="file_inventory",
            )
            continue
        valid_entries.append(entry)
        expected_size = entry.get("bytes")
        if expected_size is not None and expected_size != path.stat().st_size:
            collector.error(
                code="manifest_file_size_mismatch",
                message=f"manifest.files bytes does not match actual file size: {relative}",
                path=relative,
                check="file_inventory",
                details={"manifest_bytes": expected_size, "actual_bytes": path.stat().st_size},
            )
        expected_sha256 = entry.get("sha256")
        if expected_sha256 is not None:
            actual_sha256 = _sha256(path)
            if expected_sha256 != actual_sha256:
                collector.error(
                    code="manifest_file_checksum_mismatch",
                    message=f"manifest.files sha256 does not match file content: {relative}",
                    path=relative,
                    check="file_inventory",
                    details={"manifest_sha256": expected_sha256, "actual_sha256": actual_sha256},
                )
    inventory_paths = {entry["path"] for entry in valid_entries if isinstance(entry.get("path"), str)}
    for required_path in (
        SOURCE_METADATA_RELATIVE_PATH.as_posix(),
        PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
    ):
        if required_path not in inventory_paths:
            collector.error(
                code="required_metadata_omitted_from_inventory",
                message=f"manifest.files must include generated metadata file {required_path}.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="file_inventory",
                details={"path": required_path},
            )
    collector.check(
        name="file_inventory",
        status=FAILED if any(error.check == "file_inventory" for error in collector.errors) else PASSED,
        path=MANIFEST_RELATIVE_PATH.as_posix(),
    )
    return valid_entries


def _validate_geoparquet(
    root: Path,
    entry: dict[str, Any],
    collector: _ValidationCollector,
) -> tuple[set[str] | None, int | None]:
    relative = entry["path"]
    path = root / relative
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        collector.error(
            code="pyarrow_required",
            message="Declared GeoParquet validation requires pyarrow.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"exception": str(exc)},
        )
        collector.check(name="geoparquet_pyarrow", status=FAILED, path=relative, tool="pyarrow")
        return None, None

    tool_version = _package_version("pyarrow")
    try:
        parquet_file = pq.ParquetFile(path)
        table_schema = parquet_file.schema_arrow
        metadata = parquet_file.metadata
    except Exception as exc:
        collector.error(
            code="geoparquet_open_failed",
            message=f"Declared GeoParquet file could not be opened by PyArrow: {exc}",
            path=relative,
            check="geoparquet_pyarrow",
        )
        collector.check(
            name="geoparquet_pyarrow",
            status=FAILED,
            path=relative,
            tool="pyarrow",
            tool_version=tool_version,
        )
        return None, None

    columns = set(table_schema.names)
    row_count = metadata.num_rows
    _validate_geoparquet_schema(columns, table_schema, metadata, relative, collector, pa)
    _validate_file_record_count(entry, row_count, collector, check="geoparquet_pyarrow")
    _validate_geoparquet_quality_fields(path, relative, columns, collector, pq)
    _validate_geoparquet_bbox_values(path, relative, columns, collector, pq)
    collector.check(
        name="geoparquet_pyarrow",
        status=FAILED if any(error.path == relative and error.check == "geoparquet_pyarrow" for error in collector.errors) else PASSED,
        path=relative,
        tool="pyarrow",
        tool_version=tool_version,
        details={"row_count": row_count, "columns": sorted(columns)},
    )

    _validate_geoparquet_with_geoparquet_io(path, relative, row_count, collector)
    _validate_geoparquet_with_duckdb(path, relative, row_count, collector)
    _validate_geoparquet_with_pyogrio(path, relative, row_count, collector)
    return columns, row_count


def _validate_geoparquet_schema(
    columns: set[str],
    schema: Any,
    metadata: Any,
    relative: str,
    collector: _ValidationCollector,
    pa: Any,
) -> None:
    missing = sorted(set(GEOPARQUET_PROJECTION_COLUMNS) - columns)
    if missing:
        collector.error(
            code="geoparquet_required_columns_missing",
            message="GeoParquet file is missing required projection columns.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"missing_columns": missing},
        )
    camel_case_columns = sorted(column for column in columns if _CAMEL_CASE_PATTERN.search(column))
    if camel_case_columns:
        collector.error(
            code="normalized_columns_not_snake_case",
            message="Generated occurrence columns must use normalized snake_case names.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"columns": camel_case_columns},
        )
    if GEOPARQUET_GEOMETRY_COLUMN in columns:
        geometry_field = schema.field(GEOPARQUET_GEOMETRY_COLUMN)
        if geometry_field.type != pa.binary():
            collector.error(
                code="geoparquet_geometry_type_invalid",
                message="GeoParquet geometry column must be binary WKB.",
                path=relative,
                check="geoparquet_pyarrow",
                details={"actual_type": str(geometry_field.type)},
            )

    raw_metadata = metadata.metadata or {}
    if b"geo" not in raw_metadata:
        collector.error(
            code="geoparquet_geo_metadata_missing",
            message="GeoParquet file is missing required geo footer metadata.",
            path=relative,
            check="geoparquet_pyarrow",
        )
        return
    try:
        geo = json.loads(raw_metadata[b"geo"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        collector.error(
            code="geoparquet_geo_metadata_invalid",
            message=f"GeoParquet geo footer metadata is not valid JSON: {exc}",
            path=relative,
            check="geoparquet_pyarrow",
        )
        return

    if geo.get("version") != GEOPARQUET_VERSION:
        collector.error(
            code="geoparquet_version_unsupported",
            message=(
                f"Unsupported GeoParquet metadata version {geo.get('version')!r}; "
                f"expected {GEOPARQUET_VERSION!r}."
            ),
            path=relative,
            check="geoparquet_pyarrow",
        )
    if geo.get("primary_column") != GEOPARQUET_GEOMETRY_COLUMN:
        collector.error(
            code="geoparquet_primary_column_invalid",
            message="GeoParquet primary_column must be geometry.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"primary_column": geo.get("primary_column")},
        )
    geometry_metadata = geo.get("columns", {}).get(GEOPARQUET_GEOMETRY_COLUMN)
    if not isinstance(geometry_metadata, dict):
        collector.error(
            code="geoparquet_geometry_metadata_missing",
            message="GeoParquet geo metadata must describe the geometry column.",
            path=relative,
            check="geoparquet_pyarrow",
        )
        return
    if geometry_metadata.get("encoding") != GEOMETRY_ENCODING:
        collector.error(
            code="geoparquet_geometry_encoding_invalid",
            message=f"GeoParquet geometry encoding must be {GEOMETRY_ENCODING}.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"encoding": geometry_metadata.get("encoding")},
        )
    if GEOMETRY_TYPE not in geometry_metadata.get("geometry_types", []):
        collector.error(
            code="geoparquet_geometry_type_metadata_invalid",
            message=f"GeoParquet geometry_types must include {GEOMETRY_TYPE}.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"geometry_types": geometry_metadata.get("geometry_types")},
        )
    if not _is_crs84(geometry_metadata.get("crs")):
        collector.error(
            code="geoparquet_crs_invalid",
            message=f"GeoParquet CRS must be {GEOPARQUET_CRS}.",
            path=relative,
            check="geoparquet_pyarrow",
        )
    bbox = geometry_metadata.get("bbox")
    if bbox is not None and (
        not isinstance(bbox, list)
        or len(bbox) != 4
        or any(_float_or_none(value) is None for value in bbox)
    ):
        collector.error(
            code="geoparquet_bbox_invalid",
            message="GeoParquet geometry bbox must be an array of four numbers.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"bbox": bbox},
        )
    covering = geometry_metadata.get("covering")
    if BBOX_COLUMN in columns and not covering:
        collector.error(
            code="geoparquet_covering_bbox_metadata_missing",
            message="GeoParquet bbox column must be declared in geometry covering metadata.",
            path=relative,
            check="geoparquet_pyarrow",
        )
    if covering and BBOX_COLUMN in columns:
        _validate_bbox_column_declaration(covering, schema, relative, collector)


def _validate_bbox_column_declaration(
    covering: Any,
    schema: Any,
    relative: str,
    collector: _ValidationCollector,
) -> None:
    if not isinstance(covering, dict):
        collector.error(
            code="geoparquet_covering_bbox_invalid",
            message="GeoParquet covering metadata must be an object.",
            path=relative,
            check="geoparquet_pyarrow",
        )
        return
    bbox_field_names = {"xmin", "ymin", "xmax", "ymax"}
    try:
        bbox_field = schema.field(BBOX_COLUMN)
    except KeyError:
        collector.error(
            code="geoparquet_covering_bbox_column_missing",
            message="GeoParquet covering metadata declares bbox but no bbox column exists.",
            path=relative,
            check="geoparquet_pyarrow",
        )
        return
    if not hasattr(bbox_field.type, "num_fields"):
        collector.error(
            code="geoparquet_bbox_column_not_struct",
            message="GeoParquet bbox column must be a struct when present.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"actual_type": str(bbox_field.type)},
        )
        return
    actual_fields = {bbox_field.type[index].name for index in range(bbox_field.type.num_fields)}
    if not bbox_field_names.issubset(actual_fields):
        collector.error(
            code="geoparquet_bbox_column_fields_missing",
            message="GeoParquet bbox struct must contain xmin, ymin, xmax and ymax.",
            path=relative,
            check="geoparquet_pyarrow",
            details={"actual_fields": sorted(actual_fields)},
        )


def _validate_geoparquet_quality_fields(
    path: Path,
    relative: str,
    columns: set[str],
    collector: _ValidationCollector,
    pq: Any,
) -> None:
    if "quality_flags" not in columns:
        return
    selected_columns = ["quality_flags"]
    if "has_quality_flags" in columns:
        selected_columns.append("has_quality_flags")
    try:
        table = pq.read_table(path, columns=selected_columns)
    except Exception as exc:
        collector.error(
            code="geoparquet_quality_read_failed",
            message=f"Could not read GeoParquet quality fields: {exc}",
            path=relative,
            check="geoparquet_pyarrow",
        )
        return
    for row_index, row in enumerate(table.to_pylist()):
        quality_flags = row.get("quality_flags")
        has_quality_flags = row.get("has_quality_flags")
        _validate_quality_flag_value(
            quality_flags,
            has_quality_flags,
            row_index,
            relative,
            "geoparquet_pyarrow",
            collector,
        )


def _validate_geoparquet_bbox_values(
    path: Path,
    relative: str,
    columns: set[str],
    collector: _ValidationCollector,
    pq: Any,
) -> None:
    required = {BBOX_COLUMN, "decimal_longitude", "decimal_latitude"}
    if not required.issubset(columns):
        return
    try:
        table = pq.read_table(
            path,
            columns=[BBOX_COLUMN, "decimal_longitude", "decimal_latitude"],
        )
    except Exception as exc:
        collector.error(
            code="geoparquet_bbox_read_failed",
            message=f"Could not read GeoParquet bbox fields: {exc}",
            path=relative,
            check="geoparquet_pyarrow",
        )
        return
    for row_index, row in enumerate(table.to_pylist()):
        bbox = row.get(BBOX_COLUMN)
        lon = _float_or_none(row.get("decimal_longitude"))
        lat = _float_or_none(row.get("decimal_latitude"))
        if not isinstance(bbox, dict):
            collector.error(
                code="geoparquet_bbox_value_invalid",
                message="GeoParquet bbox values must be structs.",
                path=relative,
                check="geoparquet_pyarrow",
                details={"row_index": row_index},
            )
            return
        expected = {"xmin": lon, "xmax": lon, "ymin": lat, "ymax": lat}
        for field, expected_value in expected.items():
            actual = _float_or_none(bbox.get(field))
            if actual != expected_value:
                collector.error(
                    code="geoparquet_bbox_point_mismatch",
                    message=(
                        "Point GeoParquet bbox values must equal the row "
                        "longitude and latitude."
                    ),
                    path=relative,
                    check="geoparquet_pyarrow",
                    details={
                        "row_index": row_index,
                        "field": field,
                        "actual": actual,
                        "expected": expected_value,
                    },
                )
                return


def _validate_quality_flag_value(
    quality_flags: Any,
    has_quality_flags: Any,
    row_index: int,
    relative: str,
    check_name: str,
    collector: _ValidationCollector,
) -> None:
    if quality_flags is None:
        expected_has_flags = False
    else:
        if not isinstance(quality_flags, str):
            collector.error(
                code="quality_flags_type_invalid",
                message="quality_flags values must be nullable strings.",
                path=relative,
                check=check_name,
                details={"row_index": row_index},
            )
            return
        if quality_flags == "":
            collector.error(
                code="quality_flags_empty_string",
                message="quality_flags must be null when no flags are present, not an empty string.",
                path=relative,
                check=check_name,
                details={"row_index": row_index},
            )
        tokens = quality_flags.split("|")
        for token in tokens:
            if not token or not _QUALITY_FLAG_PATTERN.fullmatch(token):
                collector.error(
                    code="quality_flags_token_invalid",
                    message=(
                        "quality_flags must split on '|' into exact lowercase "
                        "snake_case tokens."
                    ),
                    path=relative,
                    check=check_name,
                    details={"row_index": row_index, "quality_flags": quality_flags},
                )
                break
        expected_has_flags = bool(quality_flags)
    if has_quality_flags is not None and has_quality_flags is not expected_has_flags:
        collector.error(
            code="has_quality_flags_mismatch",
            message="has_quality_flags must be true exactly when quality_flags is non-empty.",
            path=relative,
            check=check_name,
            details={
                "row_index": row_index,
                "quality_flags": quality_flags,
                "has_quality_flags": has_quality_flags,
            },
        )


def _validate_geoparquet_with_geoparquet_io(
    path: Path,
    relative: str,
    expected_rows: int,
    collector: _ValidationCollector,
) -> None:
    try:
        import geoparquet_io as gpio
    except ImportError:
        _optional_skip(
            collector,
            name="geoparquet_io",
            path=relative,
            tool="geoparquet-io",
            message="Optional geoparquet-io validation is unavailable.",
        )
        return
    tool_version = _package_version("geoparquet-io")
    try:
        table = gpio.read(path)
    except Exception as exc:
        collector.warning(
            code="optional_geoparquet_io_failed",
            message=f"Optional geoparquet-io validation could not read the file: {exc}",
            path=relative,
            check="geoparquet_io",
        )
        collector.check(
            name="geoparquet_io",
            status=SKIPPED,
            path=relative,
            tool="geoparquet-io",
            tool_version=tool_version,
            message=str(exc),
        )
        return
    if table.num_rows != expected_rows:
        collector.warning(
            code="optional_geoparquet_io_row_count_mismatch",
            message="geoparquet-io row count did not match PyArrow row count.",
            path=relative,
            check="geoparquet_io",
            details={"expected_rows": expected_rows, "actual_rows": table.num_rows},
        )
    collector.check(
        name="geoparquet_io",
        status=PASSED,
        path=relative,
        tool="geoparquet-io",
        tool_version=tool_version,
        details={
            "row_count": table.num_rows,
            "geometry_column": table.geometry_column,
            "geoparquet_version": table.geoparquet_version,
        },
    )


def _validate_geoparquet_with_duckdb(
    path: Path,
    relative: str,
    expected_rows: int,
    collector: _ValidationCollector,
) -> None:
    try:
        import duckdb
    except ImportError:
        _optional_skip(
            collector,
            name="duckdb_geoparquet",
            path=relative,
            tool="duckdb",
            message="Optional DuckDB validation is unavailable.",
        )
        return
    tool_version = _package_version("duckdb")
    try:
        with duckdb.connect(database=":memory:") as connection:
            actual_rows = connection.execute(
                "SELECT count(*) FROM read_parquet(?)",
                [str(path)],
            ).fetchone()[0]
    except Exception as exc:
        collector.warning(
            code="optional_duckdb_failed",
            message=f"Optional DuckDB validation could not read the file: {exc}",
            path=relative,
            check="duckdb_geoparquet",
        )
        collector.check(
            name="duckdb_geoparquet",
            status=SKIPPED,
            path=relative,
            tool="duckdb",
            tool_version=tool_version,
            message=str(exc),
        )
        return
    if actual_rows != expected_rows:
        collector.warning(
            code="optional_duckdb_row_count_mismatch",
            message="DuckDB row count did not match PyArrow row count.",
            path=relative,
            check="duckdb_geoparquet",
            details={"expected_rows": expected_rows, "actual_rows": actual_rows},
        )
    collector.check(
        name="duckdb_geoparquet",
        status=PASSED,
        path=relative,
        tool="duckdb",
        tool_version=tool_version,
        details={"row_count": actual_rows},
    )


def _validate_geoparquet_with_pyogrio(
    path: Path,
    relative: str,
    expected_rows: int,
    collector: _ValidationCollector,
) -> None:
    try:
        import pyogrio
    except ImportError:
        _optional_skip(
            collector,
            name="pyogrio_geoparquet",
            path=relative,
            tool="pyogrio",
            message="Optional Pyogrio/GDAL GeoParquet validation is unavailable.",
        )
        return
    tool_version = _package_version("pyogrio")
    try:
        info = pyogrio.read_info(path, force_feature_count=True, force_total_bounds=True)
    except Exception as exc:
        collector.warning(
            code="optional_pyogrio_geoparquet_skipped",
            message=(
                "Optional Pyogrio/GDAL GeoParquet validation could not inspect "
                f"the file: {exc}"
            ),
            path=relative,
            check="pyogrio_geoparquet",
        )
        collector.check(
            name="pyogrio_geoparquet",
            status=SKIPPED,
            path=relative,
            tool="pyogrio",
            tool_version=tool_version,
            message=str(exc),
        )
        return
    features = info.get("features")
    if features != expected_rows:
        collector.warning(
            code="optional_pyogrio_geoparquet_row_count_mismatch",
            message="Pyogrio/GDAL GeoParquet feature count did not match PyArrow row count.",
            path=relative,
            check="pyogrio_geoparquet",
            details={"expected_rows": expected_rows, "actual_rows": features},
        )
    collector.check(
        name="pyogrio_geoparquet",
        status=PASSED,
        path=relative,
        tool="pyogrio",
        tool_version=tool_version,
        details={"features": features, "geometry_type": info.get("geometry_type")},
    )


def _validate_flatgeobuf(
    root: Path,
    entry: dict[str, Any],
    collector: _ValidationCollector,
) -> tuple[set[str] | None, int | None]:
    relative = entry["path"]
    path = root / relative
    try:
        import pyogrio
    except ImportError:
        _optional_skip(
            collector,
            name="flatgeobuf_pyogrio",
            path=relative,
            tool="pyogrio",
            message="FlatGeobuf inspection requires optional Pyogrio/GDAL support.",
        )
        return None, None

    tool_version = _package_version("pyogrio")
    drivers = pyogrio.list_drivers()
    if drivers.get("FlatGeobuf") is None:
        _optional_skip(
            collector,
            name="flatgeobuf_pyogrio",
            path=relative,
            tool="pyogrio",
            tool_version=tool_version,
            message="The local GDAL build does not expose the FlatGeobuf driver.",
        )
        return None, None
    try:
        info = pyogrio.read_info(path, force_feature_count=True, force_total_bounds=True)
    except Exception as exc:
        collector.error(
            code="flatgeobuf_open_failed",
            message=f"Declared FlatGeobuf file could not be inspected by Pyogrio/GDAL: {exc}",
            path=relative,
            check="flatgeobuf_pyogrio",
        )
        collector.check(
            name="flatgeobuf_pyogrio",
            status=FAILED,
            path=relative,
            tool="pyogrio",
            tool_version=tool_version,
        )
        return None, None

    raw_fields = info.get("fields")
    fields = set(raw_fields.tolist() if hasattr(raw_fields, "tolist") else raw_fields or [])
    columns = set(fields)
    columns.add(FLATGEOBUF_GEOMETRY_COLUMN)
    missing = sorted(set(FLATGEOBUF_PROJECTION_COLUMNS) - fields)
    if missing:
        collector.error(
            code="flatgeobuf_required_columns_missing",
            message="FlatGeobuf file is missing required projection columns.",
            path=relative,
            check="flatgeobuf_pyogrio",
            details={"missing_columns": missing},
        )
    if info.get("geometry_type") != "Point":
        collector.error(
            code="flatgeobuf_geometry_type_invalid",
            message="FlatGeobuf geometry type must be Point.",
            path=relative,
            check="flatgeobuf_pyogrio",
            details={"geometry_type": info.get("geometry_type")},
        )
    row_count = info.get("features")
    if _int_or_none(row_count) is not None:
        row_count = int(row_count)
        _validate_file_record_count(entry, row_count, collector, check="flatgeobuf_pyogrio")
    else:
        row_count = None
    collector.check(
        name="flatgeobuf_pyogrio",
        status=FAILED if any(error.path == relative and error.check == "flatgeobuf_pyogrio" for error in collector.errors) else PASSED,
        path=relative,
        tool="pyogrio",
        tool_version=tool_version,
        details={
            "features": row_count,
            "geometry_type": info.get("geometry_type"),
            "fields": sorted(fields),
        },
    )
    return columns, row_count


def _validate_geopackage(
    root: Path,
    entry: dict[str, Any],
    collector: _ValidationCollector,
) -> tuple[set[str] | None, int | None]:
    relative = entry["path"]
    path = root / relative
    columns: set[str] | None = None
    row_count: int | None = None
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            tables = _sqlite_tables(connection)
            required_metadata = {"gpkg_contents", "gpkg_geometry_columns"}
            missing_metadata = sorted(required_metadata - tables)
            if missing_metadata:
                collector.error(
                    code="geopackage_metadata_tables_missing",
                    message="GeoPackage is missing required metadata tables.",
                    path=relative,
                    check="geopackage_sqlite",
                    details={"missing_tables": missing_metadata},
                )
            layer = _geopackage_occurrence_layer(connection, tables)
            if layer is None:
                collector.error(
                    code="geopackage_occurrence_layer_missing",
                    message="GeoPackage must contain an occurrences layer.",
                    path=relative,
                    check="geopackage_sqlite",
                )
            else:
                table_info = connection.execute(f'PRAGMA table_info("{layer}")').fetchall()
                columns = {row[1] for row in table_info}
                missing_columns = sorted(set(FLATGEOBUF_PROJECTION_COLUMNS) - columns)
                if missing_columns:
                    collector.error(
                        code="geopackage_required_columns_missing",
                        message="GeoPackage occurrence layer is missing required columns.",
                        path=relative,
                        check="geopackage_sqlite",
                        details={"missing_columns": missing_columns},
                    )
                row_count = int(
                    connection.execute(f'SELECT COUNT(*) FROM "{layer}"').fetchone()[0]
                )
                _validate_file_record_count(
                    entry,
                    row_count,
                    collector,
                    check="geopackage_sqlite",
                )
    except sqlite3.Error as exc:
        collector.error(
            code="geopackage_sqlite_open_failed",
            message=f"GeoPackage could not be opened as SQLite: {exc}",
            path=relative,
            check="geopackage_sqlite",
        )

    collector.check(
        name="geopackage_sqlite",
        status=FAILED
        if any(error.path == relative and error.check == "geopackage_sqlite" for error in collector.errors)
        else PASSED,
        path=relative,
        tool="sqlite3",
        tool_version=sqlite3.sqlite_version,
        details={
            "row_count": row_count,
            "columns": sorted(columns) if columns is not None else None,
        },
    )
    pyogrio_columns, pyogrio_count = _validate_geopackage_with_pyogrio(
        path,
        relative,
        entry,
        collector,
    )
    return pyogrio_columns or columns, pyogrio_count if pyogrio_count is not None else row_count


def _sqlite_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ).fetchall()
    return {row[0] for row in rows}


def _geopackage_occurrence_layer(
    connection: sqlite3.Connection,
    tables: set[str],
) -> str | None:
    if "gpkg_contents" in tables:
        rows = connection.execute(
            "SELECT table_name FROM gpkg_contents WHERE data_type = 'features'"
        ).fetchall()
        feature_layers = [row[0] for row in rows]
        if GEOPACKAGE_LAYER in feature_layers:
            return GEOPACKAGE_LAYER
        if len(feature_layers) == 1:
            return feature_layers[0]
    return GEOPACKAGE_LAYER if GEOPACKAGE_LAYER in tables else None


def _validate_geopackage_with_pyogrio(
    path: Path,
    relative: str,
    entry: dict[str, Any],
    collector: _ValidationCollector,
) -> tuple[set[str] | None, int | None]:
    try:
        import pyogrio
    except ImportError:
        _optional_skip(
            collector,
            name="geopackage_pyogrio",
            path=relative,
            tool="pyogrio",
            message="Optional Pyogrio/GDAL GeoPackage validation is unavailable.",
        )
        return None, None

    tool_version = _package_version("pyogrio")
    if pyogrio.list_drivers().get("GPKG") is None:
        _optional_skip(
            collector,
            name="geopackage_pyogrio",
            path=relative,
            tool="pyogrio",
            tool_version=tool_version,
            message="The local GDAL build does not expose the GeoPackage driver.",
        )
        return None, None
    try:
        info = pyogrio.read_info(
            path,
            layer=GEOPACKAGE_LAYER,
            force_feature_count=True,
            force_total_bounds=True,
        )
    except Exception as exc:
        collector.warning(
            code="optional_geopackage_pyogrio_skipped",
            message=f"Optional Pyogrio/GDAL GeoPackage validation could not inspect the file: {exc}",
            path=relative,
            check="geopackage_pyogrio",
        )
        collector.check(
            name="geopackage_pyogrio",
            status=SKIPPED,
            path=relative,
            tool="pyogrio",
            tool_version=tool_version,
            message=str(exc),
        )
        return None, None

    raw_fields = info.get("fields")
    fields = set(raw_fields.tolist() if hasattr(raw_fields, "tolist") else raw_fields or [])
    columns = set(fields)
    columns.add(FLATGEOBUF_GEOMETRY_COLUMN)
    row_count = info.get("features")
    if _int_or_none(row_count) is not None:
        row_count = int(row_count)
        _validate_file_record_count(entry, row_count, collector, check="geopackage_pyogrio")
    else:
        row_count = None
    if info.get("geometry_type") != "Point":
        collector.error(
            code="geopackage_geometry_type_invalid",
            message="GeoPackage occurrence layer geometry type must be Point.",
            path=relative,
            check="geopackage_pyogrio",
            details={"geometry_type": info.get("geometry_type")},
        )
    collector.check(
        name="geopackage_pyogrio",
        status=FAILED
        if any(error.path == relative and error.check == "geopackage_pyogrio" for error in collector.errors)
        else PASSED,
        path=relative,
        tool="pyogrio",
        tool_version=tool_version,
        details={
            "features": row_count,
            "geometry_type": info.get("geometry_type"),
            "fields": sorted(fields),
        },
    )
    return columns, row_count


def _validate_rejected_report(
    root: Path,
    entry: dict[str, Any],
    collector: _ValidationCollector,
) -> int | None:
    relative = entry["path"]
    path = root / relative
    try:
        with path.open(encoding="utf-8", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            fieldnames = reader.fieldnames or []
            rows = list(reader)
    except csv.Error as exc:
        collector.error(
            code="rejected_report_invalid_csv",
            message=f"Rejected-record report is not valid CSV: {exc}",
            path=relative,
            check="rejected_report",
        )
        collector.check(name="rejected_report", status=FAILED, path=relative)
        return None
    missing = sorted(set(REJECTED_RECORD_COLUMNS) - set(fieldnames))
    if missing:
        collector.error(
            code="rejected_report_required_columns_missing",
            message="Rejected-record report is missing required columns.",
            path=relative,
            check="rejected_report",
            details={"missing_columns": missing},
        )
    for index, row in enumerate(rows):
        if not row.get("reason_code"):
            collector.error(
                code="rejected_report_reason_code_missing",
                message="Rejected-record rows must include reason_code.",
                path=relative,
                check="rejected_report",
                details={"row_index": index},
            )
    _validate_file_record_count(entry, len(rows), collector, check="rejected_report")
    collector.check(
        name="rejected_report",
        status=FAILED if any(error.path == relative and error.check == "rejected_report" for error in collector.errors) else PASSED,
        path=relative,
        details={"row_count": len(rows), "columns": fieldnames},
    )
    return len(rows)


def _validate_layers(
    manifest: dict[str, Any],
    file_entries: list[dict[str, Any]],
    geospatial_counts: dict[str, int],
    collector: _ValidationCollector,
) -> None:
    layers = manifest.get("layers")
    if not isinstance(layers, list):
        collector.error(
            code="manifest_layers_invalid",
            message="manifest.json layers must be an array.",
            path=MANIFEST_RELATIVE_PATH.as_posix(),
            check="layers",
        )
        collector.check(name="layers", status=FAILED, path=MANIFEST_RELATIVE_PATH.as_posix())
        return
    inventory_paths = {entry.get("path") for entry in file_entries}
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            collector.error(
                code="manifest_layer_invalid",
                message="Each manifest layer must be an object.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="layers",
                details={"index": index},
            )
            continue
        layer_path = layer.get("path")
        if layer_path not in inventory_paths:
            collector.error(
                code="manifest_layer_file_not_in_inventory",
                message="Each manifest layer path must reference a manifest.files entry.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="layers",
                details={"index": index, "path": layer_path},
            )
        geometry = layer.get("geometry")
        if not isinstance(geometry, dict):
            collector.error(
                code="manifest_layer_geometry_missing",
                message="Each manifest layer must declare geometry metadata.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="layers",
                details={"index": index},
            )
        else:
            expected_geometry = {
                "column": "geometry",
                "crs": "OGC:CRS84",
                "coordinate_order": "longitude_latitude",
            }
            for field, expected in expected_geometry.items():
                if geometry.get(field) != expected:
                    collector.error(
                        code="manifest_layer_geometry_invalid",
                        message=f"Layer geometry {field} must be {expected!r}.",
                        path=MANIFEST_RELATIVE_PATH.as_posix(),
                        check="layers",
                        details={"index": index, "field": field, "actual": geometry.get(field)},
                    )
        if isinstance(layer_path, str) and layer_path in geospatial_counts:
            _validate_named_count(
                actual=geospatial_counts[layer_path],
                expected=layer.get("record_count"),
                code="manifest_layer_record_count_mismatch",
                message="Layer record_count must match the generated file row count.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="layers",
                collector=collector,
                details={"layer_path": layer_path},
            )
    collector.check(
        name="layers",
        status=FAILED if any(error.check == "layers" for error in collector.errors) else PASSED,
        path=MANIFEST_RELATIVE_PATH.as_posix(),
    )


def _validate_counts(
    manifest: dict[str, Any],
    processing: dict[str, Any] | None,
    file_entries: list[dict[str, Any]],
    file_counts: dict[str, int],
    collector: _ValidationCollector,
) -> None:
    manifest_counts = manifest.get("counts")
    processing_counts = processing.get("counts") if processing else None
    if not isinstance(manifest_counts, dict) or not isinstance(processing_counts, dict):
        return

    for field in ("source_records", "accepted_records", "rejected_records"):
        _validate_named_count(
            actual=processing_counts.get(field),
            expected=manifest_counts.get(field),
            code="manifest_processing_count_mismatch",
            message=f"manifest.counts.{field} must match processing counts.",
            path=MANIFEST_RELATIVE_PATH.as_posix(),
            check="counts",
            collector=collector,
            details={"field": field},
        )
    _validate_named_count(
        actual=manifest_counts.get("accepted_records"),
        expected=manifest_counts.get("occurrence_records"),
        code="manifest_occurrence_count_mismatch",
        message="manifest.counts.occurrence_records must equal accepted_records.",
        path=MANIFEST_RELATIVE_PATH.as_posix(),
        check="counts",
        collector=collector,
    )

    accepted = _int_or_none(processing_counts.get("accepted_records"))
    rejected = _int_or_none(processing_counts.get("rejected_records"))
    entries_by_role = {entry.get("role"): entry for entry in file_entries}
    if "geoparquet" in entries_by_role:
        path = entries_by_role["geoparquet"]["path"]
        _validate_named_count(
            actual=file_counts.get(path),
            expected=processing_counts.get("geoparquet_records"),
            code="processing_geoparquet_count_mismatch",
            message="processing geoparquet_records must match GeoParquet rows.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="counts",
            collector=collector,
        )
        if accepted is not None:
            _validate_named_count(
                actual=file_counts.get(path),
                expected=accepted,
                code="accepted_geoparquet_count_mismatch",
                message="GeoParquet row count must match accepted_records.",
                path=path,
                check="counts",
                collector=collector,
            )
    elif processing_counts.get("geoparquet_records") not in (0, None):
        collector.error(
            code="processing_geoparquet_count_without_file",
            message="processing geoparquet_records is non-zero but no GeoParquet file is declared.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="counts",
        )

    if "flatgeobuf" in entries_by_role:
        path = entries_by_role["flatgeobuf"]["path"]
        if path in file_counts:
            _validate_named_count(
                actual=file_counts[path],
                expected=processing_counts.get("flatgeobuf_records"),
                code="processing_flatgeobuf_count_mismatch",
                message="processing flatgeobuf_records must match FlatGeobuf features.",
                path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
                check="counts",
                collector=collector,
            )
            if accepted is not None:
                _validate_named_count(
                    actual=file_counts[path],
                    expected=accepted,
                    code="accepted_flatgeobuf_count_mismatch",
                    message="FlatGeobuf feature count must match accepted_records.",
                    path=path,
                    check="counts",
                    collector=collector,
                )
    elif processing_counts.get("flatgeobuf_records") not in (0, None):
        collector.error(
            code="processing_flatgeobuf_count_without_file",
            message="processing flatgeobuf_records is non-zero but no FlatGeobuf file is declared.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="counts",
        )

    if "geopackage" in entries_by_role:
        path = entries_by_role["geopackage"]["path"]
        if path in file_counts:
            _validate_named_count(
                actual=file_counts[path],
                expected=processing_counts.get("geopackage_records"),
                code="processing_geopackage_count_mismatch",
                message="processing geopackage_records must match GeoPackage rows.",
                path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
                check="counts",
                collector=collector,
            )
            if accepted is not None:
                _validate_named_count(
                    actual=file_counts[path],
                    expected=accepted,
                    code="accepted_geopackage_count_mismatch",
                    message="GeoPackage row count must match accepted_records.",
                    path=path,
                    check="counts",
                    collector=collector,
                )
            flatgeobuf_entry = entries_by_role.get("flatgeobuf")
            flatgeobuf_path = flatgeobuf_entry.get("path") if flatgeobuf_entry else None
            if isinstance(flatgeobuf_path, str) and flatgeobuf_path in file_counts:
                _validate_named_count(
                    actual=file_counts[path],
                    expected=file_counts[flatgeobuf_path],
                    code="geopackage_flatgeobuf_count_mismatch",
                    message="GeoPackage and FlatGeobuf record counts must reconcile.",
                    path=path,
                    check="counts",
                    collector=collector,
                )
    elif processing_counts.get("geopackage_records") not in (0, None):
        collector.error(
            code="processing_geopackage_count_without_file",
            message="processing geopackage_records is non-zero but no GeoPackage file is declared.",
            path=PROCESSING_METADATA_RELATIVE_PATH.as_posix(),
            check="counts",
        )

    report_path = REJECTED_RECORDS_RELATIVE_PATH.as_posix()
    report_entry = next((entry for entry in file_entries if entry.get("path") == report_path), None)
    if rejected and rejected > 0:
        if report_entry is None:
            collector.error(
                code="rejected_report_missing",
                message="Rejected records are counted but reports/rejected_records.csv is absent.",
                path=report_path,
                check="counts",
            )
        elif report_path in file_counts:
            _validate_named_count(
                actual=file_counts[report_path],
                expected=rejected,
                code="rejected_report_count_mismatch",
                message="Rejected report row count must match rejected_records.",
                path=report_path,
                check="counts",
                collector=collector,
            )
    elif report_entry is not None:
        collector.error(
            code="unexpected_rejected_report",
            message="Rejected report is present even though rejected_records is zero.",
            path=report_path,
            check="counts",
        )
    collector.check(
        name="counts",
        status=FAILED if any(error.check == "counts" for error in collector.errors) else PASSED,
        path=MANIFEST_RELATIVE_PATH.as_posix(),
    )


def _validate_viewer_fields(
    manifest: dict[str, Any],
    geospatial_columns: dict[str, set[str]],
    collector: _ValidationCollector,
) -> None:
    viewer = manifest.get("viewer")
    if not isinstance(viewer, dict):
        collector.error(
            code="manifest_viewer_invalid",
            message="manifest.viewer must be an object.",
            path=MANIFEST_RELATIVE_PATH.as_posix(),
            check="viewer_fields",
        )
        collector.check(name="viewer_fields", status=FAILED, path=MANIFEST_RELATIVE_PATH.as_posix())
        return

    available_columns = set().union(*geospatial_columns.values()) if geospatial_columns else set()
    if not available_columns:
        _optional_skip(
            collector,
            name="viewer_fields",
            path=MANIFEST_RELATIVE_PATH.as_posix(),
            message="No geospatial output columns were inspectable for viewer field validation.",
        )
        return
    for field_group in ("display_fields", "filter_fields"):
        fields = viewer.get(field_group)
        if not isinstance(fields, list) or not all(isinstance(field, str) for field in fields):
            collector.error(
                code="manifest_viewer_fields_invalid",
                message=f"manifest.viewer.{field_group} must be an array of field names.",
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="viewer_fields",
                details={"field_group": field_group},
            )
            continue
        missing = sorted(set(fields) - available_columns)
        if missing:
            collector.error(
                code="manifest_viewer_field_missing_from_data",
                message=(
                    f"manifest.viewer.{field_group} includes fields that are "
                    "not present in inspected output data."
                ),
                path=MANIFEST_RELATIVE_PATH.as_posix(),
                check="viewer_fields",
                details={"field_group": field_group, "missing_fields": missing},
            )
    collector.check(
        name="viewer_fields",
        status=FAILED if any(error.check == "viewer_fields" for error in collector.errors) else PASSED,
        path=MANIFEST_RELATIVE_PATH.as_posix(),
    )


def _validate_file_record_count(
    entry: dict[str, Any],
    actual_count: int,
    collector: _ValidationCollector,
    *,
    check: str,
) -> None:
    expected_count = entry.get("record_count")
    if expected_count is None:
        return
    _validate_named_count(
        actual=actual_count,
        expected=expected_count,
        code="manifest_file_record_count_mismatch",
        message="manifest.files record_count does not match generated file rows.",
        path=entry["path"],
        check=check,
        collector=collector,
    )


def _validate_named_count(
    *,
    actual: Any,
    expected: Any,
    code: str,
    message: str,
    path: str,
    check: str,
    collector: _ValidationCollector,
    details: dict[str, Any] | None = None,
) -> None:
    actual_int = _int_or_none(actual)
    expected_int = _int_or_none(expected)
    if actual_int is None or expected_int is None or actual_int != expected_int:
        issue_details = {"actual": actual, "expected": expected}
        if details:
            issue_details.update(details)
        collector.error(
            code=code,
            message=message,
            path=path,
            check=check,
            details=issue_details,
        )


def _optional_skip(
    collector: _ValidationCollector,
    *,
    name: str,
    path: str,
    message: str,
    tool: str | None = None,
    tool_version: str | None = None,
) -> None:
    collector.warning(
        code="optional_validation_skipped",
        message=message,
        path=path,
        check=name,
    )
    collector.check(
        name=name,
        status=SKIPPED,
        path=path,
        tool=tool,
        tool_version=tool_version,
        message=message,
    )


def _is_safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and value == path.as_posix()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _is_crs84(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value == GEOPARQUET_CRS
    if not isinstance(value, dict):
        return False
    crs_id = value.get("id")
    if isinstance(crs_id, dict):
        return crs_id.get("authority") == "OGC" and str(crs_id.get("code")) == "CRS84"
    return crs_id == GEOPARQUET_CRS


def _package_version(package_name: str) -> str | None:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None
