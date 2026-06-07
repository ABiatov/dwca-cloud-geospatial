"""Safe Darwin Core Archive inspection and ``meta.xml`` parsing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any
import xml.etree.ElementTree as ET
import zipfile


DWC_TEXT_NAMESPACE = "http://rs.tdwg.org/dwc/text/"
OCCURRENCE_ROW_TYPE = "http://rs.tdwg.org/dwc/terms/Occurrence"
DECIMAL_LATITUDE_TERM = "http://rs.tdwg.org/dwc/terms/decimalLatitude"
DECIMAL_LONGITUDE_TERM = "http://rs.tdwg.org/dwc/terms/decimalLongitude"


class DwcaInspectionError(Exception):
    """Raised when a DwC-A path cannot be inspected at all."""


@dataclass(frozen=True)
class ParserDiagnostic:
    """Structured parser diagnostic with source context."""

    severity: str
    code: str
    message: str
    source: str
    context: str | None = None


@dataclass(frozen=True)
class DelimitedTextFormat:
    """Delimited text settings declared by a DwC-A table."""

    encoding: str
    fields_terminated_by: str
    lines_terminated_by: str
    fields_enclosed_by: str | None
    ignore_header_lines: int


@dataclass(frozen=True)
class ArchiveField:
    """A declared Darwin Core Archive field."""

    term: str
    index: int | None
    default: str | None = None
    delimited_by: str | None = None


@dataclass(frozen=True)
class ArchiveTable:
    """A DwC-A core or extension table declared in ``meta.xml``."""

    role: str
    row_type: str | None
    files: tuple[str, ...]
    id_index: int | None
    coreid_index: int | None
    fields: tuple[ArchiveField, ...]
    text_format: DelimitedTextFormat

    def field_for_term(self, term: str) -> ArchiveField | None:
        """Return the first declared field for a Darwin Core term."""

        for field in self.fields:
            if field.term == term:
                return field
        return None

    @property
    def has_decimal_latitude(self) -> bool:
        return self.field_for_term(DECIMAL_LATITUDE_TERM) is not None

    @property
    def has_decimal_longitude(self) -> bool:
        return self.field_for_term(DECIMAL_LONGITUDE_TERM) is not None

    @property
    def has_coordinate_fields(self) -> bool:
        return self.has_decimal_latitude and self.has_decimal_longitude


@dataclass(frozen=True)
class ArchiveMetadata:
    """Structured metadata parsed from a Darwin Core Archive ``meta.xml``."""

    metadata_file: str | None
    core: ArchiveTable | None
    extensions: tuple[ArchiveTable, ...]

    @property
    def declared_files(self) -> tuple[str, ...]:
        files: list[str] = []
        if self.metadata_file:
            files.append(self.metadata_file)
        if self.core:
            files.extend(self.core.files)
        for extension in self.extensions:
            files.extend(extension.files)
        return tuple(files)

    @property
    def occurrence_core(self) -> ArchiveTable | None:
        if self.core and self.core.row_type == OCCURRENCE_ROW_TYPE:
            return self.core
        return None

    @property
    def has_occurrence_core(self) -> bool:
        return self.occurrence_core is not None

    @property
    def coordinate_terms_present(self) -> dict[str, bool]:
        tables = [table for table in (self.core, *self.extensions) if table is not None]
        return {
            DECIMAL_LATITUDE_TERM: any(table.has_decimal_latitude for table in tables),
            DECIMAL_LONGITUDE_TERM: any(table.has_decimal_longitude for table in tables),
        }


@dataclass(frozen=True)
class ArchiveInspection:
    """Result of inspecting a local DwC-A zip archive or unpacked directory."""

    source_path: Path
    archive_kind: str
    source_size_bytes: int | None
    source_sha256: str | None
    meta_path: str | None
    metadata: ArchiveMetadata | None
    diagnostics: tuple[ParserDiagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.severity == "error" for diagnostic in self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_path"] = str(self.source_path)
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def inspect_dwca(path: str | Path) -> ArchiveInspection:
    """Inspect a local DwC-A zip archive or unpacked directory."""

    source_path = Path(path).expanduser().resolve()
    if not source_path.exists():
        diagnostic = ParserDiagnostic(
            severity="error",
            code="path_not_found",
            message="DwC-A path does not exist.",
            source=str(source_path),
        )
        return ArchiveInspection(
            source_path=source_path,
            archive_kind="missing",
            source_size_bytes=None,
            source_sha256=None,
            meta_path=None,
            metadata=None,
            diagnostics=(diagnostic,),
        )

    if source_path.is_dir():
        return _inspect_directory(source_path)

    if source_path.is_file() and zipfile.is_zipfile(source_path):
        return _inspect_zip(source_path)

    diagnostic = ParserDiagnostic(
        severity="error",
        code="unsupported_archive_path",
        message="Expected a .zip Darwin Core Archive or an unpacked archive directory.",
        source=str(source_path),
    )
    return ArchiveInspection(
        source_path=source_path,
        archive_kind="unsupported",
        source_size_bytes=source_path.stat().st_size if source_path.is_file() else None,
        source_sha256=_sha256_file(source_path) if source_path.is_file() else None,
        meta_path=None,
        metadata=None,
        diagnostics=(diagnostic,),
    )


def _inspect_directory(source_path: Path) -> ArchiveInspection:
    diagnostics: list[ParserDiagnostic] = []
    meta_file = source_path / "meta.xml"

    if not meta_file.exists():
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="missing_meta_xml",
                message="Unpacked DwC-A directory does not contain meta.xml at its root.",
                source=str(source_path),
                context="meta.xml",
            )
        )
        return ArchiveInspection(
            source_path=source_path,
            archive_kind="directory",
            source_size_bytes=None,
            source_sha256=None,
            meta_path=None,
            metadata=None,
            diagnostics=tuple(diagnostics),
        )

    try:
        meta_bytes = meta_file.read_bytes()
    except OSError as exc:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="metadata_read_error",
                message=f"Could not read meta.xml: {exc}",
                source=str(meta_file),
            )
        )
        meta_bytes = b""

    metadata = _parse_meta_xml(meta_bytes, "meta.xml", diagnostics) if meta_bytes else None
    if metadata:
        _validate_declared_files(
            metadata=metadata,
            available=lambda declared_file: (source_path / declared_file).is_file(),
            diagnostics=diagnostics,
            source="meta.xml",
        )

    return ArchiveInspection(
        source_path=source_path,
        archive_kind="directory",
        source_size_bytes=None,
        source_sha256=None,
        meta_path="meta.xml" if metadata else None,
        metadata=metadata,
        diagnostics=tuple(diagnostics),
    )


def _inspect_zip(source_path: Path) -> ArchiveInspection:
    diagnostics: list[ParserDiagnostic] = []
    with zipfile.ZipFile(source_path) as archive:
        entries = tuple(info.filename for info in archive.infolist() if not info.is_dir())

        unsafe_entries = [entry for entry in entries if not _is_safe_archive_path(entry)]
        for entry in unsafe_entries:
            diagnostics.append(
                ParserDiagnostic(
                    severity="error",
                    code="unsafe_zip_entry_path",
                    message="Zip entry path is absolute, contains traversal, or uses unsafe separators.",
                    source=str(source_path),
                    context=entry,
                )
            )
        if unsafe_entries:
            return ArchiveInspection(
                source_path=source_path,
                archive_kind="zip",
                source_size_bytes=source_path.stat().st_size,
                source_sha256=_sha256_file(source_path),
                meta_path=None,
                metadata=None,
                diagnostics=tuple(diagnostics),
            )

        meta_path = _locate_meta_xml(entries, diagnostics, str(source_path))
        if meta_path is None:
            return ArchiveInspection(
                source_path=source_path,
                archive_kind="zip",
                source_size_bytes=source_path.stat().st_size,
                source_sha256=_sha256_file(source_path),
                meta_path=None,
                metadata=None,
                diagnostics=tuple(diagnostics),
            )

        try:
            meta_bytes = archive.read(meta_path)
        except KeyError:
            diagnostics.append(
                ParserDiagnostic(
                    severity="error",
                    code="metadata_read_error",
                    message="Located meta.xml was not readable from the zip archive.",
                    source=str(source_path),
                    context=meta_path,
                )
            )
            metadata = None
        else:
            metadata = _parse_meta_xml(meta_bytes, meta_path, diagnostics)

        if metadata:
            zip_base = ""
            if "/" in meta_path:
                zip_base = f"{meta_path.rsplit('/', 1)[0]}/"
            _validate_declared_files(
                metadata=metadata,
                available=lambda declared_file: f"{zip_base}{declared_file}" in entries,
                diagnostics=diagnostics,
                source=meta_path,
            )

    return ArchiveInspection(
        source_path=source_path,
        archive_kind="zip",
        source_size_bytes=source_path.stat().st_size,
        source_sha256=_sha256_file(source_path),
        meta_path=meta_path if metadata else None,
        metadata=metadata,
        diagnostics=tuple(diagnostics),
    )


def _parse_meta_xml(
    meta_bytes: bytes, source: str, diagnostics: list[ParserDiagnostic]
) -> ArchiveMetadata | None:
    try:
        root = ET.fromstring(meta_bytes)
    except ET.ParseError as exc:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="malformed_metadata",
                message=f"Could not parse DwC-A meta.xml: {exc}",
                source=source,
            )
        )
        return None

    if _local_name(root.tag) != "archive":
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="unsupported_metadata_root",
                message="DwC-A meta.xml root element must be archive.",
                source=source,
                context=root.tag,
            )
        )
        return None

    metadata_file = root.attrib.get("metadata")
    if metadata_file and not _is_safe_archive_path(metadata_file):
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="unsafe_declared_file_path",
                message="Archive metadata path is absolute or contains traversal.",
                source=source,
                context=metadata_file,
            )
        )

    core_elements = _children(root, "core")
    if not core_elements:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="missing_core",
                message="DwC-A meta.xml does not declare a core table.",
                source=source,
            )
        )
        core = None
    else:
        if len(core_elements) > 1:
            diagnostics.append(
                ParserDiagnostic(
                    severity="warning",
                    code="multiple_core_elements",
                    message="DwC-A meta.xml declares multiple core elements; only the first is used.",
                    source=source,
                )
            )
        core = _parse_table(core_elements[0], "core", source, diagnostics)

    extensions = tuple(
        _parse_table(extension, "extension", source, diagnostics)
        for extension in _children(root, "extension")
    )

    return ArchiveMetadata(
        metadata_file=metadata_file,
        core=core,
        extensions=extensions,
    )


def _parse_table(
    element: ET.Element,
    role: str,
    source: str,
    diagnostics: list[ParserDiagnostic],
) -> ArchiveTable:
    files = tuple(
        (location.text or "").strip()
        for files_element in _children(element, "files")
        for location in _children(files_element, "location")
        if (location.text or "").strip()
    )
    if not files:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="missing_table_location",
                message=f"DwC-A {role} table does not declare a file location.",
                source=source,
                context=element.attrib.get("rowType"),
            )
        )
    if len(files) > 1:
        diagnostics.append(
            ParserDiagnostic(
                severity="warning",
                code="unsupported_multiple_table_files",
                message=(
                    f"DwC-A {role} table declares multiple files; streaming support "
                    "for multiple files is deferred."
                ),
                source=source,
                context=", ".join(files),
            )
        )
    for declared_file in files:
        if not _is_safe_archive_path(declared_file):
            diagnostics.append(
                ParserDiagnostic(
                    severity="error",
                    code="unsafe_declared_file_path",
                    message="Declared table file path is absolute or contains traversal.",
                    source=source,
                    context=declared_file,
                )
            )

    fields = tuple(
        _parse_field(field, source, diagnostics)
        for field in _children(element, "field")
        if "term" in field.attrib
    )
    return ArchiveTable(
        role=role,
        row_type=element.attrib.get("rowType"),
        files=files,
        id_index=_parse_index(_first_child(element, "id"), source, "id", diagnostics),
        coreid_index=_parse_index(
            _first_child(element, "coreid"), source, "coreid", diagnostics
        ),
        fields=fields,
        text_format=DelimitedTextFormat(
            encoding=element.attrib.get("encoding", "UTF-8"),
            fields_terminated_by=_decode_control_value(
                element.attrib.get("fieldsTerminatedBy", ",")
            ),
            lines_terminated_by=_decode_control_value(
                element.attrib.get("linesTerminatedBy", "\n")
            ),
            fields_enclosed_by=_optional_control_value(
                element.attrib.get("fieldsEnclosedBy", '"')
            ),
            ignore_header_lines=_parse_int_attribute(
                element.attrib.get("ignoreHeaderLines"),
                default=0,
                source=source,
                context=f"{role} ignoreHeaderLines",
                diagnostics=diagnostics,
            ),
        ),
    )


def _parse_field(
    element: ET.Element,
    source: str,
    diagnostics: list[ParserDiagnostic],
) -> ArchiveField:
    return ArchiveField(
        term=element.attrib["term"],
        index=_parse_int_attribute(
            element.attrib.get("index"),
            default=None,
            source=source,
            context=f"field {element.attrib['term']} index",
            diagnostics=diagnostics,
        ),
        default=element.attrib.get("default"),
        delimited_by=element.attrib.get("delimitedBy"),
    )


def _validate_declared_files(
    metadata: ArchiveMetadata,
    available: Any,
    diagnostics: list[ParserDiagnostic],
    source: str,
) -> None:
    for declared_file in metadata.declared_files:
        if not _is_safe_archive_path(declared_file):
            continue
        if not available(declared_file):
            diagnostics.append(
                ParserDiagnostic(
                    severity="error",
                    code="missing_declared_file",
                    message="DwC-A meta.xml declares a file that is not present.",
                    source=source,
                    context=declared_file,
                )
            )


def _locate_meta_xml(
    entries: tuple[str, ...], diagnostics: list[ParserDiagnostic], source: str
) -> str | None:
    if "meta.xml" in entries:
        return "meta.xml"

    candidates = tuple(entry for entry in entries if entry.endswith("/meta.xml"))
    if not candidates:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="missing_meta_xml",
                message="Zip archive does not contain meta.xml.",
                source=source,
            )
        )
        return None
    if len(candidates) > 1:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="ambiguous_meta_xml",
                message="Zip archive contains multiple nested meta.xml files.",
                source=source,
                context=", ".join(candidates),
            )
        )
        return None
    return candidates[0]


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


def _parse_index(
    element: ET.Element | None,
    source: str,
    context: str,
    diagnostics: list[ParserDiagnostic],
) -> int | None:
    if element is None:
        return None
    return _parse_int_attribute(
        element.attrib.get("index"),
        default=None,
        source=source,
        context=f"{context} index",
        diagnostics=diagnostics,
    )


def _parse_int_attribute(
    value: str | None,
    default: int | None,
    source: str,
    context: str,
    diagnostics: list[ParserDiagnostic],
) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="invalid_integer_attribute",
                message="DwC-A meta.xml declares a non-integer attribute.",
                source=source,
                context=f"{context}={value}",
            )
        )
        return default


def _optional_control_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return _decode_control_value(value)


def _decode_control_value(value: str) -> str:
    return (
        value.replace("\\t", "\t")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
    )


def _children(element: ET.Element, local_name: str) -> tuple[ET.Element, ...]:
    return tuple(child for child in element if _local_name(child.tag) == local_name)


def _first_child(element: ET.Element, local_name: str) -> ET.Element | None:
    for child in element:
        if _local_name(child.tag) == local_name:
            return child
    return None


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
