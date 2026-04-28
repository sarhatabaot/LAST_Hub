from collections import defaultdict
from datetime import datetime, timezone

import requests
from django.conf import settings


SERIES_LABELS = {
    "temperature": ("Temperature", "degC"),
    "relative_humidity": ("Humidity", "%"),
    "total_precipitation": ("Precipitation", "mm"),
    "cloud_cover": ("Cloud Cover", "%"),
}

DEFAULT_VISIBLE_GROUPS = (
    "temperature",
    "relative_humidity",
    "cloud_cover",
    "total_precipitation",
)


def _provider_definitions():
    return [
        {
            "key": "ims232",
            "label": "IMS232",
            "url": settings.FORECAST_URL,
            "enabled": bool(settings.FORECAST_URL),
        }
    ]


def normalize_time(raw):
    if isinstance(raw, (int, float)):
        if raw > 1e15:
            return round(raw / 1e6)
        return int(raw)
    return raw


def normalize_rows(raw):
    if isinstance(raw, list):
        return [
            {
                "time": normalize_time(row.get("time")),
                "series": str(row.get("series") or "").strip(),
                "value": row.get("value"),
            }
            for row in raw
            if isinstance(row, dict)
        ]

    if isinstance(raw, dict):
        normalized = []
        for series, payload in raw.items():
            if not isinstance(payload, dict):
                continue
            times = payload.get("time") or []
            values = payload.get("value") or []
            count = min(len(times), len(values))
            for index in range(count):
                normalized.append(
                    {
                        "time": normalize_time(times[index]),
                        "series": str(series).strip(),
                        "value": values[index],
                    }
                )
        return normalized

    return []


def infer_group_key(series_name):
    if "cloud_cover" in series_name:
        return "cloud_cover"
    return series_name


def _coerce_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_timestamp(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
    return str(value or "")


def _format_window_label(start, end):
    if not start or not end:
        return "No forecast window available"

    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    if start_dt.date() == end_dt.date():
        return start_dt.strftime("%b %d, %Y UTC")
    return f"{start_dt.strftime('%b %d, %Y')} - {end_dt.strftime('%b %d, %Y')} UTC"


def _format_display_value(value, unit="", decimals=1):
    if unit == "mm" and value < 0.1:
        return "0"
    return f"{value:.{decimals}f}"


def fetch_provider(provider, timeout=10):
    if not provider["enabled"]:
        return {
            "provider": provider,
            "status": "disabled",
            "rows": [],
            "error": "Provider URL is not configured.",
        }

    try:
        response = requests.get(provider["url"], timeout=timeout)
        response.raise_for_status()
        rows = normalize_rows(response.json())
        return {
            "provider": provider,
            "status": "ok",
            "rows": rows,
            "error": "",
        }
    except (requests.RequestException, ValueError, OSError) as exc:
        return {
            "provider": provider,
            "status": "error",
            "rows": [],
            "error": f"Failed to load provider: {exc}",
        }


def summarize_rows(rows):
    numeric_rows = []
    for row in rows:
        value = _coerce_number(row["value"])
        if value is None or not row["series"]:
            continue
        numeric_rows.append({**row, "value": value})

    timestamps = []
    for row in numeric_rows:
        raw_time = row["time"]
        if isinstance(raw_time, (int, float)):
            timestamps.append(int(raw_time))

    start = _format_timestamp(min(timestamps)) if timestamps else ""
    end = _format_timestamp(max(timestamps)) if timestamps else ""

    by_group = defaultdict(list)
    for row in numeric_rows:
        by_group[infer_group_key(row["series"])].append(row["value"])

    stats = []
    for key in DEFAULT_VISIBLE_GROUPS:
        values = by_group.get(key) or []
        if not values:
            continue
        label, unit = SERIES_LABELS.get(key, (key.replace("_", " ").title(), ""))
        stats.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "min": min(values),
                "max": max(values),
                "latest": values[-1],
            }
        )

    return {
        "window_start": start,
        "window_end": end,
        "window_label": _format_window_label(start, end),
        "point_count": len(numeric_rows),
        "stats": stats,
    }


