"""Core conversion orchestration for DwC-A output bundles."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any

from dwca_cloud_geospatial.bundle import (
    BundleMetadataWriteResult,
    BundleWriterOptions,
    write_bundle_metadata,
)
from dwca_cloud_geospatial.flatgeobuf import (
    FlatGeobufBackend,
    FlatGeobufDependencyError,
    FlatGeobufWriteResult,
    FlatGeobufWriterOptions,
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
    OccurrenceNormalizationResult,
    normalize_occurrence_records,
)
from dwca_cloud_geospatial.occurrence import OccurrenceReadResult, read_occurrence_rows


FLATGEOBUF_FORMAT = "flatgeobuf"
GEOPARQUET_FORMAT = "geoparquet"
SUPPORTED_OUTPUT_FORMATS = (FLATGEOBUF_FORMAT, GEOPARQUET_FORMAT)


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
    flatgeobuf_backend: FlatGeobufBackend | None = field(
        default=None,
        repr=False,
        compare=False,
    )


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

    occurrence_result = read_occurrence_rows(source_path)
    _raise_for_occurrence_read_errors(occurrence_result)
    _raise_for_missing_coordinate_terms(occurrence_result)

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
        )
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
    configuration: dict[str, Any] = {"formats": list(output_formats)}
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
