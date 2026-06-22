# Demo Dataset

Source download page:
https://www.gbif.org/occurrence/download/0038004-260519110011954

Download URL:
https://api.gbif.org/v1/occurrence/download/request/0038004-260519110011954.zip

Download the source archive locally:

```bash
mkdir -p demo/source
curl -L \
  "https://api.gbif.org/v1/occurrence/download/request/0038004-260519110011954.zip" \
  -o demo/source/0038004-260519110011954.zip
```

Citation:
GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b

License:
CC BY-NC 4.0

Notes:
The GBIF occurrence download page is the authoritative license source for this
demo archive. The dataset license applies to the source archive and derived
demo outputs.
The project code remains licensed separately under AGPL-3.0-only.
When redistributing generated demo bundles, preserve the DOI, citation,
license and source download link.

For reproducible demo bundle generation, pass the source license explicitly:

```bash
dwca-cloud-geospatial convert \
  demo/source/0038004-260519110011954.zip \
  demo/output \
  --gbif-download-key 0038004-260519110011954 \
  --gbif-doi 10.15468/dl.3xbk5b \
  --gbif-citation "GBIF.org (4 June 2026) GBIF Occurrence Download https://doi.org/10.15468/dl.3xbk5b" \
  --gbif-license CC_BY_NC_4_0 \
  --gbif-enrich \
  --format flatgeobuf \
  --format geoparquet \
  --overwrite
```
