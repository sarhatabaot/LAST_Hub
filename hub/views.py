import json
from pathlib import Path

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect, render

from checklist.services import get_dashboard_summary
from forecast.services import get_forecast_aggregate
from hub.forms import AccountRequestForm
from safety.services import fetch_safety_status


BASE_DIR = Path(__file__).resolve().parent

def _load_service_sections():
    services_path = BASE_DIR / "data" / "services.json"

    with open(services_path, encoding="utf-8") as f:
        config = json.load(f)

    return config


def overview_view(request):
    forecast_data = get_forecast_aggregate()
    checklist_summary = get_dashboard_summary()
    safety_data = fetch_safety_status(timeout=2)
    context = {
        "safety_data": safety_data,
        "forecast_data": forecast_data,
        "checklist_summary": checklist_summary,
        "service_sections": _load_service_sections(),
    }
    return render(request, "hub/overview.html", context)


def resources_view(request):
    context = {
        "service_sections": _load_service_sections(),
    }
    return render(request, "hub/resources.html", context)


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


def account_request(request):
    if request.method == "POST":
        form = AccountRequestForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                form.add_error("email", "A request with this email already exists.")
            else:
                messages.success(
                    request,
                    "Request submitted. An admin will review it shortly.",
                )
                return redirect("account_request")
    else:
        form = AccountRequestForm()

    return render(request, "accounts/request_access.html", {"form": form})


def operations_redirect(request):
    messages.info(request, "Operations has moved to Checklist.")
    return redirect("checklist:index")
