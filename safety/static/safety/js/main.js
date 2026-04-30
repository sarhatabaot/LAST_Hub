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
  const metrics = [...failed, ...stale, ...passed];

  grid.innerHTML = "";
  if (!metrics.length) {
    return;
  }

  for (const metric of metrics) {
    const card = document.createElement("article");
    card.className = `safety-metric is-${metric._state}`;
    const label = metric.label || metric.key || "Sensor";
    const isStale = metric._state === "stale";
    const limit = isStale ? "" : fmtLimit(metric);
    const stateLabel = isStale ? "STALE" : (metric._state === "failed" ? "FAIL" : "OK");
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
  renderStatusCard(payload);
  renderError(payload);
  renderMetrics(payload);
  requestAnimationFrame(fitMetricLabels);
}

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
