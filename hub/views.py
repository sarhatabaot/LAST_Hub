import json
from pathlib import Path

import requests
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render

from LAST_Hub import settings
from LAST_Hub.settings import BASE_DIR
from hub.safety import fetch_safety_status


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
    context = fetch_safety_status(timeout=3)
    return render(request, "safety/status.html", context)


def allsky_view(request):
    context = {
        "external_url": "http://10.23.2.33/allsky/",
    }
    return render(request, "observations/allsky.html", context)


def zorg_view(request):
    context = {
        "external_url": "http://10.23.1.25/",
    }
    return render(request, "observations/zorg.html", context)
