"""Command-line entry point for the DwC-A cloud geospatial converter."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from dwca_cloud_geospatial import __version__


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
            "Inspect a local Darwin Core Archive path. Parser behavior will be "
            "implemented in a later MVP milestone."
        ),
    )
    inspect_parser.add_argument(
        "archive",
        help="Explicit path to a .zip DwC-A archive or unpacked DwC-A directory.",
    )
    inspect_parser.set_defaults(handler=_not_implemented)

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
