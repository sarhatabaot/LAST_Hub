const POLL_INTERVAL_MS = 5000;
const API_URL = "/hub/safety/api/";

function getInitialPayload() {
  const node = document.getElementById("safety-data");
  if (!node) return null;
  try {
    return JSON.parse(node.textContent || "null");
  } catch {
    return null;
  }
}

function fmtNumber(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 100) return value.toFixed(0);
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

function fmtValue(metric) {
  const num = fmtNumber(metric.value);
  return metric.unit ? `${num} ${metric.unit}` : num;
}

// Operator from the API encodes the FAIL condition (e.g. `>` means "fails when
// value > threshold"). For display + bar highlighting we want the OK condition,
// which is the inverse.
function okOperatorSymbol(failOp) {
  switch ((failOp || "").trim()) {
    case ">": return "≤";
    case ">=": return "<";
    case "<": return "≥";
    case "<=": return ">";
    default: return "≤";
  }
}

function fmtLimit(metric) {
  const unit = metric.unit ? ` ${metric.unit}` : "";
  if (metric.range_min != null && metric.range_max != null) {
    return `${fmtNumber(metric.range_min)} – ${fmtNumber(metric.range_max)}${unit}`;
  }
  if (metric.threshold != null) {
    return `${okOperatorSymbol(metric.operator)} ${fmtNumber(metric.threshold)}${unit}`;
  }
  return "";
}

const CARDINAL_16 = [
  "N", "NNE", "NE", "ENE",
  "E", "ESE", "SE", "SSE",
  "S", "SSW", "SW", "WSW",
  "W", "WNW", "NW", "NNW",
];

function cardinalOf(deg) {
  if (typeof deg !== "number" || !Number.isFinite(deg)) return "";
  const normalized = ((deg % 360) + 360) % 360;
  return CARDINAL_16[Math.round(normalized / 22.5) % 16];
}

function isWindDirection(metric) {
  const key = (metric.key || "").toLowerCase();
  const unit = (metric.unit || "").toLowerCase();
  const looksDeg = unit === "deg" || unit === "degrees" || unit === "°";
  return /wind.*dir|wind_?dir/.test(key) || (key.includes("wind") && looksDeg);
}

function isWindSpeed(metric) {
  return classifyWind(metric) !== null && classifyWind(metric) !== "dir";
}

// Classify a wind-related metric. Returns one of:
//   "dir" | "speed" | "max" | "min" | "std" | "mean" | "gust"
// or null if the metric isn't wind-related at all. Order matters — std is
// checked before max so a key like "wind_std_max" still classifies as std.
function classifyWind(metric) {
  if (isWindDirection(metric)) return "dir";
  // Normalize separators to spaces so word-boundary regexes work on snake_case
  // and kebab-case keys (`wind_max` → `wind max` → `\bmax\b` matches).
  const text = `${metric.key || ""} ${metric.label || ""}`
    .toLowerCase()
    .replace(/[_-]/g, " ");
  if (!/wind/.test(text)) return null;
  if (/\b(std|stdev|sigma)\b/.test(text)) return "std";
  if (/\bgust\b/.test(text)) return "gust";
  if (/\b(mean|avg|average)\b/.test(text)) return "mean";
  if (/\b(min|minimum)\b/.test(text)) return "min";
  if (/\b(max|maximum)\b/.test(text)) return "max";
  return "speed";
}

// Fixed source universe — the filter row always shows these chips so users see
// the available filters even when no metric currently matches a source.
const KNOWN_SOURCES = [
  "ims232",
  "outside arduino",
  "inside arduino",
  "davis",
  "sun",
  "home front command",
];

// Without an upstream `source` field we infer source from the metric key.
// Easy to swap to `metric.source` once the safety API exposes one.
const SOURCE_RULES = [
  { match: /ims/i, source: "ims232" },
  { match: /sun|solar|daylight|altitude/i, source: "sun" },
  { match: /hfc|home_?front|red_?alert/i, source: "home front command" },
  { match: /outdoor|outside|exterior/i, source: "outside arduino" },
  { match: /indoor|inside|interior/i, source: "inside arduino" },
  { match: /davis|wind|temp|humid|rh|press|baro|rain/i, source: "davis" },
];

function inferSource(metric) {
  const text = `${metric.key || ""} ${metric.label || ""}`.toLowerCase();
  for (const rule of SOURCE_RULES) {
    if (rule.match.test(text)) return rule.source;
  }
  return "davis";
}

function presetRange(preset) {
  const to = new Date();
  let hours;
  switch (preset) {
    case "6h": hours = 6; break;
    case "24h": hours = 24; break;
    case "3d": hours = 72; break;
    case "1w": hours = 168; break;
    case "1m": hours = 720; break;
    default: hours = 1; break;
  }
  const from = new Date(to.getTime() - hours * 3600 * 1000);
  return { from, to, preset };
}

