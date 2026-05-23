const DATA = window.GRAPH_DATA;

const PALETTES = {
  generator: ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#be123c", "#4f46e5", "#65a30d", "#c026d3", "#0f766e", "#b45309"],
  neon: ["#22d3ee", "#fb7185", "#4ade80", "#c084fc", "#f97316", "#06b6d4", "#e11d48", "#818cf8", "#84cc16", "#f0abfc", "#2dd4bf", "#f59e0b"],
};

const PRESETS = {
  blueprint: {
    backgroundHue: 210,
    backgroundSaturation: 33,
    backgroundLightness: 98,
    backgroundBlack: 0,
    lineMode: "blueprint",
    lineHue: 217,
    lineSaturation: 91,
    lineLightness: 60,
    lineBlack: 0,
    lineWidth: 0.75,
    lineAlpha: 0.12,
    densityEnabled: true,
    densityWidth: 2.5,
    densityAlpha: 0.22,
    pointMode: "steel",
    pointHue: 222,
    pointSaturation: 47,
    pointLightness: 11,
    pointBlack: 0,
    pointSize: 2.5,
    pointAlpha: 0.9,
  },
  generator: {
    backgroundHue: 0,
    backgroundSaturation: 0,
    backgroundLightness: 100,
    backgroundBlack: 0,
    lineMode: "generator",
    lineHue: 217,
    lineSaturation: 91,
    lineLightness: 60,
    lineBlack: 0,
    lineWidth: 0.85,
    lineAlpha: 0.13,
    densityEnabled: true,
    densityWidth: 2,
    densityAlpha: 0.2,
    pointMode: "ink",
    pointHue: 222,
    pointSaturation: 47,
    pointLightness: 11,
    pointBlack: 0,
    pointSize: 2.8,
    pointAlpha: 0.92,
  },
  print: {
    backgroundHue: 0,
    backgroundSaturation: 0,
    backgroundLightness: 100,
    backgroundBlack: 0,
    lineMode: "charcoal",
    lineHue: 222,
    lineSaturation: 47,
    lineLightness: 11,
    lineBlack: 0,
    lineWidth: 0.75,
    lineAlpha: 0.14,
    densityEnabled: true,
    densityWidth: 2,
    densityAlpha: 0.24,
    pointMode: "ink",
    pointHue: 0,
    pointSaturation: 0,
    pointLightness: 0,
    pointBlack: 0,
    pointSize: 3.2,
    pointAlpha: 1,
  },
  dark: {
    backgroundHue: 227,
    backgroundSaturation: 49,
    backgroundLightness: 8,
    backgroundBlack: 0,
    lineMode: "neon",
    lineHue: 187,
    lineSaturation: 85,
    lineLightness: 53,
    lineBlack: 0,
    lineWidth: 0.85,
    lineAlpha: 0.16,
    densityEnabled: true,
    densityWidth: 2.5,
    densityAlpha: 0.25,
    pointMode: "neon",
    pointHue: 187,
    pointSaturation: 85,
    pointLightness: 53,
    pointBlack: 0,
    pointSize: 2.9,
    pointAlpha: 0.95,
  },
};

