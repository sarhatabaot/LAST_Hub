import requests

from LAST_Hub import settings


def fetch_safety_status(timeout=3):
    safe = None
    passed_reasons = []
    failed_reasons = []
    stale_sensors = []
    evaluated_at = ""
    error = ""

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
        stale_sensors = payload.get("stale_sensors") or []
        evaluated_at = payload.get("evaluated_at") or ""
    except (requests.RequestException, ValueError) as exc:
        error = f"Failed to load safety status: {exc}"

    return {
        "safe": safe,
        "passed_reasons": passed_reasons,
        "failed_reasons": failed_reasons,
        "stale_sensors": stale_sensors,
        "evaluated_at": evaluated_at,
        "error": error,
    }
