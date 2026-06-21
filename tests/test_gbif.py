from __future__ import annotations

from dwca_cloud_geospatial.gbif import (
    GbifDownloadMetadata,
    GbifDownloadOptions,
    doi_url,
    extract_download_key_from_eml_xml,
    extract_download_key_from_text,
    format_gbif_download_citation,
    infer_download_key_from_path_name,
    metadata_from_api_payload,
    metadata_from_citation_text,
    normalize_citation_text,
    normalize_doi,
    resolve_gbif_download_metadata,
)


def test_extracts_gbif_download_key_from_eml_additional_metadata() -> None:
    xml = """
    <eml>
      <additionalMetadata>
        <metadata>
          <gbif>
            <citation identifier="0038004-260519110011954">
              GBIF Occurrence Download
            </citation>
          </gbif>
        </metadata>
      </additionalMetadata>
    </eml>
    """

    assert extract_download_key_from_eml_xml(xml) == "0038004-260519110011954"


def test_extracts_gbif_download_key_from_download_urls_and_exact_names() -> None:
    assert (
        extract_download_key_from_text(
            "https://api.gbif.org/v1/occurrence/download/request/"
            "0038004-260519110011954.zip"
        )
        == "0038004-260519110011954"
    )
    assert (
        infer_download_key_from_path_name("0038004-260519110011954.zip")
        == "0038004-260519110011954"
    )
    assert infer_download_key_from_path_name("prefix-0038004-260519110011954.zip") is None


def test_normalizes_doi_values() -> None:
    assert normalize_doi("10.15468/dl.3xbk5b") == "10.15468/dl.3xbk5b"
    assert (
        normalize_doi("https://doi.org/10.15468/dl.3xbk5b")
        == "10.15468/dl.3xbk5b"
    )
    assert doi_url("10.15468/dl.3xbk5b") == "https://doi.org/10.15468/dl.3xbk5b"
    assert normalize_doi(None) is None
    assert normalize_doi("not a doi") is None
    assert (
        normalize_doi(
            "GBIF.org (10 June 2026) GBIF Occurrence Download "
            "https: //doi.org/10.15468/dl.9t5b2m"
        )
        == "10.15468/dl.9t5b2m"
    )


def test_normalizes_citation_endpoint_text_and_extracts_doi() -> None:
    citation = (
        "GBIF.org (10 June 2026) GBIF Occurrence Download "
        "https: //doi.org/10.15468/dl.9t5b2m"
    )

    assert normalize_citation_text(citation) == (
        "GBIF.org (10 June 2026) GBIF Occurrence Download "
        "https://doi.org/10.15468/dl.9t5b2m"
    )
    assert metadata_from_citation_text(
        citation,
        download_key="0049663-260519110011954",
    ) == GbifDownloadMetadata(
        download_key="0049663-260519110011954",
        doi="10.15468/dl.9t5b2m",
        citation=(
            "GBIF.org (10 June 2026) GBIF Occurrence Download "
            "https://doi.org/10.15468/dl.9t5b2m"
        ),
        license=None,
    )


def test_formats_gbif_download_citation_from_api_like_metadata() -> None:
    citation = format_gbif_download_citation(
        {
            "doi": "10.15468/dl.3xbk5b",
            "created": "2026-06-04T19:32:00.000+00:00",
        }
    )

    assert citation == (
        "GBIF.org (4 June 2026) GBIF Occurrence Download "
        "https://doi.org/10.15468/dl.3xbk5b"
    )


def test_metadata_from_api_payload_normalizes_download_metadata() -> None:
    metadata = metadata_from_api_payload(
        {
            "key": "0038004-260519110011954",
            "doi": "https://doi.org/10.15468/dl.3xbk5b",
            "created": "2026-06-04",
            "license": "https://creativecommons.org/licenses/by/4.0/legalcode",
        }
    )

    assert metadata == GbifDownloadMetadata(
        download_key="0038004-260519110011954",
        doi="10.15468/dl.3xbk5b",
        citation=(
            "GBIF.org (4 June 2026) GBIF Occurrence Download "
            "https://doi.org/10.15468/dl.3xbk5b"
        ),
        license="https://creativecommons.org/licenses/by/4.0/legalcode",
    )


def test_resolve_gbif_download_metadata_uses_manual_values_without_network() -> None:
    result = resolve_gbif_download_metadata(
        options=GbifDownloadOptions(
            download_key="0038004-260519110011954",
            doi="https://doi.org/10.15468/dl.3xbk5b",
            citation=(
                "GBIF.org (4 June 2026) GBIF Occurrence Download "
                "https://doi.org/10.15468/dl.3xbk5b"
            ),
            license="CC_BY_NC_4_0",
        )
    )

    assert result.metadata.download_key == "0038004-260519110011954"
    assert result.metadata.doi == "10.15468/dl.3xbk5b"
    assert result.metadata.license == "CC_BY_NC_4_0"
    assert result.warnings == ()


def test_resolve_gbif_download_metadata_warns_when_enrichment_lacks_key() -> None:
    result = resolve_gbif_download_metadata(options=GbifDownloadOptions(enrich=True))

    assert result.metadata == GbifDownloadMetadata()
    assert result.warnings[0]["code"] == "gbif_download_key_unavailable"


def test_resolve_gbif_download_metadata_uses_mocked_api_client() -> None:
    class FakeClient:
        def fetch_download_metadata(self, download_key: str):
            assert download_key == "0038004-260519110011954"
            return {
                "key": download_key,
                "created": "2026-06-04",
            }

        def fetch_download_citation(self, download_key: str) -> str:
            assert download_key == "0038004-260519110011954"
            return (
                "GBIF.org (4 June 2026) GBIF Occurrence Download "
                "https://doi.org/10.15468/dl.3xbk5b"
            )

    result = resolve_gbif_download_metadata(
        options=GbifDownloadOptions(enrich=True),
        inferred_download_key="0038004-260519110011954",
        client=FakeClient(),
    )

    assert result.metadata.doi == "10.15468/dl.3xbk5b"
    assert result.metadata.citation == (
        "GBIF.org (4 June 2026) GBIF Occurrence Download "
        "https://doi.org/10.15468/dl.3xbk5b"
    )
    assert result.warnings == ()