const controls = {
  sourceSelect: document.getElementById("sourceSelect"),
  datasetSelect: document.getElementById("datasetSelect"),
  datasetStats: document.getElementById("datasetStats"),
  pointsFile: document.getElementById("pointsFile"),
  edgesFile: document.getElementById("edgesFile"),
  loadCsvDataset: document.getElementById("loadCsvDataset"),
  loadStatus: document.getElementById("loadStatus"),
  backgroundHue: document.getElementById("backgroundHue"),
  backgroundSaturation: document.getElementById("backgroundSaturation"),
  backgroundLightness: document.getElementById("backgroundLightness"),
  backgroundBlack: document.getElementById("backgroundBlack"),
  backgroundSwatch: document.getElementById("backgroundSwatch"),
  exportScale: document.getElementById("exportScale"),
  lineMode: document.getElementById("lineMode"),
  lineHue: document.getElementById("lineHue"),
  lineSaturation: document.getElementById("lineSaturation"),
  lineLightness: document.getElementById("lineLightness"),
  lineBlack: document.getElementById("lineBlack"),
  lineSwatch: document.getElementById("lineSwatch"),
  lineWidth: document.getElementById("lineWidth"),
  lineAlpha: document.getElementById("lineAlpha"),
  densityEnabled: document.getElementById("densityEnabled"),
  densityWidth: document.getElementById("densityWidth"),
  densityAlpha: document.getElementById("densityAlpha"),
  pointMode: document.getElementById("pointMode"),
  pointHue: document.getElementById("pointHue"),
  pointSaturation: document.getElementById("pointSaturation"),
  pointLightness: document.getElementById("pointLightness"),
  pointBlack: document.getElementById("pointBlack"),
  pointSwatch: document.getElementById("pointSwatch"),
  pointSize: document.getElementById("pointSize"),
  pointAlpha: document.getElementById("pointAlpha"),
  showLines: document.getElementById("showLines"),
  showPoints: document.getElementById("showPoints"),
  showLabels: document.getElementById("showLabels"),
  downloadPng: document.getElementById("downloadPng"),
  resetView: document.getElementById("resetView"),
  activeTitle: document.getElementById("activeTitle"),
  activeSubtitle: document.getElementById("activeSubtitle"),
  renderInfo: document.getElementById("renderInfo"),
  canvas: document.getElementById("graphCanvas"),
};

const outputs = {
  backgroundHue: document.getElementById("backgroundHueOut"),
  backgroundSaturation: document.getElementById("backgroundSaturationOut"),
  backgroundLightness: document.getElementById("backgroundLightnessOut"),
  backgroundBlack: document.getElementById("backgroundBlackOut"),
  lineHue: document.getElementById("lineHueOut"),
  lineSaturation: document.getElementById("lineSaturationOut"),
  lineLightness: document.getElementById("lineLightnessOut"),
  lineBlack: document.getElementById("lineBlackOut"),
  lineWidth: document.getElementById("lineWidthOut"),
  lineAlpha: document.getElementById("lineAlphaOut"),
  densityWidth: document.getElementById("densityWidthOut"),
  densityAlpha: document.getElementById("densityAlphaOut"),
  pointHue: document.getElementById("pointHueOut"),
  pointSaturation: document.getElementById("pointSaturationOut"),
  pointLightness: document.getElementById("pointLightnessOut"),
  pointBlack: document.getElementById("pointBlackOut"),
  pointSize: document.getElementById("pointSizeOut"),
  pointAlpha: document.getElementById("pointAlphaOut"),
};

let currentData = null;
let renderQueued = false;
let customDatasetCounter = 0;

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
  ];
}

function mix(a, b, t) {
  const ar = hexToRgb(a);
  const br = hexToRgb(b);
  return ar.map((v, i) => Math.round(v + (br[i] - v) * t));
}

function hslToRgb(h, s, l) {
  h = ((h % 360) + 360) % 360;
  s = Math.max(0, Math.min(100, s)) / 100;
  l = Math.max(0, Math.min(100, l)) / 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0;
  let g = 0;
  let b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  return [r, g, b].map((v) => Math.round((v + m) * 255));
}

function applyBlack(rgb, blackPercent) {
  const t = Math.max(0, Math.min(100, blackPercent)) / 100;
  return rgb.map((v) => Math.round(v * (1 - t)));
}

function customBaseRgb(prefix) {
  return hslToRgb(
    Number(controls[`${prefix}Hue`].value),
    Number(controls[`${prefix}Saturation`].value),
    Number(controls[`${prefix}Lightness`].value),
  );
}

function customRgb(prefix) {
  return applyBlack(customBaseRgb(prefix), Number(controls[`${prefix}Black`].value));
}

