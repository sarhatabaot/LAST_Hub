import { createSeriesChart, updateChartTheme } from "./chart.js";

let charts = [];

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

function formatStatus(status) {
  if (status === "ok") return "Loaded";
  if (status === "disabled") return "Disabled";
  return "Error";
}

function renderSummaryCards(payload) {
  const container = document.getElementById("forecastSummary");
  if (!(container instanceof HTMLDivElement)) {
    return;
  }

  container.innerHTML = "";
  for (const card of payload.summary_cards || []) {
    const element = document.createElement("article");
    element.className = "summary-card";
    element.innerHTML = `
      <p class="card-kicker">${card.label}</p>
      <h2>${card.value}</h2>
      <p class="card-copy">${card.detail}</p>
    `;
    container.appendChild(element);
  }
}

function renderProviders(payload) {
  const container = document.getElementById("forecastProviders");
  if (!(container instanceof HTMLDivElement)) {
    return;
  }

  container.innerHTML = "";
  for (const provider of payload.providers || []) {
    const element = document.createElement("article");
    element.className = "provider-card";
    element.innerHTML = `
      <p class="card-kicker">Provider</p>
      <h2>${provider.label}</h2>
      <p class="card-copy provider-${provider.status}">${formatStatus(provider.status)}</p>
      <p class="meta-line">${provider.row_count} normalized rows</p>
      ${provider.error ? `<p class="meta-line">${provider.error}</p>` : ""}
    `;
    container.appendChild(element);
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

function updateTheme() {
  charts.forEach((chart) => updateChartTheme(chart));
}

function renderCharts(payload) {
  const container = document.getElementById("chartGrid");
  if (!(container instanceof HTMLDivElement)) {
    return;
  }

  container.innerHTML = "";
  charts.forEach((chart) => chart.destroy());
  charts = [];

  for (const group of payload.series_groups || []) {
    const card = document.createElement("article");
    card.className = "chart-card";

    const title = document.createElement("h2");
    title.className = "chart-title";
    title.textContent = group.unit ? `${group.label} (${group.unit})` : group.label;

    const canvas = document.createElement("canvas");
    canvas.className = "chart-canvas";

    card.appendChild(title);
    card.appendChild(canvas);
    container.appendChild(card);

    const datasets = (group.datasets || []).map((dataset) => ({
      label: dataset.label,
      data: dataset.points,
    }));
    charts.push(createSeriesChart(canvas, datasets));
  }

  updateTheme();
}

async function loadPayload() {
  const response = await fetch("/hub/forecast/api/");
  return response.json();
}

function renderPayload(payload) {
  renderSummaryCards(payload);
  renderProviders(payload);
  renderWarnings(payload);
  renderCharts(payload);
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

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    updateTheme();
  }
});

window.addEventListener("resize", updateTheme);

init();
