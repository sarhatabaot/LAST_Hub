const LUXON = () => globalThis.luxon?.DateTime;

let currentPayload = null;
let selectedNightIndex = 0;

function getNights(payload) {
  const obs = payload?.observability;
  if (!obs) return [];
  const nights = [];
  if (obs.tonight) nights.push(obs.tonight);
  for (const n of obs.upcoming || []) nights.push(n);
  return nights;
}

function getSelectedNight() {
  const nights = getNights(currentPayload);
  return nights[selectedNightIndex] || nights[0] || null;
}

function selectNight(index) {
  const nights = getNights(currentPayload);
  if (index < 0 || index >= nights.length) return;
  selectedNightIndex = index;
  renderTonight(currentPayload);
  renderHourlyGrid(currentPayload);
  renderOutlook(currentPayload);
}

function getInitialPayload() {
  const node = document.getElementById("forecast-data");
  if (!node) {
    return null;
  }

  try {
    return JSON.parse(node.textContent || "null");
  } catch {
    return null;
  }
}

function renderWarnings(payload) {
  const container = document.getElementById("forecastWarnings");
  if (!(container instanceof HTMLDivElement)) {
    return;
  }

  container.innerHTML = "";
  for (const warning of payload.warnings || []) {
    const element = document.createElement("p");
    element.className = "operations-note";
    element.textContent = `${warning.provider}: ${warning.message}`;
    container.appendChild(element);
  }
}

function setSubtitle(payload) {
  const subtitle = document.getElementById("pageSubtitle");
  if (!(subtitle instanceof HTMLParagraphElement)) {
    return;
  }

  subtitle.textContent = payload.summary?.window_label || "No forecast window available";
  subtitle.setAttribute("aria-busy", "false");
}

