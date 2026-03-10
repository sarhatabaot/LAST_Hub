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
ALLSKY_URL = "http://10.23.2.33/allsky/"
ZORG_URL = "http://10.23.1.25/"

def _load_service_sections():
    services_path = BASE_DIR / "data" / "services.json"

    with open(services_path, encoding="utf-8") as f:
        config = json.load(f)

    return config


def _overview_failed_snippets(safety_data, limit=3):
    snippets = []

    def format_value(value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value).strip()
        compact = round(numeric, 2)
        if compact.is_integer():
            return str(int(compact))
        return f"{compact}"

    for metric in safety_data.get("failed_reason_metrics") or []:
        label = str(metric.get("label") or metric.get("key") or "Failed check").strip()
        detail = format_value(metric.get("value"))
        if metric.get("unit"):
            detail = f"{detail} {metric['unit']}"
        if metric.get("operator") and metric.get("threshold") is not None:
            threshold_text = format_value(metric["threshold"])
            detail = f"{detail} ({metric['operator']} {threshold_text}"
            if metric.get("unit"):
                detail = f"{detail} {metric['unit']}"
            detail = f"{detail})"
        visible = f"{label}, {format_value(metric.get('value'))}"
        if metric.get("unit"):
            visible = f"{visible} {metric['unit']}"
        full_text = f"{label}: {detail}"
        snippets.append(
            {
                "label": visible,
                "full_text": full_text,
            }
        )

    if not snippets:
        for reason in safety_data.get("failed_reasons") or []:
            text = str(reason).strip()
            if text:
                snippets.append(
                    {
                        "label": text,
                        "full_text": text,
                    }
                )

    return snippets[:limit]


def overview_view(request):
    forecast_data = get_forecast_aggregate()
    checklist_summary = get_dashboard_summary()
    safety_data = fetch_safety_status(timeout=2)
    stale_sensors = safety_data.get("stale_sensors") or []
    context = {
        "safety_data": safety_data,
        "forecast_data": forecast_data,
        "checklist_summary": checklist_summary,
        "overview_failed_checks": _overview_failed_snippets(safety_data),
        "overview_stale_summary": ", ".join(stale_sensors[:3]) if stale_sensors else "None",
    }
    return render(request, "hub/overview.html", context)


def resources_view(request):
    context = {
        "service_sections": _load_service_sections(),
    }
    return render(request, "hub/resources.html", context)


def allsky_view(request):
    context = {
        "external_url": ALLSKY_URL,
    }
    return render(request, "observations/allsky.html", context)


def zorg_view(request):
    return redirect(ZORG_URL)


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