let activeSources = null; // null = all
let activeRange = presetRange("1h");
let lastPayload = null;

function passesSourceFilter(metric) {
  if (activeSources == null) return true;
  return activeSources.has(inferSource(metric));
}

// Returns true when the value satisfies the metric's OK condition (the inverse
// of the API's FAIL operator). Mirrors the bar logic in computeBar.
function passesThreshold(value, metric) {
  const t = typeof metric.threshold === "number" ? metric.threshold : null;
  const rmin = typeof metric.range_min === "number" ? metric.range_min : null;
  const rmax = typeof metric.range_max === "number" ? metric.range_max : null;
  if (rmin != null && rmax != null) return value >= rmin && value <= rmax;
  if (t == null) return true;
  switch ((metric.operator || "").trim()) {
    case ">": return value <= t;
    case ">=": return value < t;
    case "<": return value >= t;
    case "<=": return value > t;
    default: return true;
  }
}

function compassSvg(bearingDeg) {
  // 16 small ticks every 22.5°. The needle's "from" arm points to the bearing
  // (where the wind is coming from, the standard meteorological convention);
  // its "to" arm sits opposite as a counterweight.
  const ticks = Array.from({ length: 16 }, (_, i) => {
    const major = i % 4 === 0;
    const len = major ? 6 : 3;
    const angle = (i * 22.5 - 90) * (Math.PI / 180);
    const x1 = 50 + Math.cos(angle) * 44;
    const y1 = 50 + Math.sin(angle) * 44;
    const x2 = 50 + Math.cos(angle) * (44 - len);
    const y2 = 50 + Math.sin(angle) * (44 - len);
    return `<line class="safety-compass-tick${major ? " is-major" : ""}" x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}" />`;
  }).join("");
  return `
    <svg class="safety-compass-svg" viewBox="0 0 100 100" aria-hidden="true">
      <circle class="safety-compass-ring" cx="50" cy="50" r="44" />
      ${ticks}
      <text class="safety-compass-cardinal" x="50" y="13">N</text>
      <text class="safety-compass-cardinal" x="87" y="53">E</text>
      <text class="safety-compass-cardinal" x="50" y="93">S</text>
      <text class="safety-compass-cardinal" x="13" y="53">W</text>
      <g class="safety-compass-needle" style="transform: rotate(${bearingDeg}deg)">
        <path class="safety-compass-needle-from" d="M50 14 L45 50 L55 50 Z" />
        <path class="safety-compass-needle-to" d="M50 86 L45 50 L55 50 Z" />
        <circle class="safety-compass-hub" cx="50" cy="50" r="3.2" />
      </g>
    </svg>
  `;
}

