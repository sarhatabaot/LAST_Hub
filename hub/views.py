import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from checklist.services import build_page_context as build_checklist_page_context
from checklist.services import get_dashboard_summary
from controller import client as controller_client
from controller.commands import COMMAND_CATALOG, is_allowed
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


def mission_control_view(request):
    context = {
        "safety_data": fetch_safety_status(timeout=2),
        "forecast_data": get_forecast_aggregate(),
        "controller_configured": bool(settings.CONTROLLER_API_BASE_URL),
    }
    context.update(build_checklist_page_context())
    return render(request, "hub/operations.html", context)


@require_http_methods(["GET", "POST"])
def controller_view(request):
    if request.method == "POST":
        # Mirror the checklist pattern: GET is viewable, mutations require login.
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        _handle_controller_action(request)

    template = (
        "hub/_controller_panel.html"
        if request.headers.get("HX-Request")
        else "hub/controller.html"
    )
    return render(request, template, _build_controller_context())


def _parse_units_from_post(post):
    raw = post.getlist("units")
    if not raw:
        return None
    units = []
    for value in raw:
        try:
            units.append(int(value))
        except (TypeError, ValueError):
            continue
    return units or None


def _units_label(units):
    return "all units" if not units else f"unit{'s' if len(units) > 1 else ''} {','.join(str(u) for u in units)}"


def _handle_controller_action(request):
    action = request.POST.get("action", "").strip()
    units = _parse_units_from_post(request.POST)
    if "units" in request.POST and units is None:
        # The form rendered a units selector but the user unchecked everything.
        messages.error(request, "Pick at least one target unit.")
        return

    target = _units_label(units)
    if action == "command":
        command = (request.POST.get("command") or "").strip()
        if not command:
            messages.error(request, "Command is required.")
        elif not is_allowed(command):
            messages.error(
                request,
                f"Unknown command: {command!r}. Pick one from the suggestions.",
            )
        else:
            payload, error = controller_client.send_command(command, units=units)
            if error:
                messages.error(request, error)
            else:
                result = payload.get("result") if isinstance(payload, dict) else payload
                messages.success(request, f"Dispatched to {target}. Result: {result}")
    elif action == "abort":
        _, error = controller_client.abort(units=units)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, f"Abort flag set on {target}.")
    elif action == "open":
        success, message = controller_client.open_observatory(units=units)
        (messages.success if success else messages.error)(request, f"{message} ({target})")
    elif action == "close":
        success, message = controller_client.close_observatory(units=units)
        (messages.success if success else messages.error)(request, f"{message} ({target})")
    else:
        messages.error(request, f"Unknown action: {action!r}")


def _build_controller_context():
    status, status_error = controller_client.get_status(timeout=3)
    units_table = []
    available_units = []
    if status and isinstance(status.get("state"), dict):
        state = status["state"]
        available_units = list(state.get("units") or [])
        for index, unit_id in enumerate(available_units):
            units_table.append({
                "id": unit_id,
                "general_status": _safe_index(state.get("general_status"), index, ""),
                "executing": _safe_index(state.get("command_executing"), index, ""),
                "abort": _safe_index(state.get("abort_activity"), index, False),
            })

    return {
        "controller_configured": bool(settings.CONTROLLER_API_BASE_URL),
        "controller_backend": (status or {}).get("backend"),
        "controller_status_error": status_error,
        "units_table": units_table,
        "available_units": available_units,
        "events": (status or {}).get("events") or [],
        "command_catalog": COMMAND_CATALOG,
        "command_schema": [
            {"base": entry["base"], "summary": entry["summary"], "args": entry.get("args", [])}
            for entry in COMMAND_CATALOG
        ],
    }


def _safe_index(seq, index, default):
    if not isinstance(seq, list) or index >= len(seq):
        return default
    return seq[index]
