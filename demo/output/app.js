(function () {
  "use strict";

  const SUPPORTED_BUNDLE_SCHEMA_VERSION = "0.1.2";
  const SUPPORTED_VIEWER_CONTRACT_VERSION = "0.1.2";
  const SOURCE_METADATA_PATH = "metadata/source.json";
  const PROCESSING_METADATA_PATH = "metadata/processing.json";
  const ARTIFACT_DISPLAY_ORDER = [
    "data/occurrences.fgb",
    "data/occurrences.gpkg",
    "data/occurrences.parquet",
    SOURCE_METADATA_PATH,
    PROCESSING_METADATA_PATH,
  ];
  const VISIBILITY_ARTIFACT_PATHS = Object.freeze({
    "data/occurrences.fgb": "occurrences.fgb",
    "data/occurrences.gpkg": "occurrences.gpkg",
    "data/occurrences.parquet": "occurrences.parquet",
    [SOURCE_METADATA_PATH]: "source.json",
    [PROCESSING_METADATA_PATH]: "processing.json",
  });
  const FIELD_LABEL_OVERRIDES = {
    iucn_red_list_category: "IUCN Red List Categories",
  };
  const FIELD_LABEL_ACRONYMS = {
    doi: "DOI",
    gbif: "GBIF",
    id: "ID",
    iucn: "IUCN",
    obis: "OBIS",
    url: "URL",
  };
  const NO_MAP_LAYER_MESSAGE =
    "No FlatGeobuf map layer is available for this bundle. To display occurrence points on the map, generate the bundle with the FlatGeobuf output format selected.";
  const APP_DESCRIPTION_ALLOWED_TAGS = Object.freeze([
    "p",
    "b",
    "i",
    "h2",
    "h3",
    "h4",
    "a",
    "img",
    "br",
    "ol",
    "ul",
    "li",
    "table",
    "tr",
    "td",
    "iframe",
    "center",
    "small",
  ]);
  const APP_DESCRIPTION_ALLOWED_TAG_SET = new Set(APP_DESCRIPTION_ALLOWED_TAGS);
  const APP_DESCRIPTION_DROP_CONTENT_TAGS = new Set(["script", "style"]);
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
    popup: null,
    allFeatures: [],
    filteredFeatures: [],
    selectedFeatureId: null,
    appDescriptionPreviousFocus: null,
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

  function viewerVisibility(manifest) {
    const viewer = manifest && typeof manifest.viewer === "object" ? manifest.viewer : null;
    const visibility = viewer && viewer.visibility;
    return visibility && typeof visibility === "object" && !Array.isArray(visibility)
      ? visibility
      : {};
  }

  function viewerElementVisible(path, manifest = state.manifest) {
    let node = viewerVisibility(manifest);
    const keys = Array.isArray(path) ? path : path.split(".");
    for (const key of keys) {
      if (node && node.is_visible === false) {
        return false;
      }
      if (!node || typeof node !== "object" || Array.isArray(node)) {
        return true;
      }
      node = node[key];
    }
    return !(node && typeof node === "object" && node.is_visible === false);
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

  function normalizeDoi(value) {
    if (!value) {
      return null;
    }
    const text = String(value).trim().replace(/[.,]+$/, "");
    const urlMatch = text.match(/https:\/\/doi\.org\/(10\.\d{4,9}\/\S+)/i);
    const candidate = (urlMatch ? urlMatch[1] : text.replace(/^doi:/i, "").trim()).replace(
      /[.,]+$/,
      ""
    );
    return /^10\.\d{4,9}\/\S+$/i.test(candidate) ? candidate : null;
  }

  function doiHref(value) {
    const doi = normalizeDoi(value);
    return doi ? `https://doi.org/${doi}` : null;
  }

  function appendExternalLink(parent, href, text) {
    const link = document.createElement("a");
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = text || href;
    parent.append(link);
  }

  function appendCitationContent(parent, value) {
    const text = displayValue(value);
    const doiUrlPattern = /https:\/\/doi\.org\/10\.\d{4,9}\/\S+/gi;
    let offset = 0;
    let match = doiUrlPattern.exec(text);
    while (match) {
      if (match.index > offset) {
        parent.append(document.createTextNode(text.slice(offset, match.index)));
      }
      const rawUrl = match[0];
      const url = rawUrl.replace(/[.,]+$/, "");
      appendExternalLink(parent, url, url);
      if (url.length < rawUrl.length) {
        parent.append(document.createTextNode(rawUrl.slice(url.length)));
      }
      offset = match.index + match[0].length;
      match = doiUrlPattern.exec(text);
    }
    if (offset < text.length) {
      parent.append(document.createTextNode(text.slice(offset)));
    }
  }

  function addProvenanceDefinition(list, label, value) {
    if (value === null || value === undefined || value === "") {
      return;
    }
    if (label === "DOI") {
      const href = doiHref(value);
      if (href) {
        addLinkDefinition(list, label, href, href);
        return;
      }
    }
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    if (label === "Citation") {
      appendCitationContent(description, value);
    } else {
      description.textContent = displayValue(value);
    }
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

  function viewerMapTitle(manifest) {
    const viewer = (manifest && manifest.viewer) || {};
    const title = viewer.map_title;
    return title === null || title === undefined ? "" : String(title).trim();
  }

  function viewerAppDescription(manifest) {
    const viewer = (manifest && manifest.viewer) || {};
    const description = viewer.appDescription;
    return description === null || description === undefined ? "" : String(description).trim();
  }

  function isSafeAppDescriptionUrl(value) {
    if (typeof value !== "string") {
      return false;
    }
    const url = value.trim();
    if (!url || /[\u0000-\u001f\u007f]/.test(url) || url.includes("\\")) {
      return false;
    }
    if (url.startsWith("//") || url.startsWith("/")) {
      return false;
    }
    const schemeMatch = url.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):/);
    if (schemeMatch) {
      return ["http:", "https:"].includes(`${schemeMatch[1].toLowerCase()}:`);
    }
    return true;
  }

  function copySafeAttribute(source, target, name) {
    if (!source.hasAttribute(name)) {
      return;
    }
    const value = source.getAttribute(name);
    if (value !== null) {
      target.setAttribute(name, value);
    }
  }

  function copyDimensionAttribute(source, target, name) {
    if (!source.hasAttribute(name)) {
      return;
    }
    const value = source.getAttribute(name).trim();
    if (/^\d{1,5}$/.test(value) || /^\d{1,3}%$/.test(value)) {
      target.setAttribute(name, value);
    }
  }

  function copyLoadingAttribute(source, target) {
    if (!source.hasAttribute("loading")) {
      return;
    }
    const value = source.getAttribute("loading").trim().toLowerCase();
    if (value === "lazy" || value === "eager") {
      target.setAttribute("loading", value);
    }
  }

  function sanitizeElementAttributes(source, target, tagName) {
    if (tagName === "a") {
      const href = source.getAttribute("href");
      if (href && isSafeAppDescriptionUrl(href)) {
        target.setAttribute("href", href.trim());
        if (/^https?:/i.test(href.trim())) {
          target.target = "_blank";
          target.rel = "noopener";
        }
      }
      copySafeAttribute(source, target, "title");
    } else if (tagName === "img") {
      const src = source.getAttribute("src");
      if (src && isSafeAppDescriptionUrl(src)) {
        target.setAttribute("src", src.trim());
      }
      copySafeAttribute(source, target, "alt");
      copySafeAttribute(source, target, "title");
      copyDimensionAttribute(source, target, "width");
      copyDimensionAttribute(source, target, "height");
      copyLoadingAttribute(source, target);
    } else if (tagName === "iframe") {
      const src = source.getAttribute("src");
      if (src && isSafeAppDescriptionUrl(src)) {
        target.setAttribute("src", src.trim());
      }
      copySafeAttribute(source, target, "title");
      copySafeAttribute(source, target, "allow");
      copyDimensionAttribute(source, target, "width");
      copyDimensionAttribute(source, target, "height");
      copyLoadingAttribute(source, target);
      if (source.hasAttribute("allowfullscreen")) {
        target.setAttribute("allowfullscreen", "");
      }
    }
  }

  function sanitizeAppDescriptionNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return document.createTextNode(node.textContent || "");
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
      return document.createDocumentFragment();
    }
    const tagName = node.tagName.toLowerCase();
    if (APP_DESCRIPTION_DROP_CONTENT_TAGS.has(tagName)) {
      return document.createDocumentFragment();
    }
    const fragment = document.createDocumentFragment();
    const appendSanitizedChildren = (parent) => {
      for (const child of Array.from(node.childNodes)) {
        parent.append(sanitizeAppDescriptionNode(child));
      }
    };
    if (!APP_DESCRIPTION_ALLOWED_TAG_SET.has(tagName)) {
      appendSanitizedChildren(fragment);
      return fragment;
    }
    if (
      (tagName === "img" || tagName === "iframe") &&
      !isSafeAppDescriptionUrl(node.getAttribute("src") || "")
    ) {
      return fragment;
    }
    const sanitized = document.createElement(tagName);
    sanitizeElementAttributes(node, sanitized, tagName);
    if (tagName !== "br" && tagName !== "img") {
      appendSanitizedChildren(sanitized);
    }
    return sanitized;
  }

  function sanitizeAppDescription(html) {
    const parsed = new DOMParser().parseFromString(String(html), "text/html");
    const fragment = document.createDocumentFragment();
    for (const child of Array.from(parsed.body.childNodes)) {
      fragment.append(sanitizeAppDescriptionNode(child));
    }
    return fragment;
  }

  function renderAppDescriptionContent() {
    const content = byId("app-description-content");
    content.replaceChildren();
    const description = viewerAppDescription(state.manifest);
    if (description) {
      content.append(sanitizeAppDescription(description));
    }
  }

  function openAppDescriptionDialog() {
    const dialog = byId("app-description-dialog");
    if (dialog.hidden) {
      state.appDescriptionPreviousFocus = document.activeElement;
    }
    renderAppDescriptionContent();
    dialog.hidden = false;
    byId("app-description-close").focus();
  }

  function closeAppDescriptionDialog() {
    const dialog = byId("app-description-dialog");
    if (dialog.hidden) {
      return;
    }
    dialog.hidden = true;
    byId("app-description-content").replaceChildren();
    if (
      state.appDescriptionPreviousFocus &&
      typeof state.appDescriptionPreviousFocus.focus === "function"
    ) {
      state.appDescriptionPreviousFocus.focus();
    }
    state.appDescriptionPreviousFocus = null;
  }

  function initAppDescriptionDialog() {
    const button = byId("app-description-button");
    const dialog = byId("app-description-dialog");
    byId("app-description-close").addEventListener("click", closeAppDescriptionDialog);
    button.addEventListener("click", openAppDescriptionDialog);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        closeAppDescriptionDialog();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !dialog.hidden) {
        closeAppDescriptionDialog();
      }
    });
  }

  function renderAppHeader() {
    const header = byId("map-title-header");
    const titleNode = byId("map-title");
    const descriptionButton = byId("app-description-button");
    const title = viewerMapTitle(state.manifest);
    const description = viewerAppDescription(state.manifest);
    titleNode.textContent = title;
    titleNode.hidden = !title;
    descriptionButton.hidden = !description;
    header.hidden = !title && !description;
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
      ["dataset_title", "Dataset title", dataset.title || state.manifest.title || manifestSource.title],
      ["description", "Description", dataset.description],
      ["publisher", "Publisher", dataset.publisher || manifestSource.publisher],
      [null, "Homepage", dataset.homepage],
      ["doi", "DOI", dataset.doi || gbif.doi || obis.doi || manifestSource.doi],
      ["citation", "Citation", dataset.citation || gbif.citation || obis.citation || manifestSource.citation],
      ["license", "License", gbif.license || obis.license || rights.license || manifestSource.license],
      ["rights_holder", "Rights holder", rights.rights_holder],
      ["source_archive", "Source archive", [archive.name, archive.kind, archive.bytes].filter(Boolean).join(" | ")],
      ["archive_sha256", "Archive SHA-256", archive.sha256],
      ["gbif_dataset_key", "GBIF dataset key", gbif.dataset_key || manifestSource.gbif_dataset_key],
      ["gbif_download_key", "GBIF download key", gbif.download_key || manifestSource.gbif_download_key],
      [null, "OBIS dataset id", obis.dataset_id || manifestSource.obis_dataset_id],
      ["generated", "Generated", state.manifest.created_at || processing.created_at],
      [
        "converter",
        "Converter",
        [
          state.manifest.generator && state.manifest.generator.name,
          state.manifest.generator && state.manifest.generator.version,
        ]
          .filter(Boolean)
          .join(" "),
      ],
      ["validation", "Validation", processing.validation && processing.validation.status],
    ];
  }

  function renderProvenance() {
    const list = byId("provenance-list");
    list.replaceChildren();
    for (const [key, label, value] of provenanceRows()) {
      if (key && !viewerElementVisible(`panel-info.provenance.${key}`)) {
        continue;
      }
      addProvenanceDefinition(list, label, value);
    }
  }

  function artifactDisplayRank(path) {
    const index = ARTIFACT_DISPLAY_ORDER.indexOf(path);
    return index === -1 ? ARTIFACT_DISPLAY_ORDER.length : index;
  }

  function artifactLinkLabel(path) {
    if (path === SOURCE_METADATA_PATH) {
      return "source.json (metadata)";
    }
    if (path === PROCESSING_METADATA_PATH) {
      return "processing.json (metadata)";
    }
    return path.startsWith("data/") ? path.slice("data/".length) : path;
  }

  function artifactVisibilityKey(path) {
    return VISIBILITY_ARTIFACT_PATHS[path] || null;
  }

  function legacyCopyText(text) {
    if (typeof document.execCommand !== "function") {
      return Promise.reject(new Error("Clipboard copy is not available."));
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-1000px";
    textarea.style.top = "-1000px";
    document.body.append(textarea);

    const selection = document.getSelection();
    const previousRange =
      selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);

    let copied = false;
    try {
      copied = document.execCommand("copy");
    } finally {
      textarea.remove();
      if (selection && previousRange) {
        selection.removeAllRanges();
        selection.addRange(previousRange);
      }
    }
    return copied
      ? Promise.resolve()
      : Promise.reject(new Error("Clipboard copy failed."));
  }

  function copyTextToClipboard(text) {
    if (
      typeof navigator !== "undefined" &&
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === "function"
    ) {
      return navigator.clipboard.writeText(text).catch(() => legacyCopyText(text));
    }
    return legacyCopyText(text);
  }

  function renderArtifacts() {
    const container = byId("artifact-list");
    container.replaceChildren();
    const files = (state.manifest.files || [])
      .map((entry, index) => ({ entry, index }))
      .sort(
        (left, right) =>
          artifactDisplayRank(left.entry.path) -
            artifactDisplayRank(right.entry.path) || left.index - right.index
    )
      .map((item) => item.entry);
    for (const entry of files) {
      const visibilityKey = artifactVisibilityKey(entry.path);
      if (
        visibilityKey &&
        !viewerElementVisible(["panel-download", "artifacts", visibilityKey])
      ) {
        continue;
      }
      const item = document.createElement("article");
      item.className = "artifact";
      const artifactUrl = urlForBundlePath(entry.path).href;
      const row = document.createElement("div");
      row.className = "artifact-row";
      const link = document.createElement("a");
      link.href = artifactUrl;
      link.textContent = artifactLinkLabel(entry.path);
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "copy-url-btn";
      copyBtn.title = "Copy URL";
      copyBtn.setAttribute("aria-label", `Copy URL for ${artifactLinkLabel(entry.path)}`);
      const copyImg = document.createElement("img");
      copyImg.src = "assets/pic/pic-copy-32.png";
      copyImg.alt = "";
      copyImg.width = 16;
      copyImg.height = 16;
      copyBtn.append(copyImg);
      copyBtn.addEventListener("click", (event) => {
        event.preventDefault();
        copyTextToClipboard(artifactUrl).then(
          () => {
            copyBtn.classList.add("copied");
            copyBtn.title = "Copied!";
            setTimeout(() => {
              copyBtn.classList.remove("copied");
              copyBtn.title = "Copy URL";
            }, 1500);
          },
          () => {
            copyBtn.title = "Copy failed";
            setTimeout(() => { copyBtn.title = "Copy URL"; }, 1500);
          }
        );
      });
      row.append(link, copyBtn);
      const description = document.createElement("p");
      description.textContent = [
        entry.role,
        `${displayValue(entry.record_count)} records`,
        entry.bytes ? `${entry.bytes} bytes` : null,
      ]
        .filter(Boolean)
        .join(" | ");
      item.append(row, description);
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
          "circle-stroke-width": 2,
          "circle-stroke-color": "#111827",
          "circle-opacity": 1,
        },
      });
      updateSelectedFeatureLayer();
      map.on("click", "occurrence-points", (event) => {
        const feature = event.features && event.features[0];
        if (feature && feature.properties) {
          selectFeature(Number(feature.properties._viewerId));
          showPointPopup(feature, event.lngLat);
        }
      });
      map.on("click", (event) => {
        const features = map.queryRenderedFeatures(event.point, { layers: ["occurrence-points"] });
        if (!features.length) {
          closePointPopup();
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
      state.allFeatures.some((feature) => featureHasField(feature, field)) &&
      viewerElementVisible(`panel-filters.filter_groups.${field}`)
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
      const group = createFilterGroup("Scientific Name");
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

    if (available.includes("kingdom")) {
      container.append(createCategoricalFilter("kingdom"));
    }

    if (available.includes("iucn_red_list_category")) {
      container.append(createCategoricalFilter("iucn_red_list_category"));
    }

    if (available.includes("event_year")) {
      const group = createFilterGroup("Event Year");
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

    if (available.includes("basis_of_record")) {
      container.append(createCategoricalFilter("basis_of_record"));
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

  function fieldLabel(field) {
    if (FIELD_LABEL_OVERRIDES[field]) {
      return FIELD_LABEL_OVERRIDES[field];
    }
    return field
      .split("_")
      .filter(Boolean)
      .map((token) => {
        const normalized = token.toLowerCase();
        return (
          FIELD_LABEL_ACRONYMS[normalized] ||
          `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)}`
        );
      })
      .join(" ");
  }

  function createCategoricalFilter(field) {
    const group = createFilterGroup(fieldLabel(field));
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
    const group = createFilterGroup("Quality Flags");
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
    const list = byId("sidebar-record-list");
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
    closePointPopup();
  }

  function clearHiddenFilterState() {
    const groups = [
      "scientific_name",
      "kingdom",
      "iucn_red_list_category",
      "event_year",
      "basis_of_record",
      "quality_flags",
    ];
    for (const group of groups) {
      if (viewerElementVisible(`panel-filters.filter_groups.${group}`)) {
        continue;
      }
      if (group === "scientific_name") {
        state.filters.scientific_name = "";
      } else if (group === "event_year") {
        state.filters.year_min = "";
        state.filters.year_max = "";
      } else if (group === "quality_flags") {
        state.filters.quality_mode = "all";
        state.filters.quality_tokens = new Set();
      } else {
        delete state.filters.categories[group];
      }
    }
  }

  function setBottomCollapsed(bottomPanels, toggleBtn, collapsed) {
    bottomPanels.classList.toggle("collapsed", collapsed);
    const icon = toggleBtn.querySelector(".toggle-icon");
    if (icon) {
      icon.textContent = collapsed ? "▶" : "▼";
    }
  }

  function applyManifestVisibility() {
    const shell = document.querySelector(".viewer-shell");
    const panelIds = ["panel-info", "panel-filters", "panel-records", "panel-download"];
    const activePanelId = activePanel ? `panel-${activePanel}` : null;
    if (activePanelId && !viewerElementVisible(activePanelId)) {
      closePanel();
    }
    for (const panelId of panelIds) {
      const visible = viewerElementVisible(panelId);
      const panel = byId(panelId);
      const button = document.querySelector(`.ctrl-btn[data-panel="${panelId.slice(6)}"]`);
      if (button) {
        button.hidden = !visible;
      }
      if (!visible && panel) {
        panel.hidden = true;
      }
    }
    const hasSidebarLauncher = panelIds.some((panelId) => viewerElementVisible(panelId));
    byId("control-strip").hidden = !hasSidebarLauncher;
    byId("sidebar-panels").hidden = !hasSidebarLauncher;
    shell.classList.toggle("control-strip-hidden", !hasSidebarLauncher);

    byId("panel-info-header").hidden = !viewerElementVisible("panel-info.header");
    byId("panel-info-counts").hidden = !viewerElementVisible("panel-info.counts");
    byId("panel-info-provenance").hidden = !viewerElementVisible("panel-info.provenance");
    clearHiddenFilterState();

    const bottomPanels = byId("bottom-panels");
    const toggleBar = byId("bottom-toggle-bar");
    const toggleBtn = byId("bottom-toggle");
    const content = byId("bottom-panels-content");
    const bottomVisible = viewerElementVisible("bottom-panels");
    const contentVisible = viewerElementVisible("bottom-panels.bottom-panels-content");
    bottomPanels.hidden = !bottomVisible;
    toggleBar.hidden = !bottomVisible;
    content.hidden = !bottomVisible || !contentVisible;
    byId("bottom-feature-details").hidden = !viewerElementVisible(
      "bottom-panels.bottom-panels-content.feature_details"
    );
    byId("bottom-processing").hidden = !viewerElementVisible(
      "bottom-panels.bottom-panels-content.processing"
    );
    toggleBtn.hidden = !bottomVisible || !contentVisible;
    if (!viewerElementVisible("popup")) {
      closePointPopup();
    }
    if (state.map) {
      state.map.resize();
    }
  }

  const POPUP_FIELDS = null;  // now computed dynamically from manifest.viewer.display_fields + knownDetailFields

  function popupFieldsForFeature(feature) {
    const displayFields = (state.manifest && state.manifest.viewer && state.manifest.viewer.display_fields) || [];
    const ordered = Array.from(new Set([...displayFields, ...knownDetailFields]));
    return ordered.filter((field) =>
      Object.prototype.hasOwnProperty.call(feature.properties || {}, field) &&
      feature.properties[field] != null &&
      feature.properties[field] !== ""
    );
  }

  function buildPopupHTML(feature) {
    const fields = popupFieldsForFeature(feature);
    if (fields.length === 0) {
      return '<h2 class="popup-title">Feature Details</h2><p class="popup-empty">No details available</p>';
    }
    const rows = fields.map((field) => {
      let row = `<dt>${escapeHTML(fieldLabel(field))}</dt><dd>${escapeHTML(displayValue(feature.properties[field]))}</dd>`;
      if (field === "source_record_id" && feature.properties[field]) {
        const occurrenceUrl = `https://www.gbif.org/occurrence/${encodeURIComponent(feature.properties[field])}`;
        row += `<dt>Source Record URL</dt><dd><a href="${escapeHTML(occurrenceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHTML(occurrenceUrl)}</a></dd>`;
      }
      return row;
    });
    return `<h2 class="popup-title">Feature Details</h2><div class="popup-scroll"><dl class="popup-dl">${rows.join("")}</dl></div>`;
  }

  function escapeHTML(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function showPointPopup(feature, lngLat) {
    closePointPopup();
    if (!state.map || !viewerElementVisible("popup")) {
      return;
    }
    const popup = new window.maplibregl.Popup({
      closeButton: true,
      closeOnClick: false,
      maxWidth: "320px",
      className: "map-point-popup",
      offset: 10,
    })
      .setLngLat(lngLat)
      .setHTML(buildPopupHTML(feature))
      .addTo(state.map);
    state.popup = popup;
    const scrollEl = popup.getElement().querySelector(".popup-scroll");
    if (scrollEl) {
      scrollEl.scrollTop = 0;
    }
  }

  function closePointPopup() {
    if (state.popup) {
      state.popup.remove();
      state.popup = null;
    }
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
        addDefinition(list, fieldLabel(field), properties[field]);
        if (field === "source_record_id" && properties[field]) {
          const occurrenceUrl = `https://www.gbif.org/occurrence/${encodeURIComponent(
            properties[field]
          )}`;
          addLinkDefinition(list, "Source Record URL", occurrenceUrl, occurrenceUrl);
        }
      }
    }
  }

  /* ---- Sidebar panel toggling ---- */

  let activePanel = null;

  function openPanel(panelName) {
    if (!viewerElementVisible(`panel-${panelName}`)) {
      return;
    }
    if (activePanel === panelName) {
      closePanel();
      return;
    }
    closePanel();
    activePanel = panelName;
    const panel = document.getElementById(`panel-${panelName}`);
    if (panel) {
      panel.hidden = false;
    }
    document.querySelector(".viewer-shell").classList.add("panel-open");
    updateActiveButton(panelName);
    if (state.map) {
      state.map.resize();
    }
  }

  function closePanel() {
    if (activePanel) {
      const panel = document.getElementById(`panel-${activePanel}`);
      if (panel) {
        panel.hidden = true;
      }
      activePanel = null;
    }
    document.querySelector(".viewer-shell").classList.remove("panel-open");
    updateActiveButton(null);
    if (state.map) {
      state.map.resize();
    }
  }

  function updateActiveButton(panelName) {
    for (const btn of document.querySelectorAll(".ctrl-btn")) {
      btn.classList.toggle("active", btn.dataset.panel === panelName);
    }
  }

  function initPanelToggles() {
    for (const btn of document.querySelectorAll(".ctrl-btn")) {
      btn.addEventListener("click", () => {
        openPanel(btn.dataset.panel);
      });
    }
  }

  /* ---- Bottom panel toggling ---- */

  function initBottomToggle() {
    const bottomPanels = document.getElementById("bottom-panels");
    const toggleBtn = document.getElementById("bottom-toggle");
    if (!bottomPanels || !toggleBtn) {
      return;
    }
    toggleBtn.addEventListener("click", () => {
      setBottomCollapsed(
        bottomPanels,
        toggleBtn,
        !bottomPanels.classList.contains("collapsed")
      );
      if (state.map) {
        setTimeout(() => state.map.resize(), 260);
      }
    });
  }

  async function boot() {
    try {
      initPanelToggles();
      initBottomToggle();
      initAppDescriptionDialog();
      const manifestUrl = manifestUrlFromLocation();
      state.bundleRoot = new URL(".", manifestUrl);
      state.manifest = await fetchJson(manifestUrl);
      requireSupportedVersions(state.manifest);
      applyManifestVisibility();
      renderAppHeader();
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
    viewerMapTitle,
    viewerAppDescription,
    sanitizeAppDescription,
    APP_DESCRIPTION_ALLOWED_TAGS,
    NO_MAP_LAYER_MESSAGE,
  };

  boot();
})();
