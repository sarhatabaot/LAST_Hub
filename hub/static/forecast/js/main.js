import { DateTime } from "https://cdn.jsdelivr.net/npm/luxon@3.7.2/+esm";
import {
  createSeriesChart,
  updateChartTheme
} from "./chart.js";

let charts = [];

const UNIT_LABELS = {
  temperature: "°C",
  total_precipitation: "mm",
  relative_humidity: "%",
  cloud_cover: "%"
};

function resolveUnitForGroup(groupKey) {
  if (groupKey.includes("cloud_cover")) {
    return UNIT_LABELS.cloud_cover || null;
  }
  return UNIT_LABELS[groupKey] || null;
}

function formatTitle(groupKey) {
  return groupKey === "cloud_cover"
    ? "Cloud cover"
    : groupKey.replace(/_/g, " ");
}

function normalizeTime(raw) {
  if (typeof raw === "number") {
    if (raw > 1e15) {
      return Math.round(raw / 1e6);
    }
    return raw;
  }
  return raw;
}

function normalizeForecast(raw) {
  if (Array.isArray(raw)) {
    return raw.map((row) => ({
      time: normalizeTime(row.time),
      series: row.series,
      value: row.value
    }));
  }

  if (raw && typeof raw === "object") {
    const result = [];
    for (const [series, payload] of Object.entries(raw)) {
      const times = Array.isArray(payload.time) ? payload.time : [];
      const values = Array.isArray(payload.value) ? payload.value : [];
      const count = Math.min(times.length, values.length);

      for (let i = 0; i < count; i += 1) {
        result.push({
          time: normalizeTime(times[i]),
          series,
          value: values[i]
        });
      }
    }
    return result;
  }

  return [];
}

function getMillis(time) {
  if (typeof time === "number") {
    return time;
  }
  const parsed = Date.parse(time);
  return Number.isNaN(parsed) ? null : parsed;
}

function setRangeSubtitle(rows) {
  const subtitle = document.getElementById("pageSubtitle");
  if (!(subtitle instanceof HTMLParagraphElement)) {
    return;
  }

  const millis = rows
    .map((row) => getMillis(row.time))
    .filter((value) => value !== null);

  if (millis.length === 0) {
    subtitle.textContent = "No timestamp range available";
    subtitle.setAttribute("aria-busy", "false");
    return;
  }

  const min = Math.min(...millis);
  const max = Math.max(...millis);

  const start = DateTime.fromMillis(min, { zone: "utc" });
  const end = DateTime.fromMillis(max, { zone: "utc" });

  const label = start.hasSame(end, "day")
    ? `${start.toFormat("LLL dd, yyyy")} (UTC)`
    : `${start.toFormat("LLL dd, yyyy")} – ${end.toFormat("LLL dd, yyyy")} (UTC)`;

  subtitle.textContent = label;
  subtitle.setAttribute("aria-busy", "false");
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;

  const toggle = document.getElementById("themeToggle");
  if (toggle instanceof HTMLButtonElement) {
    const label =
      theme === "auto" ? "Auto" :
      theme === "dark" ? "Dark" : "Light";

    const labelSpan = toggle.querySelector(".toggle-label");
    if (labelSpan instanceof HTMLSpanElement) {
      labelSpan.textContent = label;
    }
  }

  charts.forEach((chart) => updateChartTheme(chart));
}

function initThemeToggle() {
  const toggle = document.getElementById("themeToggle");
  if (!(toggle instanceof HTMLButtonElement)) {
    return;
  }

  const stored = localStorage.getItem("theme");
  let theme =
    stored === "light" || stored === "dark" || stored === "auto"
      ? stored
      : "auto";

  applyTheme(theme);

  toggle.addEventListener("click", () => {
    theme = theme === "auto"
      ? "dark"
      : theme === "dark"
      ? "light"
      : "auto";

    localStorage.setItem("theme", theme);
    applyTheme(theme);
  });
}

async function loadForecast() {
  const response = await fetch("./api/");
  if (!response.ok) {
    throw new Error(`Failed to load forecast: ${response.status}`);
  }
  return normalizeForecast(await response.json());
}

async function init() {
  initThemeToggle();

  const rows = await loadForecast();
  setRangeSubtitle(rows);

  const container = document.getElementById("chartGrid");
  if (!(container instanceof HTMLDivElement)) {
    throw new Error("Chart container not found");
  }

  container.innerHTML = "";

  const grouped = new Map();

  for (const row of rows) {
    const groupKey = row.series.includes("cloud_cover")
      ? "cloud_cover"
      : row.series;

    if (!grouped.has(groupKey)) {
      grouped.set(groupKey, new Map());
    }

    const seriesMap = grouped.get(groupKey);

    if (!seriesMap.has(row.series)) {
      seriesMap.set(row.series, []);
    }

    seriesMap.get(row.series).push({
      x: row.time,
      y: row.value
    });
  }

  const totalCards = grouped.size;
  const columns = Math.max(1, Math.ceil(Math.sqrt(totalCards)));
  const rowsCount = Math.max(1, Math.ceil(totalCards / columns));

  container.style.setProperty("--columns", String(columns));
  container.style.setProperty("--rows", String(rowsCount));

  charts.forEach((chart) => chart.destroy());
  charts = [];

  for (const [groupKey, seriesMap] of grouped.entries()) {
    const card = document.createElement("div");
    card.className = "chart-card";

    const title = document.createElement("h2");
    title.className = "chart-title";

    const unit = resolveUnitForGroup(groupKey);
    title.textContent = unit
      ? `${formatTitle(groupKey)} (${unit})`
      : formatTitle(groupKey);

    const canvas = document.createElement("canvas");
    canvas.className = "chart-canvas";

    card.appendChild(title);
    card.appendChild(canvas);
    container.appendChild(card);

    const datasets = Array.from(seriesMap.entries()).map(
      ([series, data]) => ({
        label: series.replace(/_/g, " "),
        data
      })
    );

    charts.push(
      createSeriesChart(canvas, datasets, unit || undefined)
    );
  }
}

init().catch(console.error);
