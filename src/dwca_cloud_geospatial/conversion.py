"""Core conversion orchestration for DwC-A output bundles."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import shutil
from typing import Any
import zipfile

from dwca_cloud_geospatial.bundle import (
    BundleMetadataWriteResult,
    BundleWriterOptions,
    REJECTED_RECORDS_RELATIVE_PATH,
    RejectedRecordsCsvWriter,
    write_bundle_metadata,
)
from dwca_cloud_geospatial.gbif import (
    GbifDownloadClient,
    GbifEnrichmentResult,
    GbifDownloadOptions,
    extract_download_key_from_eml_xml,
    infer_download_key_from_path_name,
    normalize_download_key,
    resolve_gbif_download_metadata,
)
from dwca_cloud_geospatial.flatgeobuf import (
    FlatGeobufBackend,
    FlatGeobufDependencyError,
    FlatGeobufWriteResult,
    FlatGeobufWriterOptions,
    GeoPackageStagedFlatGeobufWriter,
    write_flatgeobuf_occurrences,
)
from dwca_cloud_geospatial.geoparquet import (
    GeoParquetDependencyError,
    GeoParquetWriteResult,
    GeoParquetWriterOptions,
    write_geoparquet_occurrences,
)
from dwca_cloud_geospatial.inspection import (
    DECIMAL_LATITUDE_TERM,
    DECIMAL_LONGITUDE_TERM,
    ParserDiagnostic,
)
from dwca_cloud_geospatial.normalization import (
    NULL_VALUE_ACTION,
    OPTIONAL_CONVERSION_WARNING_RATE,
    OccurrenceNormalizationCounts,
    OccurrenceNormalizationResult,
    OccurrenceNormalizationWarning,
    RejectedOccurrenceRecord,
    TypeConversionFailure,
    normalize_occurrence_record_batch,
    normalize_occurrence_records,
)
from dwca_cloud_geospatial.occurrence import (
    SUMMARY_SOURCE_TERMS,
    OccurrenceReadResult,
    OccurrenceSourceRecord,
    read_occurrence_rows,
    stream_occurrence_row_batches,
)


FLATGEOBUF_FORMAT = "flatgeobuf"
GEOPARQUET_FORMAT = "geoparquet"
SUPPORTED_OUTPUT_FORMATS = (FLATGEOBUF_FORMAT, GEOPARQUET_FORMAT)
VIEWER_ASSET_FILENAMES = ("index.html", "styles.css", "app.js")
VIEWER_ASSET_SUBDIRS = ("assets",)


class ConversionError(RuntimeError):
    """Raised when a DwC-A archive cannot be converted reliably."""

    def __init__(
        self,
        message: str,
        *,
        diagnostics: Sequence[ParserDiagnostic] = (),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.diagnostics = tuple(diagnostics)


@dataclass(frozen=True)
class ConversionOptions:
    """Options for one local archive-to-bundle conversion."""

    output_formats: tuple[str, ...] = (FLATGEOBUF_FORMAT,)
    overwrite: bool = False
    flatgeobuf: FlatGeobufWriterOptions = field(default_factory=FlatGeobufWriterOptions)
    geoparquet: GeoParquetWriterOptions = field(default_factory=GeoParquetWriterOptions)
    bundle: BundleWriterOptions = field(default_factory=BundleWriterOptions)
    gbif: GbifDownloadOptions = field(default_factory=GbifDownloadOptions)
    gbif_client: GbifDownloadClient | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    flatgeobuf_backend: FlatGeobufBackend | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    chunk_size: int = 10_000


@dataclass(frozen=True)
class ConversionResult:
    """Structured result for CLI, GUI and integration callers."""

    input_path: Path
    output_directory: Path
    output_formats: tuple[str, ...]
    occurrence_result: OccurrenceReadResult
    normalization_result: OccurrenceNormalizationResult
    metadata_result: BundleMetadataWriteResult
    flatgeobuf_result: FlatGeobufWriteResult | None = None
    geoparquet_result: GeoParquetWriteResult | None = None

    @property
    def accepted_record_count(self) -> int:
        return self.normalization_result.counts.accepted_records

    @property
    def rejected_record_count(self) -> int:
        return self.normalization_result.counts.rejected_records


def convert_dwca_archive(
    input_path: str | Path,
    output_directory: str | Path,
    *,
    options: ConversionOptions | None = None,
) -> ConversionResult:
    """Convert a local DwC-A occurrence archive into an output bundle."""

    conversion_options = options or ConversionOptions()
    output_formats = _normalize_output_formats(conversion_options.output_formats)
    source_path = Path(input_path).expanduser()
    output_root = Path(output_directory).expanduser()

    _prepare_output_path(output_root, overwrite=conversion_options.overwrite)

    if _use_streaming_conversion(conversion_options, output_formats):
        return _convert_dwca_archive_streaming_outputs(
            source_path=source_path,
            output_root=output_root,
            output_formats=output_formats,
            conversion_options=conversion_options,
        )

    occurrence_result = read_occurrence_rows(source_path)
    _raise_for_occurrence_read_errors(occurrence_result)
    _raise_for_missing_coordinate_terms(occurrence_result)
    gbif_enrichment = _resolve_gbif_metadata(
        occurrence_result=occurrence_result,
        source_path=source_path,
        conversion_options=conversion_options,
    )

    normalization_result = normalize_occurrence_records(occurrence_result.records)
    if normalization_result.counts.accepted_records == 0:
        raise ConversionError(
            "Conversion produced no accepted occurrence records after normalization. "
            "Check coordinate values and required provenance fields in the source archive.",
            diagnostics=occurrence_result.diagnostics,
        )

    flatgeobuf_result: FlatGeobufWriteResult | None = None
    geoparquet_result: GeoParquetWriteResult | None = None

    try:
        if FLATGEOBUF_FORMAT in output_formats:
            flatgeobuf_result = write_flatgeobuf_occurrences(
                normalization_result.accepted_records,
                output_root,
                options=conversion_options.flatgeobuf,
                backend=conversion_options.flatgeobuf_backend,
            )
        if GEOPARQUET_FORMAT in output_formats:
            geoparquet_result = write_geoparquet_occurrences(
                normalization_result.accepted_records,
                output_root,
                options=conversion_options.geoparquet,
            )
        metadata_result = write_bundle_metadata(
            output_directory=output_root,
            occurrence_result=occurrence_result,
            normalization_result=normalization_result,
            flatgeobuf_result=flatgeobuf_result,
            geoparquet_result=geoparquet_result,
            options=_bundle_options(conversion_options, output_formats=output_formats),
            gbif_download_metadata=gbif_enrichment.metadata,
            extra_warnings=gbif_enrichment.warnings,
        )
        _copy_static_viewer(output_root)
        _write_output_bundle_readme(output_root)
    except (FlatGeobufDependencyError, GeoParquetDependencyError) as exc:
        raise ConversionError(
            f"{exc} Install the documented optional dependencies for the selected output format.",
            diagnostics=occurrence_result.diagnostics,
        ) from exc
    except OSError as exc:
        raise ConversionError(
            f"Could not write output bundle at {output_root}: {exc}",
            diagnostics=occurrence_result.diagnostics,
        ) from exc
    except ValueError as exc:
        raise ConversionError(str(exc), diagnostics=occurrence_result.diagnostics) from exc

    return ConversionResult(
        input_path=source_path,
        output_directory=output_root,
        output_formats=output_formats,
        occurrence_result=occurrence_result,
        normalization_result=normalization_result,
        metadata_result=metadata_result,
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
    )


def _convert_dwca_archive_streaming_outputs(
    *,
    source_path: Path,
    output_root: Path,
    output_formats: tuple[str, ...],
    conversion_options: ConversionOptions,
) -> ConversionResult:
    stream = stream_occurrence_row_batches(
        source_path,
        batch_size=conversion_options.chunk_size,
    )
    occurrence_result = OccurrenceReadResult(
        inspection=stream.inspection,
        records=(),
        diagnostics=stream.diagnostics,
        source_file=stream.source_file,
        rows_read=0,
        parse_failures=0,
        first_source_values={},
    )
    _raise_for_occurrence_read_errors(occurrence_result)
    _raise_for_missing_coordinate_terms(occurrence_result)

    aggregator = _StreamingNormalizationAggregator()
    rejected_writer = RejectedRecordsCsvWriter(output_root / REJECTED_RECORDS_RELATIVE_PATH)
    flatgeobuf_writer = (
        GeoPackageStagedFlatGeobufWriter(
            output_root,
            options=conversion_options.flatgeobuf,
        )
        if FLATGEOBUF_FORMAT in output_formats
        else None
    )

    def accepted_records():
        try:
            for batch in stream.batches:
                aggregator.add_parser_batch(batch.rows_read, batch.parse_failures)
                aggregator.diagnostics.extend(batch.diagnostics)
                if any(diagnostic.severity == "error" for diagnostic in batch.diagnostics):
                    raise ConversionError(
                        "Occurrence rows could not be read reliably during streaming conversion.",
                        diagnostics=tuple(aggregator.diagnostics),
                    )
                for record in batch.records:
                    aggregator.capture_source_record(record)
                normalized = normalize_occurrence_record_batch(batch.records)
                aggregator.add_normalization_result(normalized)
                rejected_writer.write_many(normalized.rejected_records)
                if flatgeobuf_writer is not None:
                    flatgeobuf_writer.write_batch(normalized.accepted_records)
                yield from normalized.accepted_records
        finally:
            rejected_writer.close()

    try:
        flatgeobuf_result: FlatGeobufWriteResult | None = None
        geoparquet_result: GeoParquetWriteResult | None = None
        if GEOPARQUET_FORMAT in output_formats:
            geoparquet_result = write_geoparquet_occurrences(
                accepted_records(),
                output_root,
                options=conversion_options.geoparquet,
            )
        else:
            for _record in accepted_records():
                pass
        occurrence_result = OccurrenceReadResult(
            inspection=stream.inspection,
            records=(),
            diagnostics=tuple((*stream.diagnostics, *aggregator.diagnostics)),
            source_file=stream.source_file,
            rows_read=aggregator.source_records,
            parse_failures=aggregator.parse_failures,
            first_source_values=aggregator.first_source_values,
        )
        gbif_enrichment = _resolve_gbif_metadata(
            occurrence_result=occurrence_result,
            source_path=source_path,
            conversion_options=conversion_options,
        )
        normalization_result = aggregator.result()
        if normalization_result.counts.accepted_records == 0:
            raise ConversionError(
                "Conversion produced no accepted occurrence records after normalization. "
                "Check coordinate values and required provenance fields in the source archive.",
                diagnostics=occurrence_result.diagnostics,
            )
        if flatgeobuf_writer is not None:
            flatgeobuf_result = flatgeobuf_writer.finish()
        metadata_result = write_bundle_metadata(
            output_directory=output_root,
            occurrence_result=occurrence_result,
            normalization_result=normalization_result,
            flatgeobuf_result=flatgeobuf_result,
            geoparquet_result=geoparquet_result,
            rejected_records_path=rejected_writer.written_path,
            options=_bundle_options(conversion_options, output_formats=output_formats),
            gbif_download_metadata=gbif_enrichment.metadata,
            extra_warnings=gbif_enrichment.warnings,
        )
        _copy_static_viewer(output_root)
        _write_output_bundle_readme(output_root)
    except (FlatGeobufDependencyError, GeoParquetDependencyError) as exc:
        raise ConversionError(
            f"{exc} Install the documented optional dependencies for the selected output format.",
            diagnostics=tuple((*stream.diagnostics, *aggregator.diagnostics)),
        ) from exc
    except OSError as exc:
        raise ConversionError(
            f"Could not write output bundle at {output_root}: {exc}",
            diagnostics=tuple((*stream.diagnostics, *aggregator.diagnostics)),
        ) from exc
    except ValueError as exc:
        raise ConversionError(
            str(exc),
            diagnostics=tuple((*stream.diagnostics, *aggregator.diagnostics)),
        ) from exc

    return ConversionResult(
        input_path=source_path,
        output_directory=output_root,
        output_formats=output_formats,
        occurrence_result=occurrence_result,
        normalization_result=normalization_result,
        metadata_result=metadata_result,
        flatgeobuf_result=flatgeobuf_result,
        geoparquet_result=geoparquet_result,
    )


class _StreamingNormalizationAggregator:
    def __init__(self) -> None:
        self.source_records = 0
        self.parse_failures = 0
        self.accepted_records = 0
        self.rejected_records = 0
        self.failure_counts: dict[tuple[str, str, str], int] = {}
        self.first_source_values: dict[str, str] = {}
        self.first_accepted_values: dict[str, str] = {}
        self.diagnostics: list[ParserDiagnostic] = []

    def add_parser_batch(self, rows_read: int, parse_failures: int) -> None:
        self.source_records += rows_read
        self.parse_failures += parse_failures

    def capture_source_record(self, record: OccurrenceSourceRecord) -> None:
        for term in SUMMARY_SOURCE_TERMS:
            if term in self.first_source_values:
                continue
            value = record.value_for_term(term)
            if value and value.strip():
                self.first_source_values[term] = value.strip()

    def add_normalization_result(self, result: OccurrenceNormalizationResult) -> None:
        self.accepted_records += result.counts.accepted_records
        self.rejected_records += result.counts.rejected_records
        for record in result.accepted_records:
            self._capture_accepted_record(record)
        for failure in result.type_conversion_failures:
            key = (failure.field, failure.reason_code, failure.action)
            self.failure_counts[key] = self.failure_counts.get(key, 0) + failure.failure_count

    def result(self) -> OccurrenceNormalizationResult:
        failures = self._type_conversion_failures()
        warnings = self._warnings(failures)
        return OccurrenceNormalizationResult(
            accepted_records=(),
            rejected_records=(),
            counts=OccurrenceNormalizationCounts(
                source_records=self.source_records,
                parsed_records=self.source_records,
                accepted_records=self.accepted_records,
                rejected_records=self.rejected_records,
                warning_count=len(warnings),
            ),
            type_conversion_failures=failures,
            warnings=warnings,
            first_accepted_values=self.first_accepted_values,
        )

    def _capture_accepted_record(self, record: Any) -> None:
        for field in ("publisher", "license", "rights_holder"):
            if field in self.first_accepted_values:
                continue
            value = getattr(record, field)
            if isinstance(value, str) and value.strip():
                self.first_accepted_values[field] = value.strip()

    def _type_conversion_failures(self) -> tuple[TypeConversionFailure, ...]:
        failures: list[TypeConversionFailure] = []
        for key, count in sorted(self.failure_counts.items()):
            field, reason_code, action = key
            failures.append(
                TypeConversionFailure(
                    field=field,
                    reason_code=reason_code,
                    failure_count=count,
                    failure_rate=count / self.source_records
                    if self.source_records
                    else 0,
                    action=action,
                )
            )
        return tuple(failures)

    def _warnings(
        self,
        failures: tuple[TypeConversionFailure, ...],
    ) -> tuple[OccurrenceNormalizationWarning, ...]:
        warnings: list[OccurrenceNormalizationWarning] = []
        for failure in failures:
            if (
                failure.action == NULL_VALUE_ACTION
                and failure.failure_rate >= OPTIONAL_CONVERSION_WARNING_RATE
            ):
                warnings.append(
                    OccurrenceNormalizationWarning(
                        code="optional_conversion_failure_rate",
                        message=(
                            f"Optional field {failure.field} failed conversion for "
                            f"{failure.failure_count} parsed record(s)."
                        ),
                        field=failure.field,
                        reason_code=failure.reason_code,
                        failure_count=failure.failure_count,
                        failure_rate=failure.failure_rate,
                    )
                )
        return tuple(warnings)


def _normalize_output_formats(output_formats: Sequence[str]) -> tuple[str, ...]:
    if not output_formats:
        return (FLATGEOBUF_FORMAT,)

    normalized: list[str] = []
    for output_format in output_formats:
        value = output_format.strip().lower()
        if value not in SUPPORTED_OUTPUT_FORMATS:
            raise ConversionError(
                f"Unsupported output format '{output_format}'. "
                f"Supported formats: {', '.join(SUPPORTED_OUTPUT_FORMATS)}."
            )
        if value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def _resolve_gbif_metadata(
    *,
    occurrence_result: OccurrenceReadResult,
    source_path: Path,
    conversion_options: ConversionOptions,
) -> GbifEnrichmentResult:
    inferred_key = (
        _first_occurrence_download_key(occurrence_result)
        or _download_key_from_declared_metadata(occurrence_result)
        or infer_download_key_from_path_name(source_path.name)
    )
    try:
        return resolve_gbif_download_metadata(
            options=conversion_options.gbif,
            inferred_download_key=inferred_key,
            client=conversion_options.gbif_client,
        )
    except ValueError as exc:
        raise ConversionError(str(exc), diagnostics=occurrence_result.diagnostics) from exc


def _first_occurrence_download_key(
    occurrence_result: OccurrenceReadResult,
) -> str | None:
    terms = (
        "http://rs.gbif.org/terms/1.0/downloadKey",
        "http://rs.gbif.org/terms/1.0/download_key",
    )
    summary_values = occurrence_result.first_source_values or {}
    for term in terms:
        key = normalize_download_key(summary_values.get(term))
        if key:
            return key
    for record in occurrence_result.records:
        for term in terms:
            key = normalize_download_key(record.value_for_term(term))
            if key:
                return key
    return None


def _download_key_from_declared_metadata(
    occurrence_result: OccurrenceReadResult,
) -> str | None:
    inspection = occurrence_result.inspection
    metadata_file = inspection.metadata.metadata_file if inspection.metadata else None
    if not metadata_file or not _is_safe_archive_path(metadata_file):
        return None
    try:
        if inspection.archive_kind == "directory":
            payload = (inspection.source_path / metadata_file).read_bytes()
        elif inspection.archive_kind == "zip":
            member = metadata_file
            if inspection.meta_path and "/" in inspection.meta_path:
                member = f"{inspection.meta_path.rsplit('/', 1)[0]}/{metadata_file}"
            with zipfile.ZipFile(inspection.source_path) as archive:
                payload = archive.read(member)
        else:
            return None
    except (KeyError, OSError, zipfile.BadZipFile):
        return None
    return extract_download_key_from_eml_xml(payload)


def _is_safe_archive_path(path: str) -> bool:
    if not path or "\\" in path or path.startswith(("/", "\\")):
        return False
    if "//" in path or path.split("/", 1)[0].endswith(":"):
        return False
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute():
        return False
    return all(part not in ("", ".", "..") for part in pure_path.parts)


def _use_streaming_conversion(
    conversion_options: ConversionOptions,
    output_formats: tuple[str, ...],
) -> bool:
    return (
        (
            FLATGEOBUF_FORMAT in output_formats
            and conversion_options.flatgeobuf_backend is None
        )
        or (
            GEOPARQUET_FORMAT in output_formats
            and FLATGEOBUF_FORMAT not in output_formats
            and conversion_options.geoparquet.large_output_mode
        )
    )


def _prepare_output_path(output_root: Path, *, overwrite: bool) -> None:
    if not output_root.exists():
        return
    if not overwrite:
        raise ConversionError(
            f"Output path already exists: {output_root}. Pass --overwrite to replace it."
        )
    if output_root.is_dir():
        shutil.rmtree(output_root)
    else:
        output_root.unlink()


def _copy_static_viewer(output_root: Path) -> None:
    viewer_source = Path(__file__).resolve().parents[2] / "viewer"
    if not viewer_source.is_dir():
        raise ConversionError(
            "Static viewer assets were not found in the repository viewer/ directory."
        )

    for filename in VIEWER_ASSET_FILENAMES:
        source = viewer_source / filename
        if not source.is_file():
            raise ConversionError(f"Static viewer asset is missing: {source}")
        shutil.copy2(source, output_root / filename)

    for subdir in VIEWER_ASSET_SUBDIRS:
        source = viewer_source / subdir
        if not source.is_dir():
            raise ConversionError(f"Static viewer asset directory is missing: {source}")
        dest = output_root / subdir
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)


def _write_output_bundle_readme(output_root: Path) -> None:
    (output_root / "README.md").write_text(
        """# Generated DwC-A Geospatial Bundle

