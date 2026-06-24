"""Command-line entry point for the DwC-A cloud geospatial converter."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from dwca_cloud_geospatial import __version__
from dwca_cloud_geospatial.conversion import (
    GEOPARQUET_FORMAT,
    SUPPORTED_OUTPUT_FORMATS,
    ConversionError,
    ConversionOptions,
    convert_dwca_archive,
)
from dwca_cloud_geospatial.gbif import GbifDownloadOptions
from dwca_cloud_geospatial.geoparquet import GeoParquetWriterOptions
from dwca_cloud_geospatial.inspection import (
    DECIMAL_LATITUDE_TERM,
    DECIMAL_LONGITUDE_TERM,
    ArchiveInspection,
    ArchiveTable,
    inspect_dwca,
)
from dwca_cloud_geospatial.validation import BundleValidationResult, validate_output_bundle


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without executing converter behavior."""

    parser = argparse.ArgumentParser(
        prog="dwca-cloud-geospatial",
        description=(
            "Convert local Darwin Core Archive datasets into static, "
            "cloud-friendly geospatial output bundles."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        title="commands",
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a local DwC-A archive or unpacked archive directory.",
        description=(
            "Inspect a local Darwin Core Archive path and report the structure "
            "declared by meta.xml."
        ),
    )
    inspect_parser.add_argument(
        "archive",
        help="Explicit path to a .zip DwC-A archive or unpacked DwC-A directory.",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured inspection JSON instead of human-readable text.",
    )
    inspect_parser.set_defaults(handler=_inspect_archive)

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a local DwC-A archive into a static output bundle.",
        description=(
            "Convert a local Darwin Core Archive to geospatial outputs and "
            "bundle metadata."
        ),
    )
    convert_parser.add_argument(
        "archive",
        help="Explicit path to a .zip DwC-A archive or unpacked DwC-A directory.",
    )
    convert_parser.add_argument(
        "output",
        help="Explicit path to the output bundle directory.",
    )
    convert_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output path.",
    )
    convert_parser.add_argument(
        "--format",
        dest="formats",
        action="append",
        choices=SUPPORTED_OUTPUT_FORMATS,
        help=(
            "Output format to generate. May be passed more than once. "
            "Defaults to flatgeobuf."
        ),
    )
    convert_parser.add_argument(
        "--geoparquet-large-output",
        action="store_true",
        help=(
            "Enable GeoParquet large-output mode for selected GeoParquet output "
            "(bbox covering column and grid spatial sorting). Requires "
            "--format geoparquet."
        ),
    )
    convert_parser.add_argument(
        "--chunk-size",
        type=_positive_int,
        help=(
            "Positive number of source occurrence rows to process per streaming "
            "conversion chunk. Defaults to the core API default of 10000."
        ),
    )
    convert_parser.add_argument(
        "--gbif-download-key",
        help=(
            "Explicit GBIF occurrence download key for source provenance. "
            "If omitted, the converter may infer one from source metadata or the input name."
        ),
    )
    convert_parser.add_argument(
        "--gbif-doi",
        help="Explicit GBIF occurrence download DOI, as a bare DOI or doi.org URL.",
    )
    convert_parser.add_argument(
        "--gbif-citation",
        help="Explicit GBIF occurrence download citation text.",
    )
    convert_parser.add_argument(
        "--gbif-license",
        help="Explicit GBIF occurrence download license value or URI.",
    )
    convert_parser.add_argument(
        "--gbif-enrich",
        action="store_true",
        help=(
            "Opt in to read-only GBIF API download metadata lookup during conversion. "
            "Ordinary conversion performs no GBIF network access."
        ),
    )
    convert_parser.set_defaults(handler=_convert_archive, parser=convert_parser)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an existing output bundle.",
        description=(
            "Validate a generated output bundle and report structured checks."
        ),
    )
    validate_parser.add_argument(
        "bundle",
        help="Explicit path to an output bundle directory.",
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured validation JSON instead of human-readable text.",
    )
    validate_parser.set_defaults(handler=_validate_bundle)

    return parser


def _inspect_archive(args: argparse.Namespace) -> int:
    inspection = inspect_dwca(args.archive)
    if args.json:
        print(inspection.to_json())
    else:
        print(_format_inspection(inspection))
    if inspection.has_errors:
        for diagnostic in inspection.diagnostics:
            if diagnostic.severity == "error":
                print(
                    f"{diagnostic.source}: {diagnostic.code}: {diagnostic.message}",
                    file=sys.stderr,
                )
        return 1
    return 0


