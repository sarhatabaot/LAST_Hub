import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings


VERDICT_GO = "go"
VERDICT_MARGINAL = "marginal"
VERDICT_NOGO = "nogo"
VERDICT_RANK = {VERDICT_GO: 0, VERDICT_MARGINAL: 1, VERDICT_NOGO: 2}
VERDICT_LABELS = {
    VERDICT_GO: "OK",
    VERDICT_MARGINAL: "Marginal",
    VERDICT_NOGO: "No-go",
}


def _cloud_thresholds():
    return tuple(settings.FORECAST_CLOUD_THRESHOLDS)


def _humidity_thresholds():
    return tuple(settings.FORECAST_HUMIDITY_THRESHOLDS)


def _precip_thresholds():
    return tuple(settings.FORECAST_PRECIP_THRESHOLDS)


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
            "key": "ims",
            "label": "IMS ICON",
            "cache_path": Path(settings.FORECAST_CACHE_PATH),
            "enabled": True,
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
    return f"{value:.{decimals}f}"


def fetch_provider(provider):
    if not provider["enabled"]:
        return {
            "provider": provider,
            "status": "disabled",
            "rows": [],
            "error": "Provider is not configured.",
        }

    cache_path = provider["cache_path"]
    if not cache_path.exists():
        return {
            "provider": provider,
            "status": "missing",
            "rows": [],
            "error": "Forecast cache has not been generated yet.",
        }

    try:
        with open(cache_path) as f:
            data = json.load(f)
        rows = normalize_rows(data)
        return {
            "provider": provider,
            "status": "ok",
            "rows": rows,
            "error": "",
        }
    except (OSError, ValueError) as exc:
        return {
            "provider": provider,
            "status": "error",
            "rows": [],
            "error": f"Failed to read forecast cache: {exc}",
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


def _classify(value, thresholds):
    if value is None:
        return None
    if value < thresholds[0]:
        return VERDICT_GO
    if value < thresholds[1]:
        return VERDICT_MARGINAL
    return VERDICT_NOGO


def _worst_verdict(verdicts):
    valid = [v for v in verdicts if v]
    if not valid:
        return None
    return max(valid, key=lambda v: VERDICT_RANK[v])


def _parse_hhmm(value):
    hour, minute = (int(part) for part in str(value).split(":"))
    return hour, minute


def _night_windows(now_utc, count=3):
    tz = ZoneInfo(settings.TIME_ZONE)
    start_h, start_m = _parse_hhmm(settings.FORECAST_NIGHT_START)
    end_h, end_m = _parse_hhmm(settings.FORECAST_NIGHT_END)
    crosses_midnight = (end_h, end_m) <= (start_h, start_m)

    base_date = now_utc.astimezone(tz).date() - timedelta(days=1)
    windows = []
    offset = 0
    while len(windows) < count and offset < count + 5:
        date = base_date + timedelta(days=offset)
        offset += 1
        start_local = datetime(date.year, date.month, date.day, start_h, start_m, tzinfo=tz)
        end_date = date + timedelta(days=1) if crosses_midnight else date
        end_local = datetime(end_date.year, end_date.month, end_date.day, end_h, end_m, tzinfo=tz)
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        if end_utc <= now_utc:
            continue
        windows.append((start_utc, end_utc))
    return windows


def _rows_in_window(rows, start_ms, end_ms):
    out = defaultdict(list)
    for row in rows:
        time_ms = row["time"]
        if not isinstance(time_ms, (int, float)):
            continue
        if start_ms <= time_ms < end_ms:
            value = _coerce_number(row["value"])
            if value is None:
                continue
            out[row["series"]].append((int(time_ms), value))
    return out


def _evaluate_window(rows, dusk_dt, dawn_dt):
    start_ms = int(dusk_dt.timestamp() * 1000)
    end_ms = int(dawn_dt.timestamp() * 1000)
    by_series = _rows_in_window(rows, start_ms, end_ms)

    def values(series):
        return [v for _, v in by_series.get(series, [])]

    cloud = values("total_cloud_cover")
    rh = values("relative_humidity")
    precip = values("total_precipitation")

    peak_cloud = max(cloud) if cloud else None
    max_rh = max(rh) if rh else None
    max_precip = max(precip) if precip else None
    total_precip = sum(precip) if precip else None

    cloud_v = _classify(peak_cloud, _cloud_thresholds())
    rh_v = _classify(max_rh, _humidity_thresholds())
    precip_v = _classify(max_precip, _precip_thresholds())

    has_data = bool(cloud or rh or precip)
    verdict = _worst_verdict([cloud_v, rh_v, precip_v]) if has_data else None

    return {
        "verdict": verdict,
        "verdict_label": VERDICT_LABELS.get(verdict, "Unknown"),
        "peak_cloud": peak_cloud,
        "max_rh": max_rh,
        "max_precip": max_precip,
        "total_precip": total_precip,
        "metric_verdicts": {
            "cloud": cloud_v,
            "rh": rh_v,
            "precip": precip_v,
        },
        "has_data": has_data,
    }


def _hourly_grid(rows, dusk_dt, dawn_dt):
    start_ms = int(dusk_dt.timestamp() * 1000)
    end_ms = int(dawn_dt.timestamp() * 1000)

    by_time: dict[int, dict] = defaultdict(dict)
    for row in rows:
        time_ms = row["time"]
        if not isinstance(time_ms, (int, float)):
            continue
        if not (start_ms <= time_ms < end_ms):
            continue
        value = _coerce_number(row["value"])
        if value is None:
            continue
        by_time[int(time_ms)][row["series"]] = value

    hours = []
    for time_ms in sorted(by_time.keys()):
        s = by_time[time_ms]
        cloud_v = _classify(s.get("total_cloud_cover"), _cloud_thresholds())
        rh_v = _classify(s.get("relative_humidity"), _humidity_thresholds())
        precip_v = _classify(s.get("total_precipitation"), _precip_thresholds())
        hours.append({
            "time_ms": time_ms,
            "total_cloud": s.get("total_cloud_cover"),
            "high_cloud": s.get("high_cloud_cover"),
            "mid_cloud": s.get("medium_cloud_cover"),
            "low_cloud": s.get("low_cloud_cover"),
            "rh": s.get("relative_humidity"),
            "precip": s.get("total_precipitation"),
            "temp": s.get("temperature"),
            "metric_verdicts": {
                "cloud": cloud_v,
                "rh": rh_v,
                "precip": precip_v,
            },
            "verdict": _worst_verdict([cloud_v, rh_v, precip_v]),
        })
    return hours


def _build_observability(rows, now_utc=None):
    now_utc = now_utc or datetime.now(tz=timezone.utc)
    windows = _night_windows(now_utc, count=3)
    if not windows:
        return None

    nights = []
    for index, (start_dt, end_dt) in enumerate(windows):
        evaluation = _evaluate_window(rows, start_dt, end_dt)
        night = {
            "label": "Tonight" if index == 0 else start_dt.strftime("%a %b %d"),
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "duration_minutes": int((end_dt - start_dt).total_seconds() // 60),
            "hourly": _hourly_grid(rows, start_dt, end_dt),
            **evaluation,
        }
        nights.append(night)

    return {
        "thresholds": {
            "cloud": list(_cloud_thresholds()),
            "rh": list(_humidity_thresholds()),
            "precip": list(_precip_thresholds()),
        },
        "tonight": nights[0] if nights else None,
        "upcoming": nights[1:] if len(nights) > 1 else [],
    }


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

    observability = _build_observability(rows)

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
        "observability": observability,
        "series_groups": build_series_groups(rows),
    }