def build_series_groups(rows):
    grouped = defaultdict(lambda: defaultdict(list))

    for row in rows:
        series_name = row["series"]
        value = _coerce_number(row["value"])
        if not series_name or value is None:
            continue
        group_key = infer_group_key(series_name)
        grouped[group_key][series_name].append(
            {
                "x": row["time"],
                "y": value,
            }
        )

    series_groups = []
    for key in DEFAULT_VISIBLE_GROUPS:
        series_map = grouped.get(key)
        if not series_map:
            continue
        label, unit = SERIES_LABELS.get(key, (key.replace("_", " ").title(), ""))
        datasets = []
        for series_name, points in sorted(series_map.items()):
            datasets.append(
                {
                    "label": series_name.replace("_", " ").title(),
                    "series": series_name,
                    "points": points,
                }
            )
        series_groups.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "datasets": datasets,
            }
        )

    return series_groups


def get_forecast_aggregate():
    provider_results = [fetch_provider(provider) for provider in _provider_definitions()]
    rows = []
    warnings = []
    providers = []

    for result in provider_results:
        provider = result["provider"]
        rows.extend(result["rows"])
        if result["error"]:
            warnings.append(
                {
                    "provider": provider["label"],
                    "message": result["error"],
                }
            )
        providers.append(
            {
                "key": provider["key"],
                "label": provider["label"],
                "status": result["status"],
                "row_count": len(result["rows"]),
                "error": result["error"],
            }
        )

    summary = summarize_rows(rows)
    summary_cards = [
        {
            "label": "Forecast Window",
            "value": summary["window_label"],
            "detail": f"{summary['point_count']} normalized points",
        }
    ]

    for stat in summary["stats"]:
        unit = f" {stat['unit']}" if stat["unit"] else ""
        latest = _format_display_value(stat["latest"], stat["unit"], decimals=1)
        minimum = _format_display_value(stat["min"], stat["unit"], decimals=1)
        maximum = _format_display_value(stat["max"], stat["unit"], decimals=1)
        summary_cards.append(
            {
                "label": stat["label"],
                "value": f"{latest}{unit}",
                "detail": f"Range {minimum} to {maximum}{unit}",
            }
        )

    latest_by_key = {stat["key"]: stat for stat in summary["stats"]}
    cloud_stat = latest_by_key.get("cloud_cover")
    rain_stat = latest_by_key.get("total_precipitation")

    if cloud_stat:
        latest_cloud = cloud_stat["latest"]
        if latest_cloud <= 20:
            cloud_state_name = "Clear"
        elif latest_cloud <= 60:
            cloud_state_name = "Variable"
        else:
            cloud_state_name = "Cloudy"
        cloud_state = {
            "label": "Cloud state",
            "state": cloud_state_name,
            "detail": f"{latest_cloud:.0f}% latest cloud cover",
        }
    else:
        cloud_state = {
            "label": "Cloud state",
            "state": "Unknown",
            "detail": "No cloud-cover data available",
        }

    if rain_stat:
        latest_rain = rain_stat["latest"]
        if latest_rain <= 0.05:
            rain_state_name = "Dry"
        elif latest_rain <= 0.5:
            rain_state_name = "Light risk"
        else:
            rain_state_name = "Wet"
        rain_state = {
            "label": "Rain state",
            "state": rain_state_name,
            "detail": f"{_format_display_value(latest_rain, 'mm', decimals=2)} mm latest precipitation",
        }
    else:
        rain_state = {
            "label": "Rain state",
            "state": "Unknown",
            "detail": "No precipitation data available",
        }

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "providers": providers,
        "warnings": warnings,
        "summary": summary,
        "summary_cards": summary_cards,
        "overview_states": {
            "cloud": cloud_state,
            "rain": rain_state,
        },
        "series_groups": build_series_groups(rows),
    }
