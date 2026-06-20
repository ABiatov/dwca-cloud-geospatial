"""GBIF occurrence download DOI and citation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import random
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


GBIF_API_BASE_URL = "https://api.gbif.org/v1"
DEFAULT_GBIF_USER_AGENT = (
    "dwca-cloud-geospatial/0.1 "
    "(https://github.com/ABiatov/biodiversity-viewer-serverless)"
)

DOWNLOAD_KEY_PATTERN = re.compile(r"(?<!\d)(\d{7}-\d{15})(?!\d)")
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
DOI_URL_PATTERN = re.compile(
    r"https:\s*//doi\.org/(10\.\d{4,9}/\S+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GbifDownloadMetadata:
    """Resolved GBIF occurrence download provenance."""

    download_key: str | None = None
    doi: str | None = None
    citation: str | None = None
    license: str | None = None


@dataclass(frozen=True)
class GbifDownloadOptions:
    """Optional GBIF occurrence download DOI/citation enrichment controls."""

    download_key: str | None = None
    doi: str | None = None
    citation: str | None = None
    enrich: bool = False
    api_base_url: str = GBIF_API_BASE_URL
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 20.0
    max_retries: int = 2
    user_agent: str = DEFAULT_GBIF_USER_AGENT


@dataclass(frozen=True)
class GbifEnrichmentResult:
    """GBIF metadata plus non-fatal conversion warnings."""

    metadata: GbifDownloadMetadata
    warnings: tuple[dict[str, Any], ...] = ()


class GbifDownloadMetadataError(RuntimeError):
    """Raised when optional GBIF download metadata lookup fails."""


def normalize_download_key(value: str | None) -> str | None:
    """Return a GBIF download key when ``value`` is exactly one key."""

    if value is None:
        return None
    candidate = value.strip()
    return candidate if DOWNLOAD_KEY_PATTERN.fullmatch(candidate) else None


def extract_download_key_from_text(value: str | None) -> str | None:
    """Extract the first GBIF occurrence download key from text or a URL."""

    if not value:
        return None
    match = DOWNLOAD_KEY_PATTERN.search(value)
    return match.group(1) if match else None


def infer_download_key_from_path_name(value: str | None) -> str | None:
    """Infer a key only when a filename or directory name exactly matches it."""

    if not value:
        return None
    name = value.strip().rsplit("/", 1)[-1]
    if name.endswith(".zip"):
        name = name[:-4]
    return normalize_download_key(name)


def extract_download_key_from_eml_xml(xml_bytes: bytes | str | None) -> str | None:
    """Extract a GBIF download key from EML/additional metadata."""

    if not xml_bytes:
        return None
    if isinstance(xml_bytes, str):
        payload = xml_bytes.encode("utf-8")
    else:
        payload = xml_bytes
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return None

    for element in root.iter():
        for attribute in ("identifier", "id", "downloadKey", "download_key"):
            key = extract_download_key_from_text(element.attrib.get(attribute))
            if key:
                return key
        if _local_name(element.tag) in {"citation", "url", "onlineUrl"}:
            key = extract_download_key_from_text(_element_text(element))
            if key:
                return key
    return extract_download_key_from_text(_element_text(root))


def normalize_doi(value: str | None) -> str | None:
    """Normalize a bare DOI or doi.org URL to a bare DOI string."""

    if value is None:
        return None
    candidate = value.strip().rstrip(".,")
    if not candidate:
        return None
    url_match = DOI_URL_PATTERN.search(candidate)
    if url_match:
        candidate = url_match.group(1).rstrip(".,")
    if candidate.lower().startswith("doi:"):
        candidate = candidate[4:].strip()
    return candidate if DOI_PATTERN.fullmatch(candidate) else None


def normalize_citation_text(value: str | None) -> str | None:
    """Normalize GBIF citation text enough to preserve DOI links."""

    text = _clean_text(value)
    if text is None:
        return None
    return re.sub(r"https:\s*//doi\.org/", "https://doi.org/", text, flags=re.IGNORECASE)


def doi_url(value: str | None) -> str | None:
    """Return a canonical doi.org URL for a bare DOI or DOI URL value."""

    doi = normalize_doi(value)
    return f"https://doi.org/{doi}" if doi else None


def format_gbif_download_citation(metadata: dict[str, Any]) -> str | None:
    """Format GBIF's recommended occurrence download citation when possible."""

    existing = _clean_text(metadata.get("citation"))
    if existing:
        return normalize_citation_text(existing)

    doi = normalize_doi(_clean_text(metadata.get("doi")))
    if not doi:
        return None

    created = _parse_date(_clean_text(metadata.get("created")))
    date_text = (
        f"{created.day} {created.strftime('%B')} {created.year}" if created else None
    )
    if date_text:
        return f"GBIF.org ({date_text}) GBIF Occurrence Download https://doi.org/{doi}"
    return f"GBIF.org GBIF Occurrence Download https://doi.org/{doi}"