def _convert_archive(args: argparse.Namespace) -> int:
    _validate_convert_args(args)
    try:
        result = convert_dwca_archive(
            args.archive,
            args.output,
            options=_conversion_options_from_args(args),
        )
    except ConversionError as exc:
        print(f"Conversion failed: {exc.message}", file=sys.stderr)
        for diagnostic in exc.diagnostics:
            if diagnostic.severity == "error":
                print(
                    f"{diagnostic.source}: {diagnostic.code}: {diagnostic.message}",
                    file=sys.stderr,
                )
        return 1

    print(f"Converted {result.input_path} -> {result.output_directory}")
    print(f"Formats: {', '.join(result.output_formats)}")
    print(f"Accepted records: {result.accepted_record_count}")
    print(f"Rejected records: {result.rejected_record_count}")
    print(f"Manifest: {result.metadata_result.manifest_path}")
    print(f"Viewer: {result.output_directory / 'index.html'}")
    return 0


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "chunk size must be a positive integer."
        ) from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("chunk size must be a positive integer.")
    return parsed


def _validate_convert_args(args: argparse.Namespace) -> None:
    if args.geoparquet_large_output and GEOPARQUET_FORMAT not in tuple(
        args.formats or ()
    ):
        args.parser.error(
            "GeoParquet large-output mode requires GeoParquet output; "
            "pass --format geoparquet."
        )


def _conversion_options_from_args(args: argparse.Namespace) -> ConversionOptions:
    options: dict[str, object] = {
        "output_formats": tuple(args.formats or ()),
        "overwrite": args.overwrite,
        "geoparquet": GeoParquetWriterOptions(
            large_output_mode=args.geoparquet_large_output,
        ),
        "gbif": GbifDownloadOptions(
            download_key=args.gbif_download_key,
            doi=args.gbif_doi,
            citation=args.gbif_citation,
            license=args.gbif_license,
            enrich=args.gbif_enrich,
        ),
    }
    if args.chunk_size is not None:
        options["chunk_size"] = args.chunk_size
    return ConversionOptions(**options)


def _validate_bundle(args: argparse.Namespace) -> int:
    result = validate_output_bundle(args.bundle)
    if args.json:
        print(result.to_json())
    else:
        print(_format_validation(result))
    return 1 if result.has_errors else 0


def _format_inspection(inspection: ArchiveInspection) -> str:
    lines = [
        f"Archive: {inspection.source_path}",
        f"Type: {inspection.archive_kind}",
        f"meta.xml: {inspection.meta_path or 'not found'}",
    ]
    if inspection.source_size_bytes is not None:
        lines.append(f"Size: {inspection.source_size_bytes} bytes")
    if inspection.source_sha256 is not None:
        lines.append(f"SHA-256: {inspection.source_sha256}")

    if inspection.metadata is None:
        lines.append("Metadata: unavailable")
    else:
        metadata = inspection.metadata
        lines.extend(
            [
                f"Occurrence core: {'yes' if metadata.has_occurrence_core else 'no'}",
                (
                    "Coordinate fields: "
                    f"decimalLatitude={'yes' if metadata.coordinate_terms_present[DECIMAL_LATITUDE_TERM] else 'no'}, "
                    f"decimalLongitude={'yes' if metadata.coordinate_terms_present[DECIMAL_LONGITUDE_TERM] else 'no'}"
                ),
                f"Declared files: {len(metadata.declared_files)}",
            ]
        )
        if metadata.core:
            lines.append(_format_table(metadata.core, label="Core"))
        for index, extension in enumerate(metadata.extensions, start=1):
            lines.append(_format_table(extension, label=f"Extension {index}"))

    if inspection.diagnostics:
        lines.append("Diagnostics:")
        for diagnostic in inspection.diagnostics:
            context = f" ({diagnostic.context})" if diagnostic.context else ""
            lines.append(
                f"  - {diagnostic.severity}: {diagnostic.code}: "
                f"{diagnostic.message}{context}"
            )
    else:
        lines.append("Diagnostics: none")

    return "\n".join(lines)


def _format_table(table: ArchiveTable, label: str) -> str:
    files = ", ".join(table.files) if table.files else "none"
    return (
        f"{label}: rowType={table.row_type or 'unknown'}, files={files}, "
        f"fields={len(table.fields)}, ignoreHeaderLines={table.text_format.ignore_header_lines}, "
        f"encoding={table.text_format.encoding}"
    )


def _format_validation(result: BundleValidationResult) -> str:
    lines = [
        f"Bundle: {result.bundle_root}",
        f"Status: {result.status}",
        f"Errors: {len(result.errors)}",
        f"Warnings: {len(result.warnings)}",
        f"Checks: {len(result.checks)}",
    ]
    if result.errors:
        lines.append("Validation errors:")
        for issue in result.errors:
            path = f" ({issue.path})" if issue.path else ""
            lines.append(f"  - {issue.code}: {issue.message}{path}")
    if result.warnings:
        lines.append("Validation warnings:")
        for issue in result.warnings:
            path = f" ({issue.path})" if issue.path else ""
            lines.append(f"  - {issue.code}: {issue.message}{path}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    return int(handler(args))