function fmtTimestamp(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

function computeBar(metric) {
  const value = metric.value;
  if (typeof value !== "number" || !Number.isFinite(value)) return null;

  const threshold = typeof metric.threshold === "number" && Number.isFinite(metric.threshold)
    ? metric.threshold : null;
  const rangeMin = typeof metric.range_min === "number" && Number.isFinite(metric.range_min)
    ? metric.range_min : null;
  const rangeMax = typeof metric.range_max === "number" && Number.isFinite(metric.range_max)
    ? metric.range_max : null;
  const operator = (metric.operator || "").trim();
  const hasRange = rangeMin != null && rangeMax != null;
  const hasThreshold = threshold != null;
  if (!hasRange && !hasThreshold) return null;

  let lo = value;
  let hi = value;
  if (hasRange) { lo = Math.min(lo, rangeMin); hi = Math.max(hi, rangeMax); }
  if (hasThreshold) { lo = Math.min(lo, threshold); hi = Math.max(hi, threshold); }

  let pad = (hi - lo) * 0.18;
  if (!Number.isFinite(pad) || pad <= 0) {
    pad = Math.max(Math.abs(hi || lo || 1) * 0.2, 1);
  }
  lo -= pad;
  hi += pad;
  const span = Math.max(hi - lo, 1);
  const pct = (v) => clamp(((v - lo) / span) * 100, 0, 100);

  let allowedStart = 0;
  let allowedEnd = 100;
  if (hasRange) {
    allowedStart = pct(rangeMin);
    allowedEnd = pct(rangeMax);
  } else if (operator === ">" || operator === ">=") {
    // fail when value > threshold → OK below threshold (left)
    allowedEnd = pct(threshold);
  } else if (operator === "<" || operator === "<=") {
    // fail when value < threshold → OK above threshold (right)
    allowedStart = pct(threshold);
  } else if (hasThreshold) {
    // Unknown operator: infer side from current state
    const t = pct(threshold);
    if (metric._state === "failed") {
      if (value > threshold) { allowedEnd = t; } else { allowedStart = t; }
    } else {
      if (value <= threshold) { allowedEnd = t; } else { allowedStart = t; }
    }
  }

  return { current: pct(value), allowedStart, allowedEnd };
}

function renderStatusCard(payload) {
  const card = document.getElementById("safetyStatusCard");
  const title = document.getElementById("safetyStatusTitle");
  const evaluated = document.getElementById("safetyEvaluatedAt");
  if (!card || !title) return;

  let stateClass = "safety-card-unknown";
  let label = "UNKNOWN";
  if (payload.safe === true) {
    stateClass = "safety-card-safe";
    label = "SAFE";
  } else if (payload.safe === false) {
    stateClass = "safety-card-unsafe";
    label = "UNSAFE";
  }

  card.className = `safety-card ${stateClass}`;
  title.textContent = label;
  title.className = `safety-status-title${payload.safe == null ? "" : " safety-status-title-contrast"}`;

  if (evaluated) {
    if (payload.evaluated_at) {
      evaluated.textContent = `Evaluated at ${fmtTimestamp(payload.evaluated_at)}`;
      evaluated.classList.toggle("safety-status-title-contrast", payload.safe != null);
    } else {
      evaluated.textContent = "";
    }
  }
}

function renderError(payload) {
  const el = document.getElementById("safetyError");
  if (!el) return;
  if (payload.error) {
    el.hidden = false;
    el.textContent = payload.error;
  } else {
    el.hidden = true;
    el.textContent = "";
  }
}

function renderMetrics(payload) {
  const grid = document.getElementById("safetyMetricsGrid");
  if (!grid) return;

  const failed = (payload.failed_reason_metrics || []).map((m) => ({ ...m, _state: "failed" }));
  const passed = (payload.passed_reason_metrics || []).map((m) => ({ ...m, _state: "passed" }));
  const stale = (payload.stale_sensors || []).map((entry) => ({
    label: typeof entry === "string" ? entry : (entry?.label || entry?.name || "Sensor"),
    _state: "stale",
  }));
  let metrics = [...failed, ...stale, ...passed];

  // Source filter only applies to the value-bearing metrics; stale entries
  // pass through so operators always see them.
  metrics = metrics.filter((m) => m._state === "stale" || passesSourceFilter(m));

  // Group wind metrics by source so each device gets its own tile. Each entry
  // stores per-kind slots (speed, max, min, std, avg, gust, dir). State is
  // derived from any non-direction wind metric of the source.
  const windBySource = new Map();
  const remaining = [];
  for (const m of metrics) {
    if (m._state === "stale") {
      remaining.push(m);
      continue;
    }
    const kind = classifyWind(m);
    if (!kind) {
      remaining.push(m);
      continue;
    }
    const src = inferSource(m);
    let entry = windBySource.get(src);
    if (!entry) {
      entry = { source: src };
      windBySource.set(src, entry);
    }
    if (entry[kind]) {
      // Already filled this slot — fall back to the regular grid for the dup.
      remaining.push(m);
    } else {
      entry[kind] = m;
    }
  }

  grid.innerHTML = "";

  for (const entry of windBySource.values()) {
    grid.appendChild(renderWindCard(entry));
  }

  if (!remaining.length && !windBySource.size) {
    return;
  }

  for (const metric of remaining) {
    const card = document.createElement("article");
    card.className = `safety-metric is-${metric._state}`;
    card.dataset.detailKind = "metric";
    card._metric = metric;
    const label = metric.label || metric.key || "Sensor";
    const isStale = metric._state === "stale";
    const stateLabel = isStale ? "STALE" : (metric._state === "failed" ? "FAIL" : "OK");

    const limit = isStale ? "" : fmtLimit(metric);
    const valueText = isStale ? "—" : fmtValue(metric);
    card.setAttribute(
      "aria-label",
      isStale
        ? `${label} stale: no recent data`
        : `${label} ${stateLabel}: ${valueText}${limit ? `, limit ${limit}` : ""}`,
    );
    const bar = isStale ? null : computeBar(metric);
    const barHtml = bar
      ? `<div class="safety-metric-bar" aria-hidden="true">
           <span class="safety-metric-bar-range" style="left:${bar.allowedStart}%;width:${Math.max(bar.allowedEnd - bar.allowedStart, 0)}%"></span>
           <span class="safety-metric-bar-marker" style="left:${bar.current}%"></span>
         </div>`
      : `<div class="safety-metric-bar safety-metric-bar-empty" aria-hidden="true"></div>`;
    const limitLine = isStale
      ? "No recent data"
      : (limit ? `Limit ${limit}` : "&nbsp;");
    card.innerHTML = `
      <header class="safety-metric-head">
        <span class="safety-metric-label" title="${label}">${label}</span>
        <span class="safety-metric-state">${stateLabel}</span>
      </header>
      <p class="safety-metric-value">${valueText}</p>
      ${barHtml}
      <p class="safety-metric-limit">${limitLine}</p>
    `;
    grid.appendChild(card);
  }
}

function renderWindCard(entry) {
  const { source, dir } = entry;
  // Treat a plain `wind_speed` metric as the mean reading when no explicit
  // mean is reported, so a source that only exposes "speed" still has a
  // labeled row.
  const meanMetric = entry.mean || entry.speed || null;
  const rows = [
    ["mean", meanMetric],
    ["max", entry.max],
    ["min", entry.min],
    ["σ", entry.std],
    ["gust", entry.gust],
  ].filter(([, m]) => m);

  const allSpeed = rows.map(([, m]) => m);
  const states = allSpeed.map((m) => m._state);
  const state = states.includes("failed")
    ? "failed"
    : states.includes("stale")
      ? "stale"
      : "passed";
  const stateLabel = state === "failed" ? "FAIL" : state === "stale" ? "STALE" : "OK";

  const card = document.createElement("article");
  card.className = `safety-metric is-${state} safety-metric-wind-card`;
  card.dataset.detailKind = "wind-source";

  const bearing = dir && Number.isFinite(dir.value)
    ? ((dir.value % 360) + 360) % 360
    : null;
  const cardinal = bearing != null ? cardinalOf(bearing) : "";
  const signedDeg = bearing != null ? (bearing > 180 ? bearing - 360 : bearing) : null;
  const dirText = signedDeg != null ? `${Math.round(signedDeg)}° ${cardinal}` : "—";

  const rowsHtml = rows
    .map(([label, m]) => {
      const value = Number.isFinite(m.value) ? fmtNumber(m.value) : "—";
      const unit = m.unit || "km/h";
      const cls = m._state === "failed" ? " is-failed" : "";
      return `<li class="safety-wind-stat-row${cls}">
        <span class="safety-wind-stat-label">${label}</span>
        <span class="safety-wind-stat-value">${value}<span class="safety-wind-stat-unit">${unit}</span></span>
      </li>`;
    })
    .join("");

  card.setAttribute(
    "aria-label",
    `Wind ${source} ${stateLabel}: ${rows.length} readings from ${dirText}`,
  );
  card.innerHTML = `
    <header class="safety-metric-head">
      <span class="safety-metric-label" title="Wind · ${source}">Wind · ${source}</span>
      <span class="safety-metric-state">${stateLabel}</span>
    </header>
    <div class="safety-metric-wind-body">
      <div class="safety-metric-wind-compass">
        ${bearing != null ? compassSvg(bearing) : ""}
        <span class="safety-metric-wind-dir">${dirText}</span>
      </div>
      <ul class="safety-wind-stats-list">${rowsHtml || `<li class="safety-wind-stat-row safety-wind-stat-empty">no wind speed</li>`}</ul>
    </div>
  `;
  card._windPayload = entry;
  return card;
}

function renderSourceFilter() {
  const host = document.getElementById("safetySourceFilter");
  if (!host) return;

  host.innerHTML = "";

  const allChip = document.createElement("button");
  allChip.type = "button";
  allChip.className = "safety-filter-chip" + (activeSources == null ? " is-active" : "");
  allChip.textContent = "All";
  allChip.addEventListener("click", () => {
    activeSources = null;
    rerender();
  });
  host.appendChild(allChip);

  for (const src of KNOWN_SOURCES) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "safety-filter-chip"
      + (activeSources && activeSources.has(src) ? " is-active" : "");
    chip.textContent = src;
    chip.addEventListener("click", () => {
      if (activeSources == null) activeSources = new Set();
      if (activeSources.has(src)) activeSources.delete(src);
      else activeSources.add(src);
      if (activeSources.size === 0) activeSources = null;
      rerender();
    });
    host.appendChild(chip);
  }
}

