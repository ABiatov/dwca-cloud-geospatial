"""Occurrence-core row reading for inspected Darwin Core Archives."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
import csv
from dataclasses import dataclass
import io
from pathlib import Path
import zipfile

from dwca_cloud_geospatial.inspection import (
    ArchiveField,
    ArchiveInspection,
    ArchiveTable,
    ParserDiagnostic,
    inspect_dwca,
)


@dataclass(frozen=True)
class OccurrenceSourceRecord:
    """A raw occurrence-core source row with parser provenance."""

    source_file: str
    source_row_number: int
    source_data_row_number: int
    source_record_id: str | None
    values_by_term: Mapping[str, str | None]
    raw_values: tuple[str, ...]
    field_metadata: tuple[ArchiveField, ...]
    relationship_keys: Mapping[str, str | None]

    def value_for_term(self, term: str) -> str | None:
        """Return the source/default value for a declared Darwin Core term."""

        return self.values_by_term.get(term)


@dataclass(frozen=True)
class OccurrenceReadResult:
    """Collected occurrence row reader result."""

    inspection: ArchiveInspection
    records: tuple[OccurrenceSourceRecord, ...]
    diagnostics: tuple[ParserDiagnostic, ...]
    source_file: str | None
    rows_read: int
    parse_failures: int

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.severity == "error" for diagnostic in self.diagnostics)


def read_occurrence_rows(path: str | Path) -> OccurrenceReadResult:
    """Read occurrence-core rows from a local DwC-A archive path.

    The result is collected for the current MVP handoff, but the source table
    is read through a streaming ``csv.reader`` over the directory file or zip
    member.
    """

    inspection = inspect_dwca(path)
    diagnostics = list(inspection.diagnostics)
    empty_result = _empty_result_factory(inspection, diagnostics)

    if inspection.has_errors:
        return empty_result(source_file=None)

    if inspection.metadata is None:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="missing_archive_metadata",
                message="Occurrence rows cannot be read because archive metadata is unavailable.",
                source=str(inspection.source_path),
                context=inspection.meta_path,
            )
        )
        return empty_result(source_file=None)

    table = inspection.metadata.occurrence_core
    if table is None:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="missing_occurrence_core",
                message=(
                    "DwC-A metadata does not declare an Occurrence core; "
                    "non-occurrence core files will not be read as occurrence rows."
                ),
                source=str(inspection.source_path),
                context=inspection.meta_path,
            )
        )
        return empty_result(source_file=None)

    if len(table.files) != 1:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="unsupported_multiple_occurrence_core_files",
                message=(
                    "Occurrence core declares multiple file locations; "
                    "multi-file table streaming is deferred."
                ),
                source=inspection.meta_path or str(inspection.source_path),
                context=", ".join(table.files) if table.files else None,
            )
        )
        return empty_result(source_file=None)

    source_file = table.files[0]
    records: list[OccurrenceSourceRecord] = []
    parse_failures = 0

    try:
        with _open_declared_text_file(inspection, source_file) as text_file:
            reader = _make_csv_reader(text_file, table)
            for _ in range(table.text_format.ignore_header_lines):
                try:
                    next(reader)
                except StopIteration:
                    break
                except csv.Error as exc:
                    parse_failures += 1
                    diagnostics.append(
                        _row_parse_diagnostic(
                            inspection=inspection,
                            source_file=source_file,
                            source_row_number=max(reader.line_num, 1),
                            exc=exc,
                        )
                    )
                    break

            source_data_row_number = 1
            while True:
                try:
                    row = next(reader)
                except StopIteration:
                    break
                except csv.Error as exc:
                    parse_failures += 1
                    diagnostics.append(
                        _row_parse_diagnostic(
                            inspection=inspection,
                            source_file=source_file,
                            source_row_number=max(reader.line_num, 1),
                            exc=exc,
                        )
                    )
                    break

                source_row_number = reader.line_num
                records.append(
                    _record_from_row(
                        table=table,
                        source_file=source_file,
                        source_row_number=source_row_number,
                        source_data_row_number=source_data_row_number,
                        row=row,
                    )
                )
                source_data_row_number += 1
    except (KeyError, OSError) as exc:
        diagnostics.append(
            ParserDiagnostic(
                severity="error",
                code="occurrence_core_read_error",
                message=f"Could not read occurrence core file: {exc}",
                source=str(inspection.source_path),
                context=source_file,
            )
        )

    return OccurrenceReadResult(
        inspection=inspection,
        records=tuple(records),
        diagnostics=tuple(diagnostics),
        source_file=source_file,
        rows_read=len(records),
        parse_failures=parse_failures,
    )


def iter_occurrence_rows(path: str | Path) -> Iterator[OccurrenceSourceRecord]:
    """Yield occurrence source records from ``path``.

    This convenience iterator raises ``ValueError`` when row reading produced
    parser errors. Use ``read_occurrence_rows`` when diagnostics are needed.
    """

    result = read_occurrence_rows(path)
    if result.has_errors:
        codes = ", ".join(diagnostic.code for diagnostic in result.diagnostics)
        raise ValueError(f"Occurrence rows could not be read: {codes}")
    yield from result.records


def _record_from_row(
    *,
    table: ArchiveTable,
    source_file: str,
    source_row_number: int,
    source_data_row_number: int,
    row: list[str],
) -> OccurrenceSourceRecord:
    values_by_term: dict[str, str | None] = {}
    for field in table.fields:
        values_by_term[field.term] = _value_for_field(field, row)

    relationship_keys: dict[str, str | None] = {}
    if table.id_index is not None:
        relationship_keys["_id"] = _value_for_index(table.id_index, row)
    if table.coreid_index is not None:
        relationship_keys["_coreid"] = _value_for_index(table.coreid_index, row)

    source_record_id = (
        relationship_keys.get("_id") if table.id_index is not None else None
    )
    if source_record_id == "":
        source_record_id = None

    return OccurrenceSourceRecord(
        source_file=source_file,
        source_row_number=source_row_number,
        source_data_row_number=source_data_row_number,
        source_record_id=source_record_id,
        values_by_term=values_by_term,
        raw_values=tuple(row),
        field_metadata=table.fields,
        relationship_keys=relationship_keys,
    )


def _value_for_field(field: ArchiveField, row: list[str]) -> str | None:
    if field.index is None:
        return field.default
    if field.index >= len(row):
        return field.default
    return row[field.index]


def _value_for_index(index: int, row: list[str]) -> str | None:
    if index >= len(row):
        return None
    return row[index]


def _make_csv_reader(text_file: io.TextIOBase, table: ArchiveTable) -> csv.reader:
    text_format = table.text_format
    quotechar = text_format.fields_enclosed_by
    return csv.reader(
        text_file,
        delimiter=text_format.fields_terminated_by,
        quotechar=quotechar,
        quoting=csv.QUOTE_MINIMAL if quotechar else csv.QUOTE_NONE,
        strict=True,
    )


def _open_declared_text_file(
    inspection: ArchiveInspection, source_file: str
) -> io.TextIOBase:
    if inspection.archive_kind == "directory":
        raw_file = (inspection.source_path / source_file).open(
            "r",
            encoding=_occurrence_encoding(inspection),
            newline="",
        )
        return raw_file

    if inspection.archive_kind == "zip":
        archive = zipfile.ZipFile(inspection.source_path)
        member = _zip_member_path(inspection, source_file)
        binary_file = archive.open(member)
        text_file = io.TextIOWrapper(
            binary_file,
            encoding=_occurrence_encoding(inspection),
            newline="",
        )
        return _ZipTextFile(text_file, archive)

    raise OSError(f"Unsupported archive kind for occurrence row reading: {inspection.archive_kind}")


class _ZipTextFile(io.TextIOBase):
    """Text wrapper that also closes the owning zip archive."""

    def __init__(self, text_file: io.TextIOWrapper, archive: zipfile.ZipFile) -> None:
        self._text_file = text_file
        self._archive = archive

    def readable(self) -> bool:
        return True

    def readline(self, size: int = -1) -> str:
        return self._text_file.readline(size)

    def close(self) -> None:
        try:
            self._text_file.close()
        finally:
            self._archive.close()
        super().close()

    @property
    def closed(self) -> bool:
        return self._text_file.closed


def _occurrence_encoding(inspection: ArchiveInspection) -> str:
    assert inspection.metadata is not None
    assert inspection.metadata.occurrence_core is not None
    return inspection.metadata.occurrence_core.text_format.encoding


def _zip_member_path(inspection: ArchiveInspection, source_file: str) -> str:
    if inspection.meta_path and "/" in inspection.meta_path:
        return f"{inspection.meta_path.rsplit('/', 1)[0]}/{source_file}"
    return source_file


def _row_parse_diagnostic(
    *,
    inspection: ArchiveInspection,
    source_file: str,
    source_row_number: int | None,
    exc: csv.Error,
) -> ParserDiagnostic:
    row_context = (
        f"{source_file}:{source_row_number}" if source_row_number is not None else source_file
    )
    return ParserDiagnostic(
        severity="error",
        code="occurrence_row_parse_error",
        message=f"Could not parse occurrence core row: {exc}",
        source=str(inspection.source_path),
        context=row_context,
    )


def _empty_result_factory(
    inspection: ArchiveInspection, diagnostics: list[ParserDiagnostic]
):
    def _empty_result(source_file: str | None) -> OccurrenceReadResult:
        return OccurrenceReadResult(
            inspection=inspection,
            records=(),
            diagnostics=tuple(diagnostics),
            source_file=source_file,
            rows_read=0,
            parse_failures=sum(
                1 for diagnostic in diagnostics if diagnostic.code == "occurrence_row_parse_error"
            ),
        )

    return _empty_result
