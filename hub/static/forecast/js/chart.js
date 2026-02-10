import {
  Chart,
  BarController,
  BarElement,
  LinearScale,
  Title,
  Tooltip,
  Legend
} from "https://cdn.jsdelivr.net/npm/chart.js@4.5.1/+esm";
import { DateTime } from "https://cdn.jsdelivr.net/npm/luxon@3.7.2/+esm";

Chart.register(
  BarController,
  BarElement,
  LinearScale,
  Title,
  Tooltip,
  Legend
);

const LIGHT_COLORS = [
  "#0f62fe",
  "#f59e0b",
  "#10b981",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4"
];

const DARK_COLORS = [
  "#6ea8ff",
  "#fbbf24",
  "#34d399",
  "#f87171",
  "#c4b5fd",
  "#22d3ee"
];

function resolveTheme() {
  const theme = document.body.dataset.theme;
  if (theme === "light" || theme === "dark") {
    return theme;
  }
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

function paletteForTheme(theme) {
  return theme === "dark" ? DARK_COLORS : LIGHT_COLORS;
}

function axisColorForTheme(theme) {
  return theme === "dark" ? "#d1d5db" : "#374151";
}

function gridColorForTheme(theme) {
  return theme === "dark"
    ? "rgba(148, 163, 184, 0.2)"
    : "rgba(148, 163, 184, 0.35)";
}

function applyThemeToChart(chart) {
  const theme = resolveTheme();
  const palette = paletteForTheme(theme);
  const axisColor = axisColorForTheme(theme);
  const gridColor = gridColorForTheme(theme);

  chart.data.datasets.forEach((dataset, index) => {
    const color = palette[index % palette.length];
    dataset.borderColor = color;
    dataset.backgroundColor = color + "66";
  });

  const scales = chart.options.scales;
  if (scales?.x) {
    scales.x.ticks = { ...(scales.x.ticks ?? {}), color: axisColor };
    scales.x.grid = { ...(scales.x.grid ?? {}), color: gridColor };
  }
  if (scales?.y) {
    scales.y.ticks = { ...(scales.y.ticks ?? {}), color: axisColor };
    scales.y.grid = { ...(scales.y.grid ?? {}), color: gridColor };
  }

  chart.update();
}

export function createSeriesChart(canvas, datasets, yLabel, isCloudGroup = false) {

  const toMillis = (value) =>
    typeof value === "number" ? value : Date.parse(value);

  datasets.forEach((dataset) => {
    dataset.data.sort((a, b) => toMillis(a.x) - toMillis(b.x));
  });

  const theme = resolveTheme();
  const palette = paletteForTheme(theme);
  const axisColor = axisColorForTheme(theme);
  const gridColor = gridColorForTheme(theme);

  const chart = new Chart(canvas, {
    type: "bar",
    data: {
      datasets: datasets.map((dataset, index) => {
        const color = palette[index % palette.length];
        const isCloud = dataset.label.toLowerCase().includes("cloud");

        return {
          label: dataset.label,
          data: dataset.data,
          parsing: false,
          borderColor: color,
          backgroundColor: color + "66",
          borderWidth: 1,
          barThickness: isCloud ? 4 : undefined,
          stack: dataset.stack ?? (isCloudGroup ? "cloud" : undefined)
        };
      })
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "nearest",
        intersect: false
      },
      plugins: {
        legend: {
          display: datasets.length > 1,
          position: "bottom"
        },
        tooltip: {
          callbacks: {
            title: (items) => {
              if (!items.length) {
                return "";
              }
              const value = items[0].parsed.x;
              return DateTime.fromMillis(value).toFormat("LLL dd, HH:mm");
            },
            label: (item) => {
              const unit = yLabel ? ` ${yLabel}` : "";
              return `${item.dataset.label}: ${item.parsed.y}${unit}`;
            }
          }
        },
        title: {
          display: false
        }
      },
      scales: {
        y: {
          stacked: isCloudGroup,
          title: {
            display: true,
            text: yLabel ?? "Value"
          },
          ticks: {
            color: axisColor
          },
          grid: {
            color: gridColor
          }
        },
        x: {
          stacked: isCloudGroup,
          type: "linear",
          ticks: {
            color: axisColor,
            maxRotation: 0,
            stepSize: 60 * 60 * 1000,
            callback: (value, index, ticks) => {
              const current = DateTime.fromMillis(value);
              if (index === 0) {
                return current.toFormat("HH");
              }
              const previous = DateTime.fromMillis(ticks[index - 1].value);
              return current.hasSame(previous, "day")
                ? current.toFormat("HH")
                : current.toFormat("LLL dd");
            }
          },
          title: {
            display: false,
            text: "Time (UTC)"
          },
          grid: {
            color: gridColor
          }
        }
      }
    }
  });

  return chart;
}

export function updateChartTheme(chart) {
  applyThemeToChart(chart);
}