This directory is a generated output bundle from `dwca-cloud-geospatial`.

## Open The Viewer

Serve this directory, or any parent directory that contains it, with ordinary
static file hosting and open `index.html` in a browser.

For local review from the repository root:

```bash
python -m http.server 8000 --directory .
```

Then open the bundle-relative viewer URL, for example:

```text
http://localhost:8000/path/to/output-bundle/index.html
```

## Bundle Contents

- `manifest.json`: discovery document for tools and the static viewer.
- `metadata/source.json`: source archive, dataset, rights and provenance
  metadata.
- `metadata/processing.json`: converter configuration, counts, validation
  summary, warnings and parser diagnostics.
- `data/`: generated geospatial outputs such as FlatGeobuf, GeoPackage and
  GeoParquet when selected.
- `reports/`: rejected-record reports when source rows are rejected or skipped.
- `index.html`, `styles.css` and `app.js`: static viewer assets copied into
  the bundle.

The viewer does not require a project backend, database, scheduler or live
GBIF/OBIS API. Optional external frontend assets and basemap tiles depend on
the copied viewer configuration.

## Citation And License

Dataset DOI, citation, license, rights holder and GBIF/OBIS provenance are
recorded in `metadata/source.json` and summarized in `manifest.json` when
available. Preserve those fields when publishing or redistributing this
generated bundle.
""",
        encoding="utf-8",
    )


def _raise_for_occurrence_read_errors(occurrence_result: OccurrenceReadResult) -> None:
    if not occurrence_result.has_errors:
        return

    error_diagnostics = tuple(
        diagnostic
        for diagnostic in occurrence_result.diagnostics
        if diagnostic.severity == "error"
    )
    missing_core = next(
        (
            diagnostic
            for diagnostic in error_diagnostics
            if diagnostic.code == "missing_occurrence_core"
        ),
        None,
    )
    if missing_core is not None:
        raise ConversionError(
            "Input archive is not an occurrence DwC-A archive: "
            f"{missing_core.message}",
            diagnostics=error_diagnostics,
        )

    summary = "; ".join(
        f"{diagnostic.code}: {diagnostic.message}"
        for diagnostic in error_diagnostics
    )
    raise ConversionError(
        f"Occurrence rows could not be read reliably: {summary}",
        diagnostics=error_diagnostics,
    )


def _raise_for_missing_coordinate_terms(
    occurrence_result: OccurrenceReadResult,
) -> None:
    metadata = occurrence_result.inspection.metadata
    occurrence_core = metadata.occurrence_core if metadata else None
    if occurrence_core is not None and occurrence_core.has_coordinate_fields:
        return

    declared = metadata.coordinate_terms_present if metadata else {}
    missing_terms = [
        term
        for term in (DECIMAL_LATITUDE_TERM, DECIMAL_LONGITUDE_TERM)
        if not declared.get(term, False)
    ]
    missing_names = ", ".join(term.rsplit("/", 1)[-1] for term in missing_terms)
    raise ConversionError(
        "Occurrence conversion requires decimalLatitude and decimalLongitude "
        f"terms on the Occurrence core. Missing: {missing_names or 'unknown'}."
    )


def _bundle_options(
    conversion_options: ConversionOptions,
    *,
    output_formats: tuple[str, ...],
) -> BundleWriterOptions:
    configuration: dict[str, Any] = {
        "formats": list(output_formats),
        "chunk_size": conversion_options.chunk_size,
        "gbif": {
            "download_key": conversion_options.gbif.download_key,
            "doi": conversion_options.gbif.doi,
            "citation": conversion_options.gbif.citation,
            "license": conversion_options.gbif.license,
            "enrich": conversion_options.gbif.enrich,
            "api_base_url": conversion_options.gbif.api_base_url,
            "connect_timeout_seconds": (
                conversion_options.gbif.connect_timeout_seconds
            ),
            "read_timeout_seconds": conversion_options.gbif.read_timeout_seconds,
            "max_retries": conversion_options.gbif.max_retries,
        },
    }
    if conversion_options.bundle.configuration:
        configuration["user"] = dict(conversion_options.bundle.configuration)
    return BundleWriterOptions(
        bundle_id=conversion_options.bundle.bundle_id,
        title=conversion_options.bundle.title,
        created_at=conversion_options.bundle.created_at,
        generator_name=conversion_options.bundle.generator_name,
        generator_version=conversion_options.bundle.generator_version,
        generator_commit=conversion_options.bundle.generator_commit,
        configuration=configuration,
    )