function pointsForActiveRange() {
  const ms = activeRange.to.getTime() - activeRange.from.getTime();
  if (!Number.isFinite(ms) || ms <= 0) return 60;
  const hours = ms / (3600 * 1000);
  if (hours <= 1) return 60;
  if (hours <= 6) return 100;
  if (hours <= 24) return 150;
  if (hours <= 72) return 200;
  if (hours <= 168) return 240;
  return 300;
}

// Random walk anchored on the current value, with occasional excursions so the
// sample charts show some red segments. Replace with real time-series once the
// DB-backed history endpoint exists.
function generateHistorySeries(metric, points) {
  const v = Number(metric.value);
  const t = typeof metric.threshold === "number" ? metric.threshold : null;
  const span = (metric.range_min != null && metric.range_max != null)
    ? metric.range_max - metric.range_min
    : (t != null ? Math.abs(t * 0.4) : Math.abs(v) * 0.25 || 1);
  const step = span * 0.04;

  const seed = (Math.abs(hashKey(metric.key || metric.label || "x")) % 10000) / 10000;
  let cur = v;
  const arr = [];
  for (let i = 0; i < points; i++) {
    cur += (rand(seed + i * 0.137) - 0.5) * step;
    if (rand(seed + i * 0.91) < 0.04) {
      cur += (rand(seed + i * 0.31) - 0.5) * span * 0.9;
    }
    arr.push(cur);
  }
  return arr;
}