function fmtNum(value, decimals = 0, suffix = "") {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${value.toFixed(decimals)}${suffix}`;
}

function fmtTime(iso) {
  const DateTime = LUXON();
  if (!DateTime || !iso) return "";
  return DateTime.fromISO(iso, { zone: "utc" }).toLocal().toFormat("HH:mm");
}

function fmtDate(iso) {
  const DateTime = LUXON();
  if (!DateTime || !iso) return "";
  return DateTime.fromISO(iso, { zone: "utc" }).toLocal().toFormat("LLL d");
}

function fmtTimeMs(ms) {
  const DateTime = LUXON();
  if (!DateTime || ms == null) return "";
  return DateTime.fromMillis(ms).toLocal().toFormat("HH");
}

function fmtDuration(minutes) {
  if (!minutes) return "";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

function verdictClass(verdict) {
  return verdict ? `verdict-${verdict}` : "verdict-unknown";
}

function renderTonight(payload) {
  const card = document.getElementById("tonightCard");
  if (!(card instanceof HTMLElement)) return;

  const tonight = payload.observability?.tonight;
  if (!tonight) {
    card.hidden = true;
    return;
  }
  card.hidden = false;

  const isActive = selectedNightIndex === 0;
  const verdict = tonight.verdict || "unknown";
  const verdictLabel = tonight.has_data ? tonight.verdict_label : "No data";
  const dateLabel = fmtDate(tonight.start);

  card.className = `tonight-card ${verdictClass(verdict)}${isActive ? " is-active" : ""}`;
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-pressed", String(isActive));
  card.innerHTML = `
    <div class="tonight-head">
      <p class="card-kicker">Tonight${dateLabel ? ` &middot; ${dateLabel}` : ""}</p>
      <span class="verdict-badge ${verdictClass(verdict)}">${verdictLabel}</span>
    </div>
    <ul class="tonight-metrics">
      <li class="${verdictClass(tonight.metric_verdicts?.cloud)}">
        <span class="metric-label">Peak cloud</span>
        <span class="metric-value">${fmtNum(tonight.peak_cloud, 0, "%")}</span>
      </li>
      <li class="${verdictClass(tonight.metric_verdicts?.rh)}">
        <span class="metric-label">Max humidity</span>
        <span class="metric-value">${fmtNum(tonight.max_rh, 0, "%")}</span>
      </li>
      <li class="${verdictClass(tonight.metric_verdicts?.precip)}">
        <span class="metric-label">Total precip</span>
        <span class="metric-value">${fmtNum(tonight.total_precip, 2, " mm")}</span>
      </li>
    </ul>
  `;

  card.onclick = () => selectNight(0);
  card.onkeydown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectNight(0);
    }
  };
}

function renderHourlyGrid(payload) {
  const container = document.getElementById("hourlyGrid");
  if (!(container instanceof HTMLElement)) return;

  const night = getSelectedNight();
  const hours = night?.hourly || [];
  if (!hours.length) {
    container.hidden = true;
    return;
  }
  container.hidden = false;

  const cell = (value, decimals, suffix, verdict) => {
    const display = fmtNum(value, decimals, suffix);
    return `<td class="${verdictClass(verdict)}">${display}</td>`;
  };

  const headerCells = hours
    .map((h) => `<th scope="col">${fmtTimeMs(h.time_ms)}</th>`)
    .join("");

  const cloudCells = hours
    .map((h) => cell(h.total_cloud, 0, "%", h.metric_verdicts?.cloud))
    .join("");
  const highCloudCells = hours
    .map((h) => cell(h.high_cloud, 0, "%"))
    .join("");
  const midCloudCells = hours
    .map((h) => cell(h.mid_cloud, 0, "%"))
    .join("");
  const lowCloudCells = hours
    .map((h) => cell(h.low_cloud, 0, "%"))
    .join("");
  const rhCells = hours
    .map((h) => cell(h.rh, 0, "%", h.metric_verdicts?.rh))
    .join("");
  const precipCells = hours
    .map((h) => cell(h.precip, 2, "", h.metric_verdicts?.precip))
    .join("");
  const tempCells = hours
    .map((h) => cell(h.temp, 0, "°"))
    .join("");

  const dateLabel = fmtDate(night.start);
  const titleLabel = selectedNightIndex === 0
    ? `Tonight${dateLabel ? ` · ${dateLabel}` : ""}, hour by hour (local time)`
    : `${night.label}, hour by hour (local time)`;

  container.innerHTML = `
    <h2 class="section-title">${titleLabel}</h2>
    <div class="hourly-scroll">
      <table class="hourly-table">
        <thead>
          <tr><th scope="row" class="row-label">Hour</th>${headerCells}</tr>
        </thead>
        <tbody>
          <tr><th scope="row" class="row-label">Cloud (total)</th>${cloudCells}</tr>
          <tr class="row-sub"><th scope="row" class="row-label">— high</th>${highCloudCells}</tr>
          <tr class="row-sub"><th scope="row" class="row-label">— mid</th>${midCloudCells}</tr>
          <tr class="row-sub"><th scope="row" class="row-label">— low</th>${lowCloudCells}</tr>
          <tr><th scope="row" class="row-label">Humidity</th>${rhCells}</tr>
          <tr><th scope="row" class="row-label">Precip (mm)</th>${precipCells}</tr>
          <tr><th scope="row" class="row-label">Temp (°C)</th>${tempCells}</tr>
        </tbody>
      </table>
    </div>
  `;
}

function renderOutlook(payload) {
  const container = document.getElementById("outlookStrip");
  if (!(container instanceof HTMLElement)) return;

  const upcoming = payload.observability?.upcoming || [];
  if (!upcoming.length) {
    container.hidden = true;
    return;
  }
  container.hidden = false;

  container.innerHTML = `
    <h2 class="section-title">Outlook</h2>
    <div class="outlook-cards" id="outlookCards"></div>
  `;

  const cardsContainer = container.querySelector("#outlookCards");
  if (!(cardsContainer instanceof HTMLElement)) return;

  upcoming.forEach((night, i) => {
    const nightIndex = i + 1;
    const isActive = selectedNightIndex === nightIndex;
    const verdict = night.verdict || "unknown";
    const verdictLabel = night.has_data ? night.verdict_label : "No data";
    const card = document.createElement("article");
    card.className = `outlook-card ${verdictClass(verdict)}${isActive ? " is-active" : ""}`;
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-pressed", String(isActive));
    card.innerHTML = `
      <p class="card-kicker">${night.label}</p>
      <p class="outlook-verdict ${verdictClass(verdict)}">${verdictLabel}</p>
      <ul class="outlook-metrics">
        <li>Cloud ${fmtNum(night.peak_cloud, 0, "%")}</li>
        <li>RH ${fmtNum(night.max_rh, 0, "%")}</li>
        <li>Precip ${fmtNum(night.total_precip, 2, " mm")}</li>
      </ul>
    `;
    card.addEventListener("click", () => selectNight(nightIndex));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectNight(nightIndex);
      }
    });
    cardsContainer.appendChild(card);
  });
}

async function loadPayload() {
  const response = await fetch("/hub/forecast/api/");
  return response.json();
}

function renderPayload(payload) {
  currentPayload = payload;
  const nights = getNights(payload);
  if (selectedNightIndex >= nights.length) {
    selectedNightIndex = 0;
  }
  renderWarnings(payload);
  renderTonight(payload);
  renderHourlyGrid(payload);
  renderOutlook(payload);
  setSubtitle(payload);
}

async function init() {
  const initialPayload = getInitialPayload();
  if (initialPayload) {
    renderPayload(initialPayload);
  }

  try {
    const livePayload = await loadPayload();
    renderPayload(livePayload);
  } catch (error) {
    console.error(error);
  }
}

init();
