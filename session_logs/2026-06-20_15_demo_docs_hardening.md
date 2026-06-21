# Prompt 15: Demo, Documentation And MVP Hardening

## Final Files Updated

- `README.md`: linked the new deployment/static demo guide.
- `docs/developer_setup.md`: linked deployment review steps from CLI help/setup.
- `docs/converter.md`: linked deployment review steps from output bundle docs.
- `docs/development_plan.md`: updated immediate next actions after MVP hardening.
- `docs/deployment.md`: created the accepted static hosting and demo review guide.
- `tests/test_viewer_contract.py`: added a regression check for deployment/static MVP boundaries.
- `session_logs/2026-06-20_15_demo_docs_hardening.md`: recorded this evidence.

## End-To-End Demo Commands And Results

Verification used the documented in-repository `.venv/` workflow with explicit
`${REPO}/.venv/bin/...` commands.

Environment checks:

```text
.venv/bin/python --version -> Python 3.13.2
.venv/bin/dwca-cloud-geospatial --help -> inspect, convert and validate commands available
```

Writer and validation stack:

```text
pyogrio 0.12.1
gdal 3.11.4
pyarrow 24.0.0
GPKG rw
FlatGeobuf rw
ogr2ogr None
duckdb 1.5.1
geoparquet-io 1.3.0
pyproj 3.7.0
```

Default FlatGeobuf conversion:

```bash
.venv/bin/dwca-cloud-geospatial convert \
  tests/fixtures/dwca/minimal_occurrence/normalization \
  scratch/prompt15-flatgeobuf \
  --overwrite
```

Result:

```text
Formats: flatgeobuf
Accepted records: 2
Rejected records: 5
Manifest: scratch/prompt15-flatgeobuf/manifest.json
Viewer: scratch/prompt15-flatgeobuf/index.html
```

Generated files:

```text
index.html
styles.css
README.md
app.js
manifest.json
data/occurrences.fgb
data/occurrences.gpkg
metadata/source.json
metadata/processing.json
reports/rejected_records.csv
```

Validation:

```text
.venv/bin/dwca-cloud-geospatial validate scratch/prompt15-flatgeobuf
Status: passed
Errors: 0
Warnings: 0
Checks: 14
```

Explicit GeoParquet-only conversion:

```bash
.venv/bin/dwca-cloud-geospatial convert \
  tests/fixtures/dwca/minimal_occurrence/normalization \
  scratch/prompt15-geoparquet-only \
  --format geoparquet \
  --overwrite
```

Result:

```text
Formats: geoparquet
Accepted records: 2
Rejected records: 5
Manifest: scratch/prompt15-geoparquet-only/manifest.json
Viewer: scratch/prompt15-geoparquet-only/index.html
```

Generated files:

```text
index.html
styles.css
README.md
app.js
manifest.json
data/occurrences.parquet
metadata/source.json
metadata/processing.json
reports/rejected_records.csv
```

Validation:

```text
.venv/bin/dwca-cloud-geospatial validate scratch/prompt15-geoparquet-only
Status: passed_with_warnings
Errors: 0
Warnings: 1
Checks: 15
```

The warning was the accepted optional Pyogrio/GDAL GeoParquet reader skip:
the local GDAL stack does not recognize Parquet/GeoParquet as a supported
vector read format. Required PyArrow validation passed.

## Checklist Archive Evidence

The three local checklist archives inspect successfully as valid `Taxon` core
DwC-A archives with no parser diagnostics:

```bash
.venv/bin/dwca-cloud-geospatial inspect --json \
  examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip
.venv/bin/dwca-cloud-geospatial inspect --json \
  examples/dwca/dwca-appendixiibernconventionua-v1.2.zip
.venv/bin/dwca-cloud-geospatial inspect --json \
  examples/dwca/dwca-kharkivredliastua-v1.0.zip
```

Observed for all three:

```text
archive_kind: zip
diagnostics: []
core.row_type: http://rs.tdwg.org/dwc/terms/Taxon
core.files: ["taxon.txt"]
metadata_file: eml.xml
```

Negative conversion examples:

```bash
.venv/bin/dwca-cloud-geospatial convert \
  examples/dwca/dwca-reddatabookofukraine_plants-fungi-algae_checklist-v1.1.zip \
  scratch/prompt15-checklist-negative \
  --overwrite
.venv/bin/dwca-cloud-geospatial convert \
  examples/dwca/dwca-appendixiibernconventionua-v1.2.zip \
  scratch/prompt15-checklist-negative-2 \
  --overwrite
.venv/bin/dwca-cloud-geospatial convert \
  examples/dwca/dwca-kharkivredliastua-v1.0.zip \
  scratch/prompt15-checklist-negative-3 \
  --overwrite
```

Each command exited non-zero with:

```text
Conversion failed: Input archive is not an occurrence DwC-A archive: DwC-A metadata does not declare an Occurrence core; non-occurrence core files will not be read as occurrence rows.
missing_occurrence_core
```

## Test And Validation Evidence

Focused hardening suite:

```text
.venv/bin/python -m pytest tests/test_occurrence_parser.py tests/test_occurrence_normalization.py tests/test_flatgeobuf_writer.py tests/test_geoparquet_writer.py tests/test_bundle_validation.py tests/test_conversion.py tests/test_static_viewer.py tests/test_gui.py tests/test_cli.py tests/test_gbif.py -q
83 passed, 1 skipped in 2.23s
```

Full suite:

```text
.venv/bin/python -m pytest tests -q
97 passed, 1 skipped in 3.09s
```

The skip is dependency-dependent and accepted for the local GDAL GeoParquet
reader path.

PyArrow printed sandboxed `sysctlbyname` CPU-feature warnings during commands
that import Arrow. The commands still completed successfully.

## Known Remaining Limitations

- Checklist/Taxon DwC-A archives can be inspected but are not MVP geospatial
  conversion inputs.
- Occurrence geospatial conversion requires an Occurrence core with usable
  coordinate terms.
- Multi-file occurrence-core streaming remains deferred.
- GeoParquet large-output mode is single-file only; partitioned GeoParquet is
  rejected until manifest and validator contracts support it.
- GeoParquet-only bundles, including large-output bundles, are valid but have
  no MVP browser map layer.
- PMTiles is deferred to MVP+.
- FlatGeobuf conversion uses chunked GeoPackage staging, but GDAL may still
  need substantial memory while building the final FlatGeobuf spatial index.
- The GUI supports status copy through the context menu and `Copy Text`;
  `Ctrl+C` / `Cmd+C` remains an accepted Tk/macOS MVP limitation.
- Fully offline viewer hosting must mirror CDN JavaScript/CSS assets and the
  basemap or update the viewer files.

## Suggested Next MVP+ Prompts Or ADRs

- Prompt 16: PMTiles generation and viewer layer contract.
- Prompt 17: Partitioned GeoParquet manifest and validation contract.
- Prompt 18: Multi-file occurrence-core streaming implementation.
- Prompt 19: Offline viewer asset packaging and static-hosting profile.
- ADR: Large FlatGeobuf no-spatial-index option and user-facing tradeoffs.

## Prompt Updates

None