function rand(seed) {
  // Deterministic pseudo-random in [0, 1) — keeps the placeholder series
  // stable between re-renders so the user sees the same chart, not a flicker.
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
}

function hashKey(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  return h;
}

function fmtAxisTime(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
  const hours = (activeRange.to.getTime() - activeRange.from.getTime()) / 3600000;
  if (hours > 48) {
    return date.toLocaleDateString([], { month: "short", day: "2-digit" });
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtTooltipTime(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function timeAtIndex(idx, total) {
  if (total <= 1) return new Date(activeRange.to);
  const fromMs = activeRange.from.getTime();
  const toMs = activeRange.to.getTime();
  return new Date(fromMs + (idx / (total - 1)) * (toMs - fromMs));
}

function chartLayout(series, metric, opts) {
  const W = opts.width || 240;
  const H = opts.height || 80;
  const pad = opts.pad || { top: 6, right: 6, bottom: 14, left: 30 };

  let lo = Math.min(...series);
  let hi = Math.max(...series);
  if (metric.range_min != null) lo = Math.min(lo, metric.range_min);
  if (metric.range_max != null) hi = Math.max(hi, metric.range_max);
  if (typeof metric.threshold === "number") {
    lo = Math.min(lo, metric.threshold);
    hi = Math.max(hi, metric.threshold);
  }
  const span = Math.max(hi - lo, 1e-6);
  const innerW = W - pad.left - pad.right;
  const innerH = H - pad.top - pad.bottom;
  const x = (i) => pad.left + (i / (series.length - 1)) * innerW;
  const y = (v) => pad.top + innerH - ((v - lo) / span) * innerH;
  return { W, H, pad, lo, hi, span, x, y };
}

function historySvg(series, metric, opts = {}) {
  const layout = chartLayout(series, metric, opts);
  const { W, H, pad, lo, hi, x, y } = layout;
  const unit = metric.unit ? ` ${metric.unit}` : "";

  let segs = "";
  for (let i = 1; i < series.length; i++) {
    const passL = passesThreshold(series[i - 1], metric);
    const passR = passesThreshold(series[i], metric);
    let stroke = "var(--safety-history-pass, #16a34a)";
    if (!passL && !passR) stroke = "var(--safety-history-fail, #dc2626)";
    else if (passL !== passR) stroke = "var(--safety-history-edge, #d97706)";
    segs += `<line x1="${x(i - 1).toFixed(2)}" y1="${y(series[i - 1]).toFixed(2)}" x2="${x(i).toFixed(2)}" y2="${y(series[i]).toFixed(2)}" stroke="${stroke}" stroke-width="1.6" stroke-linecap="round"/>`;
  }

  let limitLines = "";
  if (typeof metric.threshold === "number") {
    const ty = y(metric.threshold).toFixed(2);
    limitLines += `<line x1="${pad.left}" y1="${ty}" x2="${W - pad.right}" y2="${ty}" stroke="currentColor" stroke-width="1" stroke-dasharray="3 3" opacity="0.35"/>`;
  }

  // Axis labels: y min/max on the left, x from/to at the bottom.
  const labels = `
    <text class="safety-history-axis" x="${pad.left - 3}" y="${pad.top + 3.5}" text-anchor="end">${fmtNumber(hi)}${unit}</text>
    <text class="safety-history-axis" x="${pad.left - 3}" y="${H - pad.bottom + 1}" text-anchor="end">${fmtNumber(lo)}${unit}</text>
    <text class="safety-history-axis" x="${pad.left}" y="${H - 2}">${fmtAxisTime(activeRange.from)}</text>
    <text class="safety-history-axis" x="${W - pad.right}" y="${H - 2}" text-anchor="end">${fmtAxisTime(activeRange.to)}</text>
  `;

  // Cursor + dot, hidden by default. Updated on hover by the global handler.
  const cursor = `
    <line class="safety-history-cursor" x1="0" y1="${pad.top}" x2="0" y2="${H - pad.bottom}" stroke="currentColor" stroke-width="0.6" opacity="0"/>
    <circle class="safety-history-cursor-dot" cx="0" cy="0" r="2.4" fill="currentColor" stroke="var(--hub-surface)" stroke-width="1" opacity="0"/>
  `;

  return `<svg class="safety-history-chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${limitLines}${segs}${labels}${cursor}</svg>`;
}

function renderHistory(payload) {
  const section = document.getElementById("safetyHistorySection");
  if (!section) return;
  const grid = section.querySelector(".safety-history-grid");
  if (!grid) return;

  const metrics = [
    ...(payload.failed_reason_metrics || []).map((m) => ({ ...m, _state: "failed" })),
    ...(payload.passed_reason_metrics || []).map((m) => ({ ...m, _state: "passed" })),
  ].filter((m) => Number.isFinite(m.value) && passesSourceFilter(m));

  grid.innerHTML = "";
  if (!metrics.length) {
    const empty = document.createElement("p");
    empty.className = "operations-note";
    empty.textContent = "No sensors match the current filter.";
    grid.appendChild(empty);
    return;
  }

  const points = pointsForActiveRange();
  for (const metric of metrics) {
    grid.appendChild(buildHistoryCard(metric, points, { width: 240, height: 80 }));
  }
}

function buildHistoryCard(metric, points, opts) {
  const series = generateHistorySeries(metric, points);
  const card = document.createElement("article");
  card.className = "safety-history-card safety-history-target";
  const label = metric.label || metric.key || "Sensor";
  card.innerHTML = `
    <header class="safety-history-head">
      <span class="safety-history-label">${label}</span>
      <span class="safety-history-source">${inferSource(metric)}</span>
    </header>
    ${historySvg(series, metric, opts)}
  `;
  card._chartSeries = series;
  card._chartMetric = metric;
  card._chartLayout = chartLayout(series, metric, opts);
  return card;
}

function rerender() {
  if (lastPayload) render(lastPayload);
}

function metricStateBadge(metric) {
  const isStale = metric._state === "stale";
  const stateLabel = isStale ? "STALE" : (metric._state === "failed" ? "FAIL" : "OK");
  return `<span class="safety-dialog-state safety-dialog-state-${metric._state}">${stateLabel}</span>`;
}

function metricSettingsBlock(metric) {
  const limit = fmtLimit(metric);
  const source = inferSource(metric);
  const rows = [
    ["State", `${metricStateBadge(metric)}`],
    ["Source", source],
    ["Threshold", limit || "—"],
    ["FAIL when value", metric.operator || "—"],
  ];
  if (metric.range_min != null && metric.range_max != null) {
    rows.push(["Allowed range", `${fmtNumber(metric.range_min)} – ${fmtNumber(metric.range_max)}${metric.unit ? ` ${metric.unit}` : ""}`]);
  }
  if (metric.raw_reason) {
    rows.push(["Reason", metric.raw_reason]);
  }
  return `<dl class="safety-dialog-settings">
    ${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}
  </dl>`;
}

function metricLiveBlock(metric) {
  const isStale = metric._state === "stale";
  const valueText = isStale ? "—" : fmtValue(metric);
  return `
    <section class="safety-dialog-live">
      <p class="safety-dialog-value">${valueText}</p>
      <p class="safety-dialog-meta">
        ${metric.label || metric.key || "Sensor"}
        ${metric._state ? ` · ${metricStateBadge(metric)}` : ""}
      </p>
    </section>
  `;
}

function metricHistoryBlock(metric) {
  if (metric._state === "stale" || !Number.isFinite(metric.value)) {
    return `<section class="safety-dialog-history"><p class="operations-note">No history sample available.</p></section>`;
  }
  const opts = { width: 520, height: 180, pad: { top: 8, right: 8, bottom: 18, left: 38 } };
  const points = pointsForActiveRange();
  const series = generateHistorySeries(metric, points);
  const layout = chartLayout(series, metric, opts);
  // Stash on a fresh data-id so the dialog can be wired up after innerHTML.
  const id = `sd${(Math.random() * 1e9) | 0}`;
  pendingDialogCharts.push({ id, series, metric, layout });
  return `<section class="safety-dialog-history" data-history-target-id="${id}">
    <h3>History <span class="safety-history-tag">sample</span></h3>
    ${historySvg(series, metric, opts)}
  </section>`;
}

const pendingDialogCharts = [];

function flushDialogChartTargets(root) {
  for (const entry of pendingDialogCharts) {
    const node = root.querySelector(`[data-history-target-id="${entry.id}"]`);
    if (!node) continue;
    node.classList.add("safety-history-target");
    node._chartSeries = entry.series;
    node._chartMetric = entry.metric;
    node._chartLayout = entry.layout;
  }
  pendingDialogCharts.length = 0;
}

function openMetricDialog(metric) {
  const dialog = document.getElementById("safetyMetricDialog");
  if (!dialog) return;
  const titleEl = dialog.querySelector("[data-dialog-title]");
  const bodyEl = dialog.querySelector("[data-dialog-body]");
  if (!titleEl || !bodyEl) return;

  titleEl.textContent = metric.label || metric.key || "Sensor";
  bodyEl.innerHTML = `
    ${metricLiveBlock(metric)}
    ${metricHistoryBlock(metric)}
    <section class="safety-dialog-settings-section">
      <h3>Settings &amp; thresholds</h3>
      ${metricSettingsBlock(metric)}
    </section>
  `;
  flushDialogChartTargets(bodyEl);
  dialog.showModal();
}

function openWindDialog(payload) {
  const { dir, speeds, title } = payload;
  const dialog = document.getElementById("safetyMetricDialog");
  if (!dialog) return;
  const titleEl = dialog.querySelector("[data-dialog-title]");
  const bodyEl = dialog.querySelector("[data-dialog-body]");
  if (!titleEl || !bodyEl) return;

  titleEl.textContent = title || "Wind";

  const bearing = dir && Number.isFinite(dir.value)
    ? ((dir.value % 360) + 360) % 360
    : null;
  const cardinal = bearing != null ? cardinalOf(bearing) : "";
  const signedDeg = bearing != null ? (bearing > 180 ? bearing - 360 : bearing) : null;
  const dirText = signedDeg != null ? `${Math.round(signedDeg)}° ${cardinal}` : "—";

  const speedSections = speeds.length
    ? speeds.map((s) => `
        <section class="safety-dialog-wind-source">
          <header>
            <h3>${s.label || s.key} <span class="safety-history-source">${inferSource(s)}</span></h3>
            ${metricStateBadge(s)}
          </header>
          ${metricLiveBlock(s)}
          ${metricHistoryBlock(s)}
          ${metricSettingsBlock(s)}
        </section>
      `).join("")
    : `<p class="operations-note">No wind speed sensors reporting.</p>`;

  bodyEl.innerHTML = `
    <section class="safety-dialog-wind-direction">
      <div class="safety-metric-wind-compass">${bearing != null ? compassSvg(bearing) : ""}</div>
      <div>
        <p class="safety-dialog-value">${dirText}</p>
        <p class="safety-dialog-meta">Direction is informational only — does not affect SAFE / UNSAFE state.</p>
      </div>
    </section>
    ${speedSections}
  `;
  flushDialogChartTargets(bodyEl);
  dialog.showModal();
}

document.addEventListener("click", (event) => {
  const close = event.target.closest("[data-dialog-close]");
  if (close) {
    const d = document.getElementById("safetyMetricDialog");
    if (d) d.close();
    return;
  }
  const dialog = document.getElementById("safetyMetricDialog");
  if (dialog && event.target === dialog) {
    dialog.close();
    return;
  }
  const card = event.target.closest("[data-detail-kind]");
  if (!card) return;
  if (card.dataset.detailKind === "wind-source" && card._windPayload) {
    const e = card._windPayload;
    const meanLike = e.mean || e.speed;
    const speeds = [meanLike, e.max, e.min, e.std, e.gust].filter(Boolean);
    openWindDialog({ title: `Wind · ${e.source}`, dir: e.dir, speeds });
  } else if (card.dataset.detailKind === "metric" && card._metric) {
    openMetricDialog(card._metric);
  }
});

function fitMetricLabels() {
  const labels = document.querySelectorAll(".safety-metric-label");
  // Shrink as small as needed so labels never clip. 7px is a hard floor for
  // legibility; below that the text is small but still fully visible, which
  // beats hiding part of it.
  const minPx = 7;
  for (const label of labels) {
    label.style.fontSize = "";
    let fontPx = parseFloat(getComputedStyle(label).fontSize);
    let safety = 40;
    while (label.scrollHeight > label.clientHeight + 1 && fontPx > minPx && safety-- > 0) {
      fontPx -= 0.5;
      label.style.fontSize = `${fontPx}px`;
    }
  }
}

function render(payload) {
  if (!payload) return;
  lastPayload = payload;
  renderStatusCard(payload);
  renderError(payload);
  renderSourceFilter();
  renderMetrics(payload);
  renderHistory(payload);
  syncRangeUi();
  requestAnimationFrame(fitMetricLabels);
}

function toLocalDatetimeValue(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
  const tz = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - tz).toISOString().slice(0, 16);
}

function syncRangeUi() {
  const chips = document.querySelectorAll(".safety-range-chip");
  chips.forEach((c) =>
    c.classList.toggle("is-active", c.dataset.range === activeRange.preset),
  );
  const fromEl = document.querySelector("[data-range-from]");
  const toEl = document.querySelector("[data-range-to]");
  if (fromEl) fromEl.value = toLocalDatetimeValue(activeRange.from);
  if (toEl) toEl.value = toLocalDatetimeValue(activeRange.to);
}

document.addEventListener("click", (event) => {
  const chip = event.target.closest(".safety-range-chip");
  if (!chip) return;
  const range = chip.dataset.range;
  if (!range) return;
  activeRange = presetRange(range);
  syncRangeUi();
  rerender();
});

function ensureChartTooltip() {
  let el = document.getElementById("safetyChartTooltip");
  if (!el) {
    el = document.createElement("div");
    el.id = "safetyChartTooltip";
    el.className = "safety-history-tooltip";
    el.hidden = true;
    document.body.appendChild(el);
  }
  return el;
}

function clearChartHover(target) {
  if (!target) return;
  const svg = target.querySelector(".safety-history-chart");
  if (!svg) return;
  const cursor = svg.querySelector(".safety-history-cursor");
  const dot = svg.querySelector(".safety-history-cursor-dot");
  if (cursor) cursor.setAttribute("opacity", "0");
  if (dot) dot.setAttribute("opacity", "0");
}

document.addEventListener("mousemove", (event) => {
  const tooltip = ensureChartTooltip();
  const target = event.target.closest(".safety-history-target");
  if (!target || !target._chartSeries || !target._chartLayout) {
    tooltip.hidden = true;
    document.querySelectorAll(".safety-history-target").forEach(clearChartHover);
    return;
  }

  const svg = target.querySelector(".safety-history-chart");
  if (!svg) return;
  const rect = svg.getBoundingClientRect();
  const layout = target._chartLayout;
  const series = target._chartSeries;
  const metric = target._chartMetric;

  // Convert mouse x in css pixels to viewBox coordinates so the cursor lines
  // up regardless of how the SVG was scaled by CSS.
  const mouseX = event.clientX - rect.left;
  const ratio = clamp(mouseX / rect.width, 0, 1);
  const idx = Math.round(ratio * (series.length - 1));
  const value = series[idx];
  const time = timeAtIndex(idx, series.length);
  const passed = passesThreshold(value, metric);

  const cx = layout.x(idx);
  const cy = layout.y(value);
  const cursor = svg.querySelector(".safety-history-cursor");
  const dot = svg.querySelector(".safety-history-cursor-dot");
  if (cursor) {
    cursor.setAttribute("x1", cx.toFixed(2));
    cursor.setAttribute("x2", cx.toFixed(2));
    cursor.setAttribute("opacity", "0.4");
  }
  if (dot) {
    dot.setAttribute("cx", cx.toFixed(2));
    dot.setAttribute("cy", cy.toFixed(2));
    dot.setAttribute("opacity", "1");
    dot.setAttribute(
      "fill",
      passed ? "var(--safety-history-pass, #16a34a)" : "var(--safety-history-fail, #dc2626)",
    );
  }

  tooltip.hidden = false;
  tooltip.innerHTML = `
    <div class="safety-history-tooltip-time">${fmtTooltipTime(time)}</div>
    <div class="safety-history-tooltip-value ${passed ? "is-passed" : "is-failed"}">${fmtNumber(value)}${metric.unit ? ` ${metric.unit}` : ""}</div>
    <div class="safety-history-tooltip-state">${passed ? "OK" : "FAIL"}${metric.threshold != null ? ` · limit ${fmtLimit(metric)}` : ""}</div>
  `;
  // Position near cursor; clamp so it stays on screen.
  const tooltipRect = tooltip.getBoundingClientRect();
  let left = event.clientX + 12;
  let top = event.clientY + 12;
  if (left + tooltipRect.width > window.innerWidth - 8) {
    left = event.clientX - tooltipRect.width - 12;
  }
  if (top + tooltipRect.height > window.innerHeight - 8) {
    top = event.clientY - tooltipRect.height - 12;
  }
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
});

document.addEventListener("mouseleave", (event) => {
  if (event.target === document) {
    const tooltip = ensureChartTooltip();
    tooltip.hidden = true;
  }
}, true);

document.addEventListener("change", (event) => {
  const input = event.target.closest("[data-range-from], [data-range-to]");
  if (!input) return;
  const which = input.dataset.rangeFrom !== undefined ? "from" : "to";
  const date = new Date(input.value);
  if (Number.isNaN(date.getTime())) return;
  activeRange = { ...activeRange, [which]: date, preset: null };
  syncRangeUi();
  rerender();
});

async function poll() {
  try {
    const response = await fetch(API_URL, { headers: { Accept: "application/json" } });
    const payload = await response.json();
    render(payload);
  } catch (err) {
    console.error("safety poll failed", err);
  }
}

const initial = getInitialPayload();
if (initial) {
  render(initial);
}

let timer = null;
function startPolling() {
  if (timer) return;
  timer = setInterval(poll, POLL_INTERVAL_MS);
}
function stopPolling() {
  if (!timer) return;
  clearInterval(timer);
  timer = null;
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    poll();
    startPolling();
  } else {
    stopPolling();
  }
});

if (document.visibilityState === "visible") {
  startPolling();
}