class GbifDownloadClient:
    """Small direct REST client for read-only GBIF download metadata."""

    def __init__(
        self,
        *,
        api_base_url: str = GBIF_API_BASE_URL,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 20.0,
        max_retries: int = 2,
        user_agent: str = DEFAULT_GBIF_USER_AGENT,
        sleep=time.sleep,
        jitter=random.uniform,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.connect_timeout_seconds = connect_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self.max_retries = max(0, max_retries)
        self.user_agent = user_agent
        self._sleep = sleep
        self._jitter = jitter

    def fetch_download_metadata(self, download_key: str) -> dict[str, Any]:
        """Fetch ``GET /occurrence/download/{download_key}`` as JSON."""

        key = normalize_download_key(download_key)
        if key is None:
            raise GbifDownloadMetadataError(f"Invalid GBIF download key: {download_key!r}")

        text = self._fetch_text(
            f"{self.api_base_url}/occurrence/download/{key}",
            accept="application/json",
            error_context="GBIF download metadata request",
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise GbifDownloadMetadataError(
                "GBIF download metadata request returned invalid JSON"
            ) from exc

    def fetch_download_citation(self, download_key: str) -> str:
        """Fetch ``GET /occurrence/download/{download_key}/citation``."""

        key = normalize_download_key(download_key)
        if key is None:
            raise GbifDownloadMetadataError(f"Invalid GBIF download key: {download_key!r}")
        return self._fetch_text(
            f"{self.api_base_url}/occurrence/download/{key}/citation",
            accept="text/plain, */*",
            error_context="GBIF download citation request",
        )

    def _fetch_text(self, url: str, *, accept: str, error_context: str) -> str:
        timeout = max(self.connect_timeout_seconds, self.read_timeout_seconds)
        for attempt in range(self.max_retries + 1):
            request = Request(
                url,
                headers={
                    "Accept": accept,
                    "User-Agent": self.user_agent,
                },
                method="GET",
            )
            try:
                with urlopen(request, timeout=timeout) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    return response.read().decode(charset)
            except HTTPError as exc:
                if exc.code == 429 and attempt < self.max_retries:
                    self._sleep(_retry_after_seconds(exc) or self._backoff(attempt))
                    continue
                if 500 <= exc.code < 600 and attempt < self.max_retries:
                    self._sleep(self._backoff(attempt))
                    continue
                raise GbifDownloadMetadataError(
                    f"{error_context} failed with HTTP {exc.code}"
                ) from exc
            except (OSError, URLError) as exc:
                if attempt < self.max_retries:
                    self._sleep(self._backoff(attempt))
                    continue
                raise GbifDownloadMetadataError(
                    f"{error_context} failed: {exc}"
                ) from exc
        raise GbifDownloadMetadataError(f"{error_context} failed")

    def _backoff(self, attempt: int) -> float:
        return min(30.0, (0.5 * (2**attempt)) + self._jitter(0.0, 0.25))


def metadata_from_api_payload(
    payload: dict[str, Any],
    *,
    download_key: str | None = None,
) -> GbifDownloadMetadata:
    """Build normalized GBIF download metadata from an API response."""

    response_key = normalize_download_key(_clean_text(payload.get("key")))
    resolved_key = download_key or response_key
    doi = normalize_doi(_clean_text(payload.get("doi")))
    citation = format_gbif_download_citation(payload)
    return GbifDownloadMetadata(
        download_key=resolved_key,
        doi=doi,
        citation=citation,
        license=_clean_text(payload.get("license")),
    )


def metadata_from_citation_text(
    citation: str | None,
    *,
    download_key: str | None = None,
    license: str | None = None,
) -> GbifDownloadMetadata:
    """Build normalized GBIF download metadata from citation endpoint text."""

    normalized_citation = normalize_citation_text(citation)
    return GbifDownloadMetadata(
        download_key=download_key,
        doi=normalize_doi(normalized_citation),
        citation=normalized_citation,
        license=license,
    )


def resolve_gbif_download_metadata(
    *,
    options: GbifDownloadOptions,
    inferred_download_key: str | None = None,
    client: GbifDownloadClient | None = None,
) -> GbifEnrichmentResult:
    """Resolve manual and optional API GBIF download metadata."""

    explicit_key = normalize_download_key(options.download_key)
    if options.download_key and explicit_key is None:
        raise ValueError(f"Invalid GBIF download key: {options.download_key!r}")
    explicit_doi = normalize_doi(options.doi)
    if options.doi and explicit_doi is None:
        raise ValueError(f"Invalid GBIF DOI: {options.doi!r}")

    download_key = explicit_key or inferred_download_key
    metadata = GbifDownloadMetadata(
        download_key=download_key,
        doi=explicit_doi,
        citation=_clean_text(options.citation),
    )
    warnings: list[dict[str, Any]] = []

    if options.enrich:
        if not download_key:
            warnings.append(_warning("gbif_download_key_unavailable", None))
        else:
            api_metadata = GbifDownloadMetadata(download_key=download_key)
            citation_metadata = GbifDownloadMetadata(download_key=download_key)
            try:
                api_client = client or GbifDownloadClient(
                    api_base_url=options.api_base_url,
                    connect_timeout_seconds=options.connect_timeout_seconds,
                    read_timeout_seconds=options.read_timeout_seconds,
                    max_retries=options.max_retries,
                    user_agent=options.user_agent,
                )
                try:
                    api_metadata = metadata_from_api_payload(
                        api_client.fetch_download_metadata(download_key),
                        download_key=download_key,
                    )
                except GbifDownloadMetadataError:
                    api_metadata = GbifDownloadMetadata(download_key=download_key)
                if not (metadata.doi and metadata.citation):
                    citation_metadata = metadata_from_citation_text(
                        api_client.fetch_download_citation(download_key),
                        download_key=download_key,
                        license=api_metadata.license,
                    )
                metadata = GbifDownloadMetadata(
                    download_key=download_key,
                    doi=metadata.doi or citation_metadata.doi or api_metadata.doi,
                    citation=(
                        metadata.citation
                        or citation_metadata.citation
                        or api_metadata.citation
                    ),
                    license=api_metadata.license or citation_metadata.license,
                )
            except GbifDownloadMetadataError as exc:
                warnings.append(_warning("gbif_download_metadata_lookup_failed", str(exc)))

    return GbifEnrichmentResult(metadata=metadata, warnings=tuple(warnings))


def _warning(code: str, message: str | None) -> dict[str, Any]:
    return {
        "code": code,
        "stage": "gbif_download_metadata",
        "message": message or "GBIF download metadata enrichment could not run.",
        "field": None,
    }


def _retry_after_seconds(exc: HTTPError) -> float | None:
    retry_after = exc.headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _element_text(element: ET.Element) -> str | None:
    text = " ".join(part.strip() for part in element.itertext() if part.strip())
    return text or None


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
