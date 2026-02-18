import requests

from LAST_Hub import settings


def _normalize_reason_metrics(metrics):
    normalized = []
    for metric in metrics or []:
        if not isinstance(metric, dict):
            continue
        try:
            value = float(metric.get("value"))
        except (TypeError, ValueError):
            continue

        threshold = metric.get("threshold")
        if threshold is not None:
            try:
                threshold = float(threshold)
            except (TypeError, ValueError):
                threshold = None

        normalized.append(
            {
                "key": str(metric.get("key") or "").strip(),
                "label": str(metric.get("label") or "").strip(),
                "value": value,
                "threshold": threshold,
                "operator": str(metric.get("operator") or "").strip(),
                "unit": str(metric.get("unit") or "").strip(),
                "state": str(metric.get("state") or "").strip(),
            }
        )
    return normalized


def fetch_safety_status(timeout=3):
    safe = None
    passed_reasons = []
    failed_reasons = []
    passed_reason_metrics = []
    failed_reason_metrics = []
    stale_sensors = []
    evaluated_at = ""
    error = ""
    passed_count = 0
    failed_count = 0

    try:
        base_url = settings.OBS_SAFETY_API_BASE_URL.rstrip("/")
        response = requests.get(
            f"{base_url}/safety/status",
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()

        safe = bool(payload.get("safe"))
        reasons = payload.get("reasons") or {}
        passed_reasons = reasons.get("passed") or []
        failed_reasons = reasons.get("failed") or []
        reason_metrics = payload.get("reason_metrics") or {}
        passed_reason_metrics = _normalize_reason_metrics(reason_metrics.get("passed"))
        failed_reason_metrics = _normalize_reason_metrics(reason_metrics.get("failed"))
        passed_count = len(passed_reasons) if passed_reasons else len(passed_reason_metrics)
        failed_count = len(failed_reasons) if failed_reasons else len(failed_reason_metrics)
        stale_sensors = payload.get("stale_sensors") or []
        evaluated_at = payload.get("evaluated_at") or ""
    except (requests.RequestException, ValueError) as exc:
        error = f"Failed to load safety status: {exc}"

    return {
        "safe": safe,
        "passed_reasons": passed_reasons,
        "failed_reasons": failed_reasons,
        "passed_reason_metrics": passed_reason_metrics,
        "failed_reason_metrics": failed_reason_metrics,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "stale_sensors": stale_sensors,
        "evaluated_at": evaluated_at,
        "error": error,
    }