function rgbToHex(rgb) {
  return `#${rgb.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

function rgba(rgb, alpha) {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

function generatorColor(index, mode) {
  let base;
  if (mode === "custom") base = customBaseRgb("line");
  else if (mode === "generator") base = hexToRgb(PALETTES.generator[index % PALETTES.generator.length]);
  else if (mode === "neon") base = hexToRgb(PALETTES.neon[index % PALETTES.neon.length]);
  else if (mode === "blueprint") base = hexToRgb("#2563eb");
  else if (mode === "charcoal") base = hexToRgb("#111827");
  else if (mode === "sage") base = hexToRgb("#6b8f71");
  else if (mode === "mist") base = hexToRgb("#64748b");
  else if (mode === "warmCool") base = mix("#2563eb", "#f97316", index / Math.max(1, currentData.translations - 1));
  else base = hexToRgb("#2563eb");
  return applyBlack(base, Number(controls.lineBlack.value));
}

function pointColor(value, mode, alpha) {
  const t = currentData.valueSpan === 0 ? 0 : (value - currentData.minValue) / currentData.valueSpan;
  let base;
  if (mode === "custom") base = customBaseRgb("point");
  else if (mode === "ink") base = hexToRgb("#0f172a");
  else if (mode === "steel") base = mix("#334155", "#020617", t);
  if (mode === "topographic") {
    base = t < 0.5 ? mix("#0f766e", "#84cc16", t * 2) : mix("#84cc16", "#f97316", (t - 0.5) * 2);
  }
  else if (mode === "coolWarm") base = mix("#0891b2", "#be123c", t);
  else if (mode === "neon") base = mix("#22d3ee", "#f0abfc", t);
  else if (mode === "violet") base = mix("#0f766e", "#7c3aed", t);
  else if (!base) base = hexToRgb("#0f172a");
  return rgba(applyBlack(base, Number(controls.pointBlack.value)), alpha);
}

function getSettings() {
  return {
    backgroundColor: rgbToHex(customRgb("background")),
    exportScale: Number(controls.exportScale.value),
    lineMode: controls.lineMode.value,
    lineWidth: Number(controls.lineWidth.value),
    lineAlpha: Number(controls.lineAlpha.value),
    densityEnabled: controls.densityEnabled.checked,
    densityWidth: Number(controls.densityWidth.value),
    densityAlpha: Number(controls.densityAlpha.value),
    pointMode: controls.pointMode.value,
    pointSize: Number(controls.pointSize.value),
    pointAlpha: Number(controls.pointAlpha.value),
    showLines: controls.showLines.checked,
    showPoints: controls.showPoints.checked,
    showLabels: controls.showLabels.checked,
  };
}

function setSettings(settings) {
  Object.entries(settings).forEach(([key, value]) => {
    const control = controls[key];
    if (!control) return;
    if (control.type === "checkbox") control.checked = Boolean(value);
    else control.value = String(value);
  });
  updateOutputs();
  queueRender();
}

function updateOutputs() {
  outputs.backgroundHue.textContent = `${Number(controls.backgroundHue.value).toFixed(0)}°`;
  outputs.backgroundSaturation.textContent = `${Number(controls.backgroundSaturation.value).toFixed(0)}%`;
  outputs.backgroundLightness.textContent = `${Number(controls.backgroundLightness.value).toFixed(0)}%`;
  outputs.backgroundBlack.textContent = `${Number(controls.backgroundBlack.value).toFixed(0)}%`;
  outputs.lineHue.textContent = `${Number(controls.lineHue.value).toFixed(0)}°`;
  outputs.lineSaturation.textContent = `${Number(controls.lineSaturation.value).toFixed(0)}%`;
  outputs.lineLightness.textContent = `${Number(controls.lineLightness.value).toFixed(0)}%`;
  outputs.lineBlack.textContent = `${Number(controls.lineBlack.value).toFixed(0)}%`;
  outputs.lineWidth.textContent = `${Number(controls.lineWidth.value).toFixed(1)}px`;
  outputs.lineAlpha.textContent = Number(controls.lineAlpha.value).toFixed(2);
  outputs.densityWidth.textContent = `+${Number(controls.densityWidth.value).toFixed(1)}px`;
  outputs.densityAlpha.textContent = Number(controls.densityAlpha.value).toFixed(2);
  outputs.pointHue.textContent = `${Number(controls.pointHue.value).toFixed(0)}°`;
  outputs.pointSaturation.textContent = `${Number(controls.pointSaturation.value).toFixed(0)}%`;
  outputs.pointLightness.textContent = `${Number(controls.pointLightness.value).toFixed(0)}%`;
  outputs.pointBlack.textContent = `${Number(controls.pointBlack.value).toFixed(0)}%`;
  outputs.pointSize.textContent = `${Number(controls.pointSize.value).toFixed(1)}px`;
  outputs.pointAlpha.textContent = Number(controls.pointAlpha.value).toFixed(2);
  controls.backgroundSwatch.style.background = rgbToHex(customRgb("background"));
  controls.lineSwatch.style.background = rgbToHex(customRgb("line"));
  controls.pointSwatch.style.background = rgbToHex(customRgb("point"));
}

function prepareDataset(dataset) {
  const pointMap = new Map();
  const points = dataset.pointRows.map(([id, x, y, maxEmbeddingAbs]) => {
    const point = { id, x, y, maxEmbeddingAbs };
    pointMap.set(id, point);
    return point;
  });
  const edges = dataset.edgeRows.map(([fromId, toId, generator]) => ({
    from: pointMap.get(fromId),
    to: pointMap.get(toId),
    generator,
  }));
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const values = points.map((p) => p.maxEmbeddingAbs);
  return {
    ...dataset,
    pointsList: points,
    edgesList: edges,
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
    minValue: Math.min(...values),
    maxValue: Math.max(...values),
    valueSpan: Math.max(...values) - Math.min(...values),
  };
}

function setCurrentDataset(dataset) {
  currentData = prepareDataset(dataset);
  controls.activeTitle.textContent = currentData.title;
  const ratioText = Number.isFinite(currentData.ratioVsGrid) ? ` · ${currentData.ratioVsGrid.toFixed(3)}x grade` : "";
  controls.activeSubtitle.textContent = `${currentData.selector} · ${currentData.points.toLocaleString("pt-BR")} pontos · ${currentData.edges.toLocaleString("pt-BR")} arestas${ratioText}`;
  controls.datasetStats.innerHTML = [
    ["source", currentData.sourceLabel || currentData.source || "custom"],
    ["selector", currentData.selector],
    ["translations", currentData.translations],
    ["points", currentData.points.toLocaleString("pt-BR")],
    ["edges", currentData.edges.toLocaleString("pt-BR")],
    ["R", currentData.polydiscRadius],
    ["ratio", Number.isFinite(currentData.ratioVsGrid) ? `${currentData.ratioVsGrid.toFixed(3)}x` : "n/a"],
  ]
    .map(([label, value]) => `<span><strong>${label}</strong><br>${value}</span>`)
    .join("");
  queueRender();
}

function setDataset(slug) {
  const dataset = DATA.datasets.find((item) => item.slug === slug) || DATA.datasets[0];
  if (!dataset) return;
  setCurrentDataset(dataset);
}

function rebuildSourceOptions() {
  const previous = controls.sourceSelect.value || "all";
  controls.sourceSelect.innerHTML = '<option value="all">All embedded datasets</option>';
  (DATA.sources || []).forEach((source) => {
    const option = document.createElement("option");
    option.value = source.key;
    option.textContent = source.label;
    controls.sourceSelect.append(option);
  });
  if (DATA.datasets.some((dataset) => dataset.source === "custom_upload")) {
    const option = document.createElement("option");
    option.value = "custom_upload";
    option.textContent = "Custom uploads";
    controls.sourceSelect.append(option);
  }
  controls.sourceSelect.value = [...controls.sourceSelect.options].some((option) => option.value === previous)
    ? previous
    : "all";
}

function rebuildDatasetOptions(preferredSlug = "") {
  const source = controls.sourceSelect.value || "all";
  const visible = DATA.datasets.filter((dataset) => source === "all" || dataset.source === source);
  controls.datasetSelect.innerHTML = "";

  visible.forEach((dataset) => {
    const option = document.createElement("option");
    option.value = dataset.slug;
    const sourcePrefix = dataset.sourceLabel ? `${dataset.sourceLabel}: ` : "";
    option.textContent = `${sourcePrefix}${dataset.title} (${dataset.selector})`;
    controls.datasetSelect.append(option);
  });

  const fallback = visible[0] || DATA.datasets[0];
  const selected = visible.find((dataset) => dataset.slug === preferredSlug) || fallback;
  if (selected) {
    controls.datasetSelect.value = selected.slug;
    setCurrentDataset(selected);
  }
}

function createProjector(width, height, settings) {
  const plot = settings.showLabels
    ? { left: 78, top: 136, right: width - 78, bottom: height - 220 }
    : { left: 58, top: 58, right: width - 58, bottom: height - 58 };
  const dx = Math.max(currentData.maxX - currentData.minX, 1e-9);
  const dy = Math.max(currentData.maxY - currentData.minY, 1e-9);
  const minX = currentData.minX - dx * 0.1;
  const maxX = currentData.maxX + dx * 0.1;
  const minY = currentData.minY - dy * 0.1;
  const maxY = currentData.maxY + dy * 0.1;
  const scale = Math.min((plot.right - plot.left) / (maxX - minX), (plot.bottom - plot.top) / (maxY - minY));
  const cxData = (minX + maxX) / 2;
  const cyData = (minY + maxY) / 2;
  const cxPix = (plot.left + plot.right) / 2;
  const cyPix = (plot.top + plot.bottom) / 2;
  return (point) => ({
    x: cxPix + (point.x - cxData) * scale,
    y: cyPix - (point.y - cyData) * scale,
  });
}

function drawLabels(ctx, width, height, settings) {
  const isDark = luminance(settings.backgroundColor) < 0.2;
  const text = isDark ? "#e5e7eb" : "#111827";
  const muted = isDark ? "#a5b4fc" : "#475569";
  ctx.fillStyle = text;
  ctx.font = "700 42px Inter, system-ui, sans-serif";
  ctx.fillText(currentData.title, 78, 66);
  ctx.fillStyle = muted;
  ctx.font = "24px Inter, system-ui, sans-serif";
  ctx.fillText(`${currentData.selector}, tc=${currentData.translations}, R=${currentData.polydiscRadius}, n=${currentData.points.toLocaleString("pt-BR")}, e=${currentData.edges.toLocaleString("pt-BR")}`, 78, 104);
  ctx.font = "20px Inter, system-ui, sans-serif";
  ctx.fillText(`Lines: ${settings.lineMode}, width ${settings.lineWidth}px, alpha ${settings.lineAlpha}; density ${settings.densityEnabled ? "on" : "off"}.`, 78, height - 78);
}

function luminance(hex) {
  const [r, g, b] = hexToRgb(hex).map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function renderToCanvas(canvas, scale = 1) {
  if (!currentData) return;
  const settings = getSettings();
  const baseWidth = 1800;
  const baseHeight = 1400;
  canvas.width = baseWidth * scale;
  canvas.height = baseHeight * scale;
  canvas.style.aspectRatio = `${baseWidth} / ${baseHeight}`;
  const ctx = canvas.getContext("2d");
  ctx.save();
  ctx.scale(scale, scale);
  ctx.fillStyle = settings.backgroundColor;
  ctx.fillRect(0, 0, baseWidth, baseHeight);
  const project = createProjector(baseWidth, baseHeight, settings);

  if (settings.showLabels) drawLabels(ctx, baseWidth, baseHeight, settings);

  if (settings.showLines) {
    drawEdges(ctx, currentData.edgesList, project, settings, false);
    if (settings.densityEnabled && settings.densityAlpha > 0) {
      drawEdges(ctx, currentData.edgesList, project, settings, true);
    }
  }

  if (settings.showPoints) {
    drawPoints(ctx, currentData.pointsList, project, settings);
  }

  ctx.restore();
  controls.renderInfo.textContent = `${canvas.width}×${canvas.height}px`;
}

function drawEdges(ctx, edges, project, settings, densityPass) {
  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.globalCompositeOperation = "source-over";
  ctx.lineWidth = densityPass ? settings.lineWidth + settings.densityWidth : settings.lineWidth;
  edges.forEach((edge) => {
    const p = project(edge.from);
    const q = project(edge.to);
    const color = generatorColor(edge.generator, settings.lineMode);
    const alpha = densityPass ? settings.densityAlpha : settings.lineAlpha;
    ctx.strokeStyle = rgba(color, alpha);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(q.x, q.y);
    ctx.stroke();
  });
  ctx.restore();
}

function drawPoints(ctx, points, project, settings) {
  ctx.save();
  points.forEach((point) => {
    const p = project(point);
    ctx.fillStyle = pointColor(point.maxEmbeddingAbs, settings.pointMode, settings.pointAlpha);
    ctx.beginPath();
    ctx.arc(p.x, p.y, settings.pointSize, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}

function queueRender() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(() => {
    renderQueued = false;
    renderToCanvas(controls.canvas, 1);
  });
}

function downloadPng() {
  const exportCanvas = document.createElement("canvas");
  const scale = Number(controls.exportScale.value);
  renderToCanvas(exportCanvas, scale);
  const link = document.createElement("a");
  link.href = exportCanvas.toDataURL("image/png");
  link.download = `${safeFilePart(currentData.slug)}_${controls.lineMode.value}_${Date.now()}.png`;
  link.click();
  renderToCanvas(controls.canvas, 1);
}

function safeFilePart(value) {
  return String(value).replace(/[^a-z0-9._-]+/gi, "_").replace(/^_+|_+$/g, "");
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (char === '"' && next === '"') {
        value += '"';
        i += 1;
      }
      else if (char === '"') {
        quoted = false;
      }
      else {
        value += char;
      }
    }
    else if (char === '"') {
      quoted = true;
    }
    else if (char === ",") {
      row.push(value);
      value = "";
    }
    else if (char === "\n") {
      row.push(value);
      rows.push(row);
      row = [];
      value = "";
    }
    else if (char !== "\r") {
      value += char;
    }
  }

  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }

  const headers = rows.shift()?.map((header) => header.trim()) || [];
  return rows
    .filter((items) => items.some((item) => item.trim().length))
    .map((items) => Object.fromEntries(headers.map((header, index) => [header, items[index] ?? ""])));
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

function numberFrom(row, names, fallback = 0) {
  for (const name of names) {
    if (row[name] !== undefined && row[name] !== "") return Number(row[name]);
  }
  return fallback;
}

async function loadCsvDataset() {
  const pointsFile = controls.pointsFile.files?.[0];
  const edgesFile = controls.edgesFile.files?.[0];
  if (!pointsFile || !edgesFile) {
    setLoadStatus("Selecione um arquivo de pontos e um arquivo de arestas.", "error");
    return;
  }

  try {
    const [pointsText, edgesText] = await Promise.all([readFileAsText(pointsFile), readFileAsText(edgesFile)]);
    const pointRows = parseCsv(pointsText);
    const edgeRows = parseCsv(edgesText);
    if (!pointRows.length || !edgeRows.length) {
      throw new Error("CSV vazio ou sem linhas de dados.");
    }

    const points = pointRows.map((row, index) => [
      Number.isFinite(numberFrom(row, ["id"], NaN)) ? numberFrom(row, ["id"]) : index,
      numberFrom(row, ["x", "X", "re", "real"]),
      numberFrom(row, ["y", "Y", "im", "imag"]),
      numberFrom(row, ["max_embedding_abs", "maxEmbeddingAbs", "principal_abs"], 0),
    ]);

    const ids = new Set(points.map((point) => point[0]));
    const edges = edgeRows
      .map((row) => [
        numberFrom(row, ["from_id", "fromId", "source", "from"]),
        numberFrom(row, ["to_id", "toId", "target", "to"]),
        numberFrom(row, ["changed_generator", "generator", "u", "gen"], 0),
      ])
      .filter(([fromId, toId]) => ids.has(fromId) && ids.has(toId));

    if (!edges.length) {
      throw new Error("Nenhuma aresta referencia ids existentes no CSV de pontos.");
    }

    customDatasetCounter += 1;
    const baseName = pointsFile.name.replace(/_points\.csv$/i, "").replace(/\.csv$/i, "");
    const dataset = {
      slug: `custom_upload:${customDatasetCounter}_${safeFilePart(baseName)}`,
      originalSlug: baseName,
      source: "custom_upload",
      sourceLabel: "Custom uploads",
      title: `Custom: ${baseName}`,
      selector: "uploaded_csv",
      translations: Math.max(...edges.map((edge) => edge[2])) + 1,
      polydiscRadius: "n/a",
      points: points.length,
      edges: edges.length,
      ratioVsGrid: NaN,
      notes: `Loaded from ${pointsFile.name} and ${edgesFile.name}`,
      pointRows: points,
      edgeRows: edges,
    };

    DATA.datasets.push(dataset);
    rebuildSourceOptions();
    controls.sourceSelect.value = "custom_upload";
    rebuildDatasetOptions(dataset.slug);
    setLoadStatus(`Dataset carregado: ${points.length.toLocaleString("pt-BR")} pontos, ${edges.length.toLocaleString("pt-BR")} arestas.`, "ok");
  }
  catch (error) {
    setLoadStatus(error.message || String(error), "error");
  }
}

function setLoadStatus(message, state = "") {
  controls.loadStatus.textContent = message;
  controls.loadStatus.dataset.state = state;
}

function init() {
  rebuildSourceOptions();

  const defaultDataset =
    DATA.datasets.find((dataset) => dataset.originalSlug === "04_regular10_balanced")
    || DATA.datasets.find((dataset) => dataset.slug.includes("04_regular10_balanced"))
    || DATA.datasets.find((dataset) => dataset.originalSlug === "05_random_representative")
    || DATA.datasets.find((dataset) => dataset.slug.includes("05_random_representative"))
    || DATA.datasets[0];

  setSettings(PRESETS.blueprint);
  rebuildDatasetOptions(defaultDataset?.slug);

  Object.values(controls).forEach((control) => {
    if (!(control instanceof HTMLElement)) return;
    if (["INPUT", "SELECT"].includes(control.tagName)) {
      control.addEventListener("input", () => {
        updateOutputs();
        queueRender();
      });
    }
  });

  ["lineHue", "lineSaturation", "lineLightness"].forEach((id) => {
    controls[id].addEventListener("input", () => {
      controls.lineMode.value = "custom";
      queueRender();
    });
  });

  ["pointHue", "pointSaturation", "pointLightness"].forEach((id) => {
    controls[id].addEventListener("input", () => {
      controls.pointMode.value = "custom";
      queueRender();
    });
  });

  controls.sourceSelect.addEventListener("change", () => rebuildDatasetOptions(controls.datasetSelect.value));
  controls.datasetSelect.addEventListener("change", () => setDataset(controls.datasetSelect.value));
  controls.loadCsvDataset.addEventListener("click", loadCsvDataset);
  controls.downloadPng.addEventListener("click", downloadPng);
  controls.resetView.addEventListener("click", () => setSettings(PRESETS.blueprint));
  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => setSettings(PRESETS[button.dataset.preset]));
  });
  updateOutputs();
}

init();
