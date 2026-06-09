"""Normalize Darwin Core occurrence source records into project fields."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime
import math
import re
from typing import Any

from dwca_cloud_geospatial.occurrence import OccurrenceSourceRecord


DWC_TERM_BASE = "http://rs.tdwg.org/dwc/terms/"
DC_TERMS_BASE = "http://purl.org/dc/terms/"
GBIF_TERM_BASE = "http://rs.gbif.org/terms/1.0/"
OBIS_TERM_BASE = "http://rs.iobis.org/obis/terms/"

MISSING_COORDINATES = "missing_coordinates"
INVALID_LATITUDE = "invalid_latitude"
INVALID_LONGITUDE = "invalid_longitude"
COORDINATE_OUT_OF_RANGE = "coordinate_out_of_range"
ZERO_ZERO_COORDINATE = "zero_zero_coordinate"
MISSING_REQUIRED_FIELD = "missing_required_field"
ROW_PARSE_ERROR = "row_parse_error"
TYPE_CONVERSION_FAILED = "type_conversion_failed"
INVALID_FLOAT = "invalid_float"
INVALID_INTEGER = "invalid_integer"

NULL_VALUE_ACTION = "null_value"
RECORD_REJECTED_ACTION = "record_rejected"
CONVERSION_FAILED_ACTION = "conversion_failed"

OPTIONAL_CONVERSION_WARNING_RATE = 0.05

MISSING_SCIENTIFIC_NAME_FLAG = "missing_scientific_name"
MISSING_EVENT_DATE_FLAG = "missing_event_date"
MISSING_COORDINATE_UNCERTAINTY_FLAG = "missing_coordinate_uncertainty"
INVALID_COORDINATE_UNCERTAINTY_FLAG = "invalid_coordinate_uncertainty"
MISSING_GEODETIC_DATUM_FLAG = "missing_geodetic_datum"
INVALID_EVENT_YEAR_FLAG = "invalid_event_year"

QUALITY_FLAG_CODES: tuple[str, ...] = (
    MISSING_SCIENTIFIC_NAME_FLAG,
    MISSING_EVENT_DATE_FLAG,
    MISSING_COORDINATE_UNCERTAINTY_FLAG,
    INVALID_COORDINATE_UNCERTAINTY_FLAG,
    MISSING_GEODETIC_DATUM_FLAG,
    INVALID_EVENT_YEAR_FLAG,
)

REJECTION_REASON_MESSAGES: Mapping[str, str] = {
    MISSING_COORDINATES: "Latitude or longitude is empty or absent.",
    INVALID_LATITUDE: "Latitude cannot be parsed as a finite number.",
    INVALID_LONGITUDE: "Longitude cannot be parsed as a finite number.",
    COORDINATE_OUT_OF_RANGE: "Latitude or longitude is outside valid ranges.",
    ZERO_ZERO_COORDINATE: "Coordinate is exactly 0,0 and excluded by policy.",
    MISSING_REQUIRED_FIELD: "A required field is absent or empty.",
    ROW_PARSE_ERROR: "Row cannot be parsed according to DwC-A metadata.",
    TYPE_CONVERSION_FAILED: "Required type conversion failed.",
}

_YEAR_PATTERN = re.compile(r"^\d{4}$")
_YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
_YEAR_MONTH_DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_QUALITY_FLAG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class NormalizedOccurrenceRecord:
    """Accepted occurrence record using the MVP canonical snake_case schema."""

    source_record_id: str
    source_file: str
    source_row_number: int
    source_data_row_number: int | None
    occurrence_id: str | None
    scientific_name: str | None
    verbatim_scientific_name: str | None
    kingdom: str | None
    phylum: str | None
    class_: str | None
    order: str | None
    family: str | None
    genus: str | None
    taxon_id: str | None
    taxon_rank: str | None
    identified_by: str | None
    basis_of_record: str | None
    degree_of_establishment: str | None
    event_date: str | None
    event_year: int | None
    recorded_by: str | None
    decimal_longitude: float
    decimal_latitude: float
    coordinate_uncertainty_in_meters: float | None
    geodetic_datum: str | None
    country_code: str | None
    locality: str | None
    dataset_name: str | None
    dataset_key: str | None
    publisher: str | None
    license: str | None
    rights_holder: str | None
    references: str | None
    quality_flags: str | None
    has_quality_flags: bool
    iucn_red_list_category: str | None
    catalog_number: str | None
    collection_code: str | None
    institution_code: str | None
    record_number: str | None
    organism_id: str | None
    gbif_id: str | None
    obis_id: str | None
    raw_decimal_longitude: str | None
    raw_decimal_latitude: str | None
    raw_event_date: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["class"] = data.pop("class_")
        return data


@dataclass(frozen=True)
class RejectedOccurrenceRecord:
    """Rejected occurrence row aligned with ``reports/rejected_records.csv``."""

    source_file: str
    source_row_number: int
    source_record_id: str | None
    occurrence_id: str | None
    scientific_name: str | None
    decimal_longitude: str | None
    decimal_latitude: str | None
    event_date: str | None
    reason_code: str
    reason_message: str
    source_data_row_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OccurrenceNormalizationCounts:
    """Counts that reconcile parser source records and normalization output."""

    source_records: int
    parsed_records: int
    accepted_records: int
    rejected_records: int
    warning_count: int = 0


@dataclass(frozen=True)
class TypeConversionFailure:
    """Counted type conversion or critical validation failure."""

    field: str
    reason_code: str
    failure_count: int
    failure_rate: float
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OccurrenceNormalizationWarning:
    """Non-fatal normalization warning for later processing metadata."""

    code: str
    message: str
    field: str
    reason_code: str
    failure_count: int
    failure_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OccurrenceNormalizationResult:
    """Batch normalization result for occurrence source records."""

    accepted_records: tuple[NormalizedOccurrenceRecord, ...]
    rejected_records: tuple[RejectedOccurrenceRecord, ...]
    counts: OccurrenceNormalizationCounts
    type_conversion_failures: tuple[TypeConversionFailure, ...] = ()
    warnings: tuple[OccurrenceNormalizationWarning, ...] = ()


@dataclass(frozen=True)
class _ConversionFailureEvent:
    field: str
    reason_code: str
    action: str


def _dwc(local_name: str) -> str:
    return f"{DWC_TERM_BASE}{local_name}"


def _dc(local_name: str) -> str:
    return f"{DC_TERMS_BASE}{local_name}"


def _gbif(local_name: str) -> str:
    return f"{GBIF_TERM_BASE}{local_name}"


def _obis(local_name: str) -> str:
    return f"{OBIS_TERM_BASE}{local_name}"


NORMALIZED_FIELD_TERMS: Mapping[str, tuple[str, ...]] = {
    "occurrence_id": (_dwc("occurrenceID"),),
    "scientific_name": (_dwc("scientificName"),),
    "verbatim_scientific_name": (_dwc("verbatimScientificName"),),
    "kingdom": (_dwc("kingdom"),),
    "phylum": (_dwc("phylum"),),
    "class_": (_dwc("class"),),
    "order": (_dwc("order"),),
    "family": (_dwc("family"),),
    "genus": (_dwc("genus"),),
    "taxon_id": (_dwc("taxonID"),),
    "taxon_rank": (_dwc("taxonRank"),),
    "identified_by": (_dwc("identifiedBy"),),
    "basis_of_record": (_dwc("basisOfRecord"),),
    "degree_of_establishment": (_dwc("degreeOfEstablishment"),),
    "event_date": (_dwc("eventDate"),),
    "year": (_dwc("year"),),
    "recorded_by": (_dwc("recordedBy"),),
    "decimal_longitude": (_dwc("decimalLongitude"),),
    "decimal_latitude": (_dwc("decimalLatitude"),),
    "coordinate_uncertainty_in_meters": (_dwc("coordinateUncertaintyInMeters"),),
    "geodetic_datum": (_dwc("geodeticDatum"),),
    "country_code": (_dwc("countryCode"),),
    "locality": (_dwc("locality"),),
    "dataset_name": (_dwc("datasetName"),),
    "dataset_key": (_gbif("datasetKey"), _dwc("datasetKey"), _obis("dataset_id")),
    "publisher": (_dc("publisher"), _dwc("publisher")),
    "license": (_dc("license"), _dwc("license")),
    "rights_holder": (_dwc("rightsHolder"), _dc("rightsHolder")),
    "references": (_dc("references"), _dwc("references")),
    "iucn_red_list_category": (
        _gbif("iucnRedListCategory"),
        _dwc("iucnRedListCategory"),
    ),
    "catalog_number": (_dwc("catalogNumber"),),
    "collection_code": (_dwc("collectionCode"),),
    "institution_code": (_dwc("institutionCode"),),
    "record_number": (_dwc("recordNumber"),),
    "organism_id": (_dwc("organismID"),),
    "gbif_id": (_gbif("gbifID"), _dwc("gbifID")),
    "obis_id": (_obis("id"), _obis("obisID"), _dwc("obisID")),
}


def normalize_occurrence_records(
    records: Iterable[OccurrenceSourceRecord],
) -> OccurrenceNormalizationResult:
    """Normalize parser source records into accepted and rejected records."""

    accepted: list[NormalizedOccurrenceRecord] = []
    rejected: list[RejectedOccurrenceRecord] = []
    conversion_failure_events: list[_ConversionFailureEvent] = []
    source_count = 0

    for record in records:
        source_count += 1
        normalized, failure_events = _normalize_occurrence_record_with_failures(record)
        conversion_failure_events.extend(failure_events)
        if isinstance(normalized, RejectedOccurrenceRecord):
            rejected.append(normalized)
        else:
            accepted.append(normalized)

    type_conversion_failures = _type_conversion_failures(
        conversion_failure_events, source_count
    )
    warnings = _normalization_warnings(type_conversion_failures)

    return OccurrenceNormalizationResult(
        accepted_records=tuple(accepted),
        rejected_records=tuple(rejected),
        counts=OccurrenceNormalizationCounts(
            source_records=source_count,
            parsed_records=source_count,
            accepted_records=len(accepted),
            rejected_records=len(rejected),
            warning_count=len(warnings),
        ),
        type_conversion_failures=type_conversion_failures,
        warnings=warnings,
    )


def normalize_occurrence_record(
    record: OccurrenceSourceRecord,
) -> NormalizedOccurrenceRecord | RejectedOccurrenceRecord:
    """Normalize one occurrence source record or return its rejection model."""

    normalized, _failure_events = _normalize_occurrence_record_with_failures(record)
    return normalized


def _normalize_occurrence_record_with_failures(
    record: OccurrenceSourceRecord,
) -> tuple[
    NormalizedOccurrenceRecord | RejectedOccurrenceRecord,
    tuple[_ConversionFailureEvent, ...],
]:
    failure_events: list[_ConversionFailureEvent] = []

    raw_latitude = _term_value(record, "decimal_latitude")
    raw_longitude = _term_value(record, "decimal_longitude")
    occurrence_id = _term_value(record, "occurrence_id")
    scientific_name = _term_value(record, "scientific_name")
    raw_event_date = _term_value(record, "event_date")

    provenance_failure_field = _required_provenance_failure_field(record)
    if provenance_failure_field is not None:
        failure_events.append(
            _ConversionFailureEvent(
                field=provenance_failure_field,
                reason_code=MISSING_REQUIRED_FIELD,
                action=RECORD_REJECTED_ACTION,
            )
        )
        return (
            _rejected_record(
                record=record,
                occurrence_id=occurrence_id,
                scientific_name=scientific_name,
                raw_longitude=raw_longitude,
                raw_latitude=raw_latitude,
                raw_event_date=raw_event_date,
                reason_code=MISSING_REQUIRED_FIELD,
            ),
            tuple(failure_events),
        )

    coordinate_error = _coordinate_rejection_reason(raw_longitude, raw_latitude)
    if coordinate_error is not None:
        failure_events.append(
            _ConversionFailureEvent(
                field=_coordinate_failure_field(
                    coordinate_error, raw_longitude, raw_latitude
                ),
                reason_code=coordinate_error,
                action=RECORD_REJECTED_ACTION,
            )
        )
        return (
            _rejected_record(
                record=record,
                occurrence_id=occurrence_id,
                scientific_name=scientific_name,
                raw_longitude=raw_longitude,
                raw_latitude=raw_latitude,
                raw_event_date=raw_event_date,
                reason_code=coordinate_error,
            ),
            tuple(failure_events),
        )

    assert raw_longitude is not None
    assert raw_latitude is not None
    decimal_longitude = _parse_float(raw_longitude)
    decimal_latitude = _parse_float(raw_latitude)
    assert decimal_longitude is not None
    assert decimal_latitude is not None

    event_date, event_year = _normalize_event_date(raw_event_date)
    invalid_event_year = False
    if event_year is None:
        raw_year = _term_value(record, "year")
        event_year = _parse_year(raw_year)
        if _blank_to_none(raw_year) is not None and event_year is None:
            invalid_event_year = True
            failure_events.append(
                _ConversionFailureEvent(
                    field="event_year",
                    reason_code=INVALID_INTEGER,
                    action=NULL_VALUE_ACTION,
                )
            )

    raw_coordinate_uncertainty = _term_value(
        record, "coordinate_uncertainty_in_meters"
    )
    coordinate_uncertainty, invalid_coordinate_uncertainty = _parse_optional_float_value(
        raw_coordinate_uncertainty
    )
    if invalid_coordinate_uncertainty:
        failure_events.append(
            _ConversionFailureEvent(
                field="coordinate_uncertainty_in_meters",
                reason_code=INVALID_FLOAT,
                action=NULL_VALUE_ACTION,
            )
        )

    quality_flags = _format_quality_flags(
        _quality_flags_for_record(
            scientific_name=scientific_name,
            event_date=event_date,
            event_year=event_year,
            raw_coordinate_uncertainty=raw_coordinate_uncertainty,
            invalid_coordinate_uncertainty=invalid_coordinate_uncertainty,
            geodetic_datum=_term_value(record, "geodetic_datum"),
            invalid_event_year=invalid_event_year,
        )
    )

    return (
        NormalizedOccurrenceRecord(
            source_record_id=_source_record_id(record, occurrence_id),
            source_file=record.source_file,
            source_row_number=record.source_row_number,
            source_data_row_number=record.source_data_row_number,
            occurrence_id=occurrence_id,
            scientific_name=scientific_name,
            verbatim_scientific_name=_term_value(record, "verbatim_scientific_name"),
            kingdom=_term_value(record, "kingdom"),
            phylum=_term_value(record, "phylum"),
            class_=_term_value(record, "class_"),
            order=_term_value(record, "order"),
            family=_term_value(record, "family"),
            genus=_term_value(record, "genus"),
            taxon_id=_term_value(record, "taxon_id"),
            taxon_rank=_term_value(record, "taxon_rank"),
            identified_by=_term_value(record, "identified_by"),
            basis_of_record=_term_value(record, "basis_of_record"),
            degree_of_establishment=_term_value(record, "degree_of_establishment"),
            event_date=event_date,
            event_year=event_year,
            recorded_by=_term_value(record, "recorded_by"),
            decimal_longitude=decimal_longitude,
            decimal_latitude=decimal_latitude,
            coordinate_uncertainty_in_meters=coordinate_uncertainty,
            geodetic_datum=_term_value(record, "geodetic_datum"),
            country_code=_term_value(record, "country_code"),
            locality=_term_value(record, "locality"),
            dataset_name=_term_value(record, "dataset_name"),
            dataset_key=_term_value(record, "dataset_key"),
            publisher=_term_value(record, "publisher"),
            license=_term_value(record, "license"),
            rights_holder=_term_value(record, "rights_holder"),
            references=_term_value(record, "references"),
            quality_flags=quality_flags,
            has_quality_flags=quality_flags is not None,
            iucn_red_list_category=_term_value(record, "iucn_red_list_category"),
            catalog_number=_term_value(record, "catalog_number"),
            collection_code=_term_value(record, "collection_code"),
            institution_code=_term_value(record, "institution_code"),
            record_number=_term_value(record, "record_number"),
            organism_id=_term_value(record, "organism_id"),
            gbif_id=_term_value(record, "gbif_id"),
            obis_id=_term_value(record, "obis_id"),
            raw_decimal_longitude=raw_longitude,
            raw_decimal_latitude=raw_latitude,
            raw_event_date=raw_event_date,
        ),
        tuple(failure_events),
    )


def _coordinate_rejection_reason(
    raw_longitude: str | None, raw_latitude: str | None
) -> str | None:
    if raw_longitude is None or raw_latitude is None:
        return MISSING_COORDINATES

    longitude = _parse_float(raw_longitude)
    latitude = _parse_float(raw_latitude)
    if latitude is None:
        return INVALID_LATITUDE
    if longitude is None:
        return INVALID_LONGITUDE
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return COORDINATE_OUT_OF_RANGE
    if latitude == 0 and longitude == 0:
        return ZERO_ZERO_COORDINATE
    return None


def _required_provenance_failure_field(record: OccurrenceSourceRecord) -> str | None:
    if _blank_to_none(record.source_file) is None:
        return "source_file"
    if record.source_row_number < 1:
        return "source_row_number"
    return None


def _coordinate_failure_field(
    reason_code: str, raw_longitude: str | None, raw_latitude: str | None
) -> str:
    if reason_code == INVALID_LATITUDE:
        return "decimal_latitude"
    if reason_code == INVALID_LONGITUDE:
        return "decimal_longitude"
    if reason_code == MISSING_COORDINATES:
        if raw_latitude is None and raw_longitude is not None:
            return "decimal_latitude"
        if raw_longitude is None and raw_latitude is not None:
            return "decimal_longitude"
    if reason_code == COORDINATE_OUT_OF_RANGE:
        latitude = _parse_float(raw_latitude) if raw_latitude is not None else None
        longitude = _parse_float(raw_longitude) if raw_longitude is not None else None
        if latitude is not None and not (-90 <= latitude <= 90):
            return "decimal_latitude"
        if longitude is not None and not (-180 <= longitude <= 180):
            return "decimal_longitude"
    return "coordinates"


def _rejected_record(
    *,
    record: OccurrenceSourceRecord,
    occurrence_id: str | None,
    scientific_name: str | None,
    raw_longitude: str | None,
    raw_latitude: str | None,
    raw_event_date: str | None,
    reason_code: str,
) -> RejectedOccurrenceRecord:
    return RejectedOccurrenceRecord(
        source_file=record.source_file,
        source_row_number=record.source_row_number,
        source_record_id=_source_record_id_or_none(record, occurrence_id),
        occurrence_id=occurrence_id,
        scientific_name=scientific_name,
        decimal_longitude=raw_longitude,
        decimal_latitude=raw_latitude,
        event_date=raw_event_date,
        reason_code=reason_code,
        reason_message=REJECTION_REASON_MESSAGES[reason_code],
        source_data_row_number=record.source_data_row_number,
    )


def _source_record_id(
    record: OccurrenceSourceRecord, occurrence_id: str | None
) -> str:
    return _source_record_id_or_none(record, occurrence_id) or (
        f"{record.source_file}:{record.source_row_number}"
    )


def _source_record_id_or_none(
    record: OccurrenceSourceRecord, occurrence_id: str | None
) -> str | None:
    return _blank_to_none(record.source_record_id) or occurrence_id


def _term_value(record: OccurrenceSourceRecord, normalized_field: str) -> str | None:
    for term in NORMALIZED_FIELD_TERMS[normalized_field]:
        value = _blank_to_none(record.value_for_term(term))
        if value is not None:
            return value
    return None


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_float(value: str) -> float | None:
    try:
        parsed = float(value.strip())
    except ValueError:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _parse_optional_float_value(value: str | None) -> tuple[float | None, bool]:
    value = _blank_to_none(value)
    if value is None:
        return None, False
    parsed = _parse_float(value)
    return parsed, parsed is None


def _normalize_event_date(value: str | None) -> tuple[str | None, int | None]:
    value = _blank_to_none(value)
    if value is None:
        return None, None

    if _YEAR_PATTERN.fullmatch(value):
        return value, int(value)
    if _YEAR_MONTH_PATTERN.fullmatch(value):
        return value, int(value[:4])
    if _YEAR_MONTH_DAY_PATTERN.fullmatch(value):
        try:
            parsed_date = date.fromisoformat(value)
        except ValueError:
            return value, _year_prefix(value)
        return parsed_date.isoformat(), parsed_date.year

    if "/" in value:
        start, _separator, _end = value.partition("/")
        normalized_start, year = _normalize_event_date(start)
        return value, year if normalized_start is not None else _year_prefix(value)

    datetime_value = value.replace("Z", "+00:00")
    try:
        parsed_datetime = datetime.fromisoformat(datetime_value)
    except ValueError:
        return value, _year_prefix(value)
    return parsed_datetime.date().isoformat(), parsed_datetime.year


def _parse_year(value: str | None) -> int | None:
    value = _blank_to_none(value)
    if value is None:
        return None
    try:
        year = int(value)
    except ValueError:
        return None
    if 0 < year <= 9999:
        return year
    return None


def _year_prefix(value: str) -> int | None:
    prefix = value[:4]
    if _YEAR_PATTERN.fullmatch(prefix):
        return int(prefix)
    return None


def _quality_flags_for_record(
    *,
    scientific_name: str | None,
    event_date: str | None,
    event_year: int | None,
    raw_coordinate_uncertainty: str | None,
    invalid_coordinate_uncertainty: bool,
    geodetic_datum: str | None,
    invalid_event_year: bool,
) -> tuple[str, ...]:
    flags: list[str] = []
    if scientific_name is None:
        flags.append(MISSING_SCIENTIFIC_NAME_FLAG)
    if event_date is None and event_year is None:
        flags.append(MISSING_EVENT_DATE_FLAG)
    if _blank_to_none(raw_coordinate_uncertainty) is None:
        flags.append(MISSING_COORDINATE_UNCERTAINTY_FLAG)
    elif invalid_coordinate_uncertainty:
        flags.append(INVALID_COORDINATE_UNCERTAINTY_FLAG)
    if geodetic_datum is None:
        flags.append(MISSING_GEODETIC_DATUM_FLAG)
    if invalid_event_year:
        flags.append(INVALID_EVENT_YEAR_FLAG)
    return tuple(flags)


def _format_quality_flags(flags: tuple[str, ...]) -> str | None:
    if not flags:
        return None
    for flag in flags:
        if "|" in flag or _QUALITY_FLAG_PATTERN.fullmatch(flag) is None:
            raise ValueError(f"Invalid quality flag code: {flag}")
    return "|".join(flags)


def _type_conversion_failures(
    events: Iterable[_ConversionFailureEvent], parsed_records: int
) -> tuple[TypeConversionFailure, ...]:
    counter = Counter(events)
    failures: list[TypeConversionFailure] = []
    for event, count in sorted(
        counter.items(),
        key=lambda item: (item[0].field, item[0].reason_code, item[0].action),
    ):
        failures.append(
            TypeConversionFailure(
                field=event.field,
                reason_code=event.reason_code,
                failure_count=count,
                failure_rate=count / parsed_records if parsed_records else 0,
                action=event.action,
            )
        )
    return tuple(failures)


def _normalization_warnings(
    failures: Iterable[TypeConversionFailure],
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
