"""Command-line entry point for the DwC-A cloud geospatial converter."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from dwca_cloud_geospatial import __version__
from dwca_cloud_geospatial.inspection import (
    DECIMAL_LATITUDE_TERM,
    DECIMAL_LONGITUDE_TERM,
    ArchiveInspection,
    ArchiveTable,
    inspect_dwca,
)


COMMAND_NOT_IMPLEMENTED = (
    "This command is part of the planned MVP interface but is not implemented yet."
)


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
            "Convert a local Darwin Core Archive to geospatial outputs. "
            "Conversion behavior will be implemented in a later MVP milestone."
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
        help="Allow replacing an existing output path when conversion is implemented.",
    )
    convert_parser.set_defaults(handler=_not_implemented)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an existing output bundle.",
        description=(
            "Validate a generated output bundle. Validation behavior will be "
            "implemented in a later MVP milestone."
        ),
    )
    validate_parser.add_argument(
        "bundle",
        help="Explicit path to an output bundle directory.",
    )
    validate_parser.set_defaults(handler=_not_implemented)

    return parser


def _not_implemented(args: argparse.Namespace) -> int:
    raise NotImplementedError(COMMAND_NOT_IMPLEMENTED)


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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    try:
        return int(handler(args))
    except NotImplementedError as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
