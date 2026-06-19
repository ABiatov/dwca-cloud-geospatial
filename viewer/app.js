(function () {
  "use strict";

  const SUPPORTED_BUNDLE_SCHEMA_VERSION = "0.1.0";
  const SUPPORTED_VIEWER_CONTRACT_VERSION = "0.1.0";
  const SOURCE_METADATA_PATH = "metadata/source.json";
  const PROCESSING_METADATA_PATH = "metadata/processing.json";
  const NO_MAP_LAYER_MESSAGE =
    "No FlatGeobuf map layer is available for this bundle.";
  const KINGDOM_COLOR_EXPRESSION = [
    "match",
    ["coalesce", ["get", "kingdom"], ""],
    "Animalia",
    "#d81b60",
    "Plantae",
    "#1b9e77",
    "Fungi",
    "#8c510a",
    "Bacteria",
    "#7570b3",
    "Archaea",
    "#e6ab02",
    "Chromista",
    "#1f78b4",
    "Protozoa",
    "#6a3d9a",
    "Viruses",
    "#e6550d",
    "#111827",
  ];

  const state = {
    manifest: null,
    sourceMetadata: null,
    processingMetadata: null,
    bundleRoot: null,
    map: null,
    allFeatures: [],
    filteredFeatures: [],
    selectedFeatureId: null,
    filters: {
      scientific_name: "",
      categories: {},
      year_min: "",
      year_max: "",
      quality_mode: "all",
      quality_tokens: new Set(),
    },
  };

  const knownDetailFields = [
    "scientific_name",
    "verbatim_scientific_name",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "taxon_rank",
    "iucn_red_list_category",
    "event_date",
    "event_year",
    "basis_of_record",
    "degree_of_establishment",
    "decimal_longitude",
    "decimal_latitude",
    "coordinate_uncertainty_in_meters",
    "country_code",
    "locality",
    "identified_by",
    "dataset_name",
    "license",
    "references",
    "rights_holder",
    "source_record_id",
    "source_file",
    "source_row_number",
    "source_data_row_number",
    "quality_flags",
    "has_quality_flags",
  ];

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(message, isError) {
    const node = byId("bundle-status");
    node.textContent = message;
    node.classList.toggle("error", Boolean(isError));
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === "") {
      return "Unknown";
    }
    if (typeof value === "boolean") {
      return value ? "yes" : "no";
    }
    if (Array.isArray(value)) {
      return value.length ? value.join(", ") : "Unknown";
    }
    if (typeof value === "object") {
      return JSON.stringify(value);
    }
    return String(value);
  }

  function addDefinition(list, label, value) {
    if (value === null || value === undefined || value === "") {
      return;
    }
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = displayValue(value);
    list.append(term, description);
  }

  function addLinkDefinition(list, label, href, text) {
    if (!href) {
      return;
    }
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    const link = document.createElement("a");
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = text || href;
    description.append(link);
    list.append(term, description);
  }

  function safeRelativePath(path) {
    if (typeof path !== "string" || path.length === 0) {
      return false;
    }
    if (path.startsWith("/") || path.includes("\\") || /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(path)) {
      return false;
    }
    const parts = path.split("/");
    return parts.every((part) => part && part !== "." && part !== "..");
  }

  function urlForBundlePath(path) {
    if (!safeRelativePath(path)) {
      throw new Error(`Unsafe bundle-relative path: ${path}`);
    }
    return new URL(path, state.bundleRoot);
  }

  function manifestUrlFromLocation() {
    const params = new URLSearchParams(window.location.search);
    const explicitManifest = params.get("manifest");
    if (explicitManifest) {
      return new URL(explicitManifest, window.location.href);
    }
    const bundle = params.get("bundle");
    if (bundle) {
      const bundleUrl = new URL(bundle, window.location.href);
      if (!bundleUrl.pathname.endsWith("/")) {
        bundleUrl.pathname += "/";
      }
      return new URL("manifest.json", bundleUrl);
    }
    return new URL("manifest.json", window.location.href);
  }

  async function fetchJson(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Could not load ${url}: HTTP ${response.status}`);
    }
    return response.json();
  }

  function requireSupportedVersions(manifest) {
    if (manifest.bundle_schema_version !== SUPPORTED_BUNDLE_SCHEMA_VERSION) {
      throw new Error(
        `Unsupported bundle schema version: ${manifest.bundle_schema_version || "missing"}`
      );
    }
    if (manifest.viewer_contract_version !== SUPPORTED_VIEWER_CONTRACT_VERSION) {
      throw new Error(
        `Unsupported viewer contract version: ${manifest.viewer_contract_version || "missing"}`
      );
    }
  }

  function fileEntry(path) {
    return (state.manifest.files || []).find((entry) => entry.path === path);
  }

  function requireMetadataFile(path) {
    const entry = fileEntry(path);
    if (!entry) {
      throw new Error(`Required metadata file is missing from manifest.files: ${path}`);
    }
    return entry;
  }

  function findUsableFlatGeobufLayer() {
    const files = new Set((state.manifest.files || []).map((entry) => entry.path));
    const layers = state.manifest.layers || [];
    const defaultLayerId = state.manifest.viewer && state.manifest.viewer.default_layer;
    const defaultLayer = layers.find((layer) => layer.id === defaultLayerId);
    const isUsable = (layer) =>
      layer &&
      layer.type === "point" &&
      layer.source_format === "flatgeobuf" &&
      safeRelativePath(layer.path) &&
      files.has(layer.path);
    if (isUsable(defaultLayer)) {
      return { layer: defaultLayer, warning: null };
    }
    const fallback = layers.find(isUsable);
    return {
      layer: fallback || null,
      warning: fallback
        ? "Default layer was not a usable FlatGeobuf point layer; using the first usable FlatGeobuf layer."
        : null,
    };
  }

  function qualityFlagTokens(value) {
    if (value === null || value === undefined || value === "") {
      return [];
    }
    return String(value)
      .split("|")
      .map((token) => token.trim())
      .filter((token) => token.length > 0);
  }

  function hasQualityFlags(properties) {
    if (typeof properties.has_quality_flags === "boolean") {
      return properties.has_quality_flags;
    }
    return qualityFlagTokens(properties.quality_flags).length > 0;
  }

  function featureHasField(feature, field) {
    return Object.prototype.hasOwnProperty.call(feature.properties || {}, field);
  }

  function fieldValues(field) {
    const values = new Set();
    for (const feature of state.allFeatures) {
      const value = feature.properties && feature.properties[field];
      if (value !== null && value !== undefined && value !== "") {
        values.add(String(value));
      }
    }
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }

  function updateCounts() {
    const counts = state.manifest.counts || {};
    const list = byId("counts-list");
    list.replaceChildren();
    const entries = [
      ["Source", counts.source_records],
      ["Accepted", counts.accepted_records],
      ["Rejected", counts.rejected_records],
      ["Visible", state.filteredFeatures.length || 0],
    ];
    for (const [label, value] of entries) {
      const wrapper = document.createElement("div");
      const term = document.createElement("dt");
      term.textContent = label;
      const description = document.createElement("dd");
      description.textContent = displayValue(value);
      wrapper.append(term, description);
      list.append(wrapper);
    }
  }

  function provenanceRows() {
    const source = state.sourceMetadata || {};
    const manifestSource = state.manifest.source || {};
    const processing = state.processingMetadata || {};
    const dataset = source.dataset || {};
    const rights = source.rights || {};
    const gbif = source.gbif || {};
    const obis = source.obis || {};
    const archive = source.source_archive || {};
    return [
      ["Dataset title", dataset.title || state.manifest.title || manifestSource.title],
      ["Description", dataset.description],
      ["Publisher", dataset.publisher || manifestSource.publisher],
      ["Homepage", dataset.homepage],
      ["DOI", dataset.doi || gbif.doi || obis.doi || manifestSource.doi],
      ["Citation", dataset.citation || gbif.citation || obis.citation || manifestSource.citation],
      ["License", rights.license || gbif.license || obis.license || manifestSource.license],
      ["Rights holder", rights.rights_holder],
      ["Source archive", [archive.name, archive.kind, archive.bytes].filter(Boolean).join(" | ")],
      ["Archive SHA-256", archive.sha256],
      ["GBIF dataset key", gbif.dataset_key || manifestSource.gbif_dataset_key],
      ["GBIF download key", gbif.download_key || manifestSource.gbif_download_key],
      ["OBIS dataset id", obis.dataset_id || manifestSource.obis_dataset_id],
      ["Generated", state.manifest.created_at || processing.created_at],
      [
        "Converter",
        [
          state.manifest.generator && state.manifest.generator.name,
          state.manifest.generator && state.manifest.generator.version,
        ]
          .filter(Boolean)
          .join(" "),
      ],
      ["Validation", processing.validation && processing.validation.status],
    ];
  }

  function renderProvenance() {
    const list = byId("provenance-list");
    list.replaceChildren();
    for (const [label, value] of provenanceRows()) {
      addDefinition(list, label, value);
    }
  }

  function artifactDescription(entry) {
    if (entry.role === "geopackage") {
      return "Retained GeoPackage staging/source artifact; not loaded as the MVP browser map layer.";
    }
    if (entry.role === "geoparquet") {
      return "Analytical GeoParquet artifact; browser loading is not part of the MVP viewer contract.";
    }
    if (entry.role === "flatgeobuf") {
      return "MVP browser point layer when declared in manifest.layers.";
    }
    if (entry.role === "report") {
      return "Rejected-record report.";
    }
    return entry.media_type || "Generated file.";
  }

  function renderArtifacts() {
    const container = byId("artifact-list");
    container.replaceChildren();
    for (const entry of state.manifest.files || []) {
      const item = document.createElement("article");
      item.className = "artifact";
      const link = document.createElement("a");
      link.href = urlForBundlePath(entry.path).href;
      link.textContent = entry.path;
      const description = document.createElement("p");
      description.textContent = [
        entry.role,
        `${displayValue(entry.record_count)} records`,
        entry.bytes ? `${entry.bytes} bytes` : null,
        artifactDescription(entry),
      ]
        .filter(Boolean)
        .join(" | ");
      item.append(link, description);
      container.append(item);
    }
  }

  function renderProcessing() {
    const container = byId("processing-summary");
    container.replaceChildren();
    const processing = state.processingMetadata || {};
    const configuration = processing.configuration || {};
    const counts = processing.counts || {};

    const countsBox = document.createElement("div");
    countsBox.className = "notice";
    countsBox.textContent = `Processing counts: source ${displayValue(
      counts.source_records
    )}, accepted ${displayValue(counts.accepted_records)}, rejected ${displayValue(
      counts.rejected_records
    )}.`;
    container.append(countsBox);

    const geoparquet = configuration.geoparquet;
    if (geoparquet) {
      const gpqBox = document.createElement("div");
      gpqBox.className = "notice";
      gpqBox.textContent = `GeoParquet: large_output_mode=${displayValue(
        geoparquet.large_output_mode
      )}, covering_bbox=${displayValue(
        geoparquet.covering_bbox_column && geoparquet.covering_bbox_column.enabled
      )}, spatial_sort=${displayValue(
        geoparquet.spatial_sorting && geoparquet.spatial_sorting.enabled
      )}, strategy=${displayValue(
        geoparquet.spatial_sorting && geoparquet.spatial_sorting.strategy
      )}, partitioned=${displayValue(
        geoparquet.partitioned_dataset && geoparquet.partitioned_dataset.enabled
      )}.`;
      container.append(gpqBox);
    }

    for (const warning of processing.warnings || []) {
      const box = document.createElement("div");
      box.className = "warning";
      if (warning.code === "large_indexed_flatgeobuf_write") {
        box.textContent = `FlatGeobuf generation warning: ${warning.code}; stage=${displayValue(
          warning.stage
        )}; feature_count=${displayValue(
          warning.feature_count
        )}; estimated_spatial_index_bytes=${displayValue(
          warning.estimated_spatial_index_bytes
        )}.`;
      } else {
        box.textContent = `Processing warning: ${displayValue(warning.code)} ${displayValue(
          warning.message
        )}`;
      }
      container.append(box);
    }
  }

  function renderMetadata() {
    const title =
      (state.sourceMetadata.dataset && state.sourceMetadata.dataset.title) ||
      state.manifest.title ||
      (state.manifest.source && state.manifest.source.title) ||
      "DwC-A output bundle";
    byId("dataset-title").textContent = title;
    renderProvenance();
    renderArtifacts();
    renderProcessing();
    updateCounts();
  }

  function setNoMapState(message) {
    const empty = byId("map-empty-state");
    empty.hidden = false;
    empty.textContent = message;
    byId("feature-count").textContent = "No FlatGeobuf features loaded";
  }

  async function loadFlatGeobufFeatures(url) {
    if (!window.flatgeobuf || typeof window.flatgeobuf.deserialize !== "function") {
      throw new Error("FlatGeobuf browser library is not available.");
    }
    const features = [];
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Could not load FlatGeobuf layer: HTTP ${response.status}`);
    }
    const bytes = new Uint8Array(await response.arrayBuffer());
    const iterable = window.flatgeobuf.deserialize(bytes);
    for await (const feature of iterable) {
      const copy = {
        type: "Feature",
        geometry: feature.geometry,
        properties: { ...(feature.properties || {}) },
      };
      copy.properties._viewerId = features.length;
      features.push(copy);
    }
    return features;
  }

  function featureCollection(features) {
    return { type: "FeatureCollection", features };
  }

  function mapStyle() {
    return {
      version: 8,
      sources: {
        osm: {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          maxzoom: 19,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        },
      },
      layers: [
        {
          id: "background",
          type: "background",
          paint: { "background-color": "#dce8e3" },
        },
        {
          id: "osm-basemap",
          type: "raster",
          source: "osm",
          paint: { "raster-opacity": 0.92 },
        },
      ],
    };
  }

  function initMap(layer) {
    if (!window.maplibregl) {
      setNoMapState("MapLibre is not available. Metadata and records remain available.");
      return null;
    }
    const bounds = layer.bounds || (state.manifest.viewer && state.manifest.viewer.initial_bounds);
    const map = new window.maplibregl.Map({
      container: "map",
      style: mapStyle(),
      center: [0, 20],
      zoom: 1,
    });
    map.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      map.addSource("occurrences", {
        type: "geojson",
        data: featureCollection(state.filteredFeatures),
      });
      map.addLayer({
        id: "occurrence-points",
        type: "circle",
        source: "occurrences",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 3, 8, 7],
          "circle-color": KINGDOM_COLOR_EXPRESSION,
          "circle-opacity": 0.84,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#ffffff",
        },
      });
      map.addLayer({
        id: "occurrence-selected",
        type: "circle",
        source: "occurrences",
        filter: ["==", ["get", "_viewerId"], -1],
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 8, 8, 14],
          "circle-color": "rgba(255, 255, 255, 0)",
          "circle-stroke-width": 4,
          "circle-stroke-color": "#111827",
          "circle-opacity": 1,
        },
      });
      updateSelectedFeatureLayer();
      map.on("click", "occurrence-points", (event) => {
        const feature = event.features && event.features[0];
        if (feature && feature.properties) {
          selectFeature(Number(feature.properties._viewerId));
        }
      });
      if (bounds && bounds.length === 4) {
        map.fitBounds(
          [
            [bounds[0], bounds[1]],
            [bounds[2], bounds[3]],
          ],
          { padding: 48, duration: 0, maxZoom: 8 }
        );
      }
    });
    return map;
  }

  function updateMapData() {
    if (!state.map || !state.map.getSource || !state.map.getSource("occurrences")) {
      return;
    }
    state.map.getSource("occurrences").setData(featureCollection(state.filteredFeatures));
    updateSelectedFeatureLayer();
  }

  function updateSelectedFeatureLayer() {
    if (!state.map || !state.map.setFilter || !state.map.getLayer("occurrence-selected")) {
      return;
    }
    const selectedId = Number.isFinite(Number(state.selectedFeatureId))
      ? Number(state.selectedFeatureId)
      : -1;
    state.map.setFilter("occurrence-selected", ["==", ["get", "_viewerId"], selectedId]);
  }

  function renderFilters() {
    const container = byId("filters");
    container.replaceChildren();
    const declared = (state.manifest.viewer && state.manifest.viewer.filter_fields) || [];
    const available = declared.filter((field) =>
      state.allFeatures.some((feature) => featureHasField(feature, field))
    );
    if (!available.length) {
      const notice = document.createElement("p");
      notice.className = "status-line";
      notice.textContent = state.allFeatures.length
        ? "No declared filter fields are present on the loaded layer."
        : "Filters are available after a FlatGeobuf layer is loaded.";
      container.append(notice);
      return;
    }

    if (available.includes("scientific_name")) {
      const group = createFilterGroup("Scientific name");
      const input = document.createElement("input");
      input.type = "search";
      input.placeholder = "Contains";
      input.value = state.filters.scientific_name;
      input.addEventListener("input", () => {
        state.filters.scientific_name = input.value;
        applyFilters();
      });
      group.append(input);
      container.append(group);
    }

    for (const field of ["kingdom", "basis_of_record", "iucn_red_list_category"]) {
      if (available.includes(field)) {
        container.append(createCategoricalFilter(field));
      }
    }

    if (available.includes("event_year")) {
      const group = createFilterGroup("Event year");
      const min = document.createElement("input");
      const max = document.createElement("input");
      min.type = "number";
      max.type = "number";
      min.placeholder = "From";
      max.placeholder = "To";
      min.value = state.filters.year_min;
      max.value = state.filters.year_max;
      min.addEventListener("input", () => {
        state.filters.year_min = min.value;
        applyFilters();
      });
      max.addEventListener("input", () => {
        state.filters.year_max = max.value;
        applyFilters();
      });
      group.append(min, max);
      container.append(group);
    }

    if (available.includes("quality_flags")) {
      container.append(createQualityFilter());
    }
  }

  function createFilterGroup(labelText) {
    const group = document.createElement("div");
    group.className = "filter-group";
    const label = document.createElement("label");
    label.textContent = labelText;
    group.append(label);
    return group;
  }

  function createCategoricalFilter(field) {
    const group = createFilterGroup(field.replaceAll("_", " "));
    const stack = document.createElement("div");
    stack.className = "checkbox-stack";
    state.filters.categories[field] = state.filters.categories[field] || new Set();
    for (const value of fieldValues(field)) {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = state.filters.categories[field].has(value);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          state.filters.categories[field].add(value);
        } else {
          state.filters.categories[field].delete(value);
        }
        applyFilters();
      });
      label.append(checkbox, document.createTextNode(value));
      stack.append(label);
    }
    group.append(stack);
    return group;
  }

  function createQualityFilter() {
    const group = createFilterGroup("Quality flags");
    const mode = document.createElement("select");
    for (const [value, label] of [
      ["all", "All records"],
      ["flagged", "Flagged only"],
      ["unflagged", "Unflagged only"],
    ]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      mode.append(option);
    }
    mode.value = state.filters.quality_mode;
    mode.addEventListener("change", () => {
      state.filters.quality_mode = mode.value;
      applyFilters();
    });
    group.append(mode);

    const tokens = new Set();
    for (const feature of state.allFeatures) {
      for (const token of qualityFlagTokens(feature.properties && feature.properties.quality_flags)) {
        tokens.add(token);
      }
    }
    if (tokens.size) {
      const stack = document.createElement("div");
      stack.className = "checkbox-stack";
      for (const token of Array.from(tokens).sort()) {
        const label = document.createElement("label");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = state.filters.quality_tokens.has(token);
        checkbox.addEventListener("change", () => {
          if (checkbox.checked) {
            state.filters.quality_tokens.add(token);
          } else {
            state.filters.quality_tokens.delete(token);
          }
          applyFilters();
        });
        label.append(checkbox, document.createTextNode(token));
        stack.append(label);
      }
      group.append(stack);
    }
    return group;
  }

  function matchesFilters(feature) {
    const properties = feature.properties || {};
    const search = state.filters.scientific_name.trim().toLowerCase();
    if (search) {
      const value = String(properties.scientific_name || "").toLowerCase();
      if (!value.includes(search)) {
        return false;
      }
    }
    for (const [field, selected] of Object.entries(state.filters.categories)) {
      if (selected.size && !selected.has(String(properties[field] || ""))) {
        return false;
      }
    }
    const yearMin = Number.parseInt(state.filters.year_min, 10);
    const yearMax = Number.parseInt(state.filters.year_max, 10);
    if (!Number.isNaN(yearMin) || !Number.isNaN(yearMax)) {
      const year = Number.parseInt(properties.event_year, 10);
      if (Number.isNaN(year)) {
        return false;
      }
      if (!Number.isNaN(yearMin) && year < yearMin) {
        return false;
      }
      if (!Number.isNaN(yearMax) && year > yearMax) {
        return false;
      }
    }
    const flagged = hasQualityFlags(properties);
    if (state.filters.quality_mode === "flagged" && !flagged) {
      return false;
    }
    if (state.filters.quality_mode === "unflagged" && flagged) {
      return false;
    }
    if (state.filters.quality_tokens.size) {
      const tokens = qualityFlagTokens(properties.quality_flags);
      for (const selectedToken of state.filters.quality_tokens) {
        if (!tokens.includes(selectedToken)) {
          return false;
        }
      }
    }
    return true;
  }

  function applyFilters() {
    state.filteredFeatures = state.allFeatures.filter(matchesFilters);
    if (!state.filteredFeatures.some((feature) => feature.properties._viewerId === state.selectedFeatureId)) {
      state.selectedFeatureId = state.filteredFeatures[0]
        ? state.filteredFeatures[0].properties._viewerId
        : null;
    }
    updateCounts();
    updateMapData();
    renderRecordList();
    renderFeatureDetails();
    byId("feature-count").textContent = `${state.filteredFeatures.length} of ${state.allFeatures.length} records visible`;
  }

  function resetFilters() {
    state.filters.scientific_name = "";
    state.filters.categories = {};
    state.filters.year_min = "";
    state.filters.year_max = "";
    state.filters.quality_mode = "all";
    state.filters.quality_tokens = new Set();
    renderFilters();
    applyFilters();
  }

  function renderRecordList() {
    const list = byId("record-list");
    list.replaceChildren();
    const visible = state.filteredFeatures.slice(0, 250);
    for (const feature of visible) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      const properties = feature.properties || {};
      button.type = "button";
      button.textContent = properties.scientific_name || properties.source_record_id || `Record ${properties._viewerId}`;
      button.setAttribute("aria-current", properties._viewerId === state.selectedFeatureId ? "true" : "false");
      button.addEventListener("click", () => selectFeature(properties._viewerId));
      item.append(button);
      list.append(item);
    }
  }

  function selectFeature(id) {
    state.selectedFeatureId = id;
    updateSelectedFeatureLayer();
    renderRecordList();
    renderFeatureDetails();
  }

  function renderFeatureDetails() {
    const list = byId("feature-details");
    list.replaceChildren();
    const feature = state.allFeatures.find(
      (candidate) => candidate.properties && candidate.properties._viewerId === state.selectedFeatureId
    );
    if (!feature) {
      const term = document.createElement("dt");
      term.textContent = "Selection";
      const description = document.createElement("dd");
      description.textContent = "No feature selected";
      list.append(term, description);
      return;
    }
    const properties = feature.properties || {};
    const displayFields = (state.manifest.viewer && state.manifest.viewer.display_fields) || [];
    const ordered = Array.from(new Set([...displayFields, ...knownDetailFields]));
    for (const field of ordered) {
      if (Object.prototype.hasOwnProperty.call(properties, field)) {
        addDefinition(list, field.replaceAll("_", " "), properties[field]);
        if (field === "source_record_id" && properties[field]) {
          const occurrenceUrl = `https://www.gbif.org/occurrence/${encodeURIComponent(
            properties[field]
          )}`;
          addLinkDefinition(list, "source record URL", occurrenceUrl, occurrenceUrl);
        }
      }
    }
  }

  async function boot() {
    try {
      const manifestUrl = manifestUrlFromLocation();
      state.bundleRoot = new URL(".", manifestUrl);
      state.manifest = await fetchJson(manifestUrl);
      requireSupportedVersions(state.manifest);
      requireMetadataFile(SOURCE_METADATA_PATH);
      requireMetadataFile(PROCESSING_METADATA_PATH);
      state.sourceMetadata = await fetchJson(urlForBundlePath(SOURCE_METADATA_PATH));
      state.processingMetadata = await fetchJson(urlForBundlePath(PROCESSING_METADATA_PATH));
      renderMetadata();

      const { layer, warning } = findUsableFlatGeobufLayer();
      if (warning) {
        setStatus(warning, false);
      }
      if (!layer) {
        setNoMapState(NO_MAP_LAYER_MESSAGE);
        setStatus("Metadata loaded; no FlatGeobuf map layer is available.", false);
        renderFilters();
        return;
      }

      state.map = initMap(layer);
      setStatus("Loading FlatGeobuf point layer", false);
      state.allFeatures = await loadFlatGeobufFeatures(urlForBundlePath(layer.path));
      state.filteredFeatures = state.allFeatures.slice();
      state.selectedFeatureId = state.filteredFeatures[0]
        ? state.filteredFeatures[0].properties._viewerId
        : null;
      renderFilters();
      applyFilters();
      setStatus("Bundle loaded", false);
    } catch (error) {
      setNoMapState(error.message || String(error));
      setStatus(error.message || String(error), true);
    }
  }

  byId("reset-filters").addEventListener("click", resetFilters);

  window.DwcaStaticViewer = {
    safeRelativePath,
    qualityFlagTokens,
    hasQualityFlags,
    matchesFilters,
    NO_MAP_LAYER_MESSAGE,
  };

  boot();
})();
