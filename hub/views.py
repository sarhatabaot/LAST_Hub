import json
from pathlib import Path

import requests
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render

from LAST_Hub import settings
from LAST_Hub.settings import BASE_DIR


# Create your views here.


BASE_DIR = Path(__file__).resolve().parent

def forecast_view(request):
    return render(request, "forecast/forecast.html")

def home_view(request):
    return render(request, "home/home.html")

def hub_view(request):
    services_path = BASE_DIR / "data" / "services.json"

    with open(services_path, encoding="utf-8") as f:
        config = json.load(f)

    has_sections = isinstance(config, dict)

    context = {
        "services": config,
        "has_sections": has_sections,
    }

    return render(request, "hub/hub.html", context)

def forecast_api(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    try:
        response = requests.get(
            settings.FORECAST_URL,
            timeout=10,
        )
        response.raise_for_status()

        return HttpResponse(
            response.text,
            content_type="application/json",
            headers={
                "Cache-Control": "no-store",
            },
        )

    except requests.RequestException as exc:
        print("Failed to load forecast:", exc)
        return HttpResponseServerError(
            '{"error": "Failed to load forecast"}',
            content_type="application/json",
        )


def safety_status(request):
    safe = False
    passed_reasons = []
    failed_reasons = []
    stale_sensors = []
    evaluated_at = ""
    error = ""

    try:
        response = requests.get(
            f"{settings.OBS_SAFETY_API_BASE_URL}/safety/status",
            timeout=3,
        )
        response.raise_for_status()
        payload = response.json()

        safe = bool(payload.get("safe"))
        reasons = payload.get("reasons") or {}
        passed_reasons = reasons.get("passed") or []
        failed_reasons = reasons.get("failed") or []
        stale_sensors = payload.get("stale_sensors") or []
        evaluated_at = payload.get("evaluated_at") or ""
        error = ""
    except (requests.RequestException, ValueError) as exc:
        error = f"Failed to load safety status: {exc}"

    context = {
        "safe": safe,
        "passed_reasons": passed_reasons,
        "failed_reasons": failed_reasons,
        "stale_sensors": stale_sensors,
        "evaluated_at": evaluated_at,
        "error": error,
    }

    return render(request, "safety/status.html", context)
