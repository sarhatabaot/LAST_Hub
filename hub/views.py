import json
from pathlib import Path

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from markdownx.utils import markdownify

from LAST_Hub import settings
from LAST_Hub.settings import BASE_DIR
from controller import client as controller_client
from hub import operations
from hub.forms import AccountRequestForm
from hub.models import ManualPage, OperationalChecklistState
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

def manual_index(request):
    context = {
        "page": None,
        "content_html": "",
    }
    return render(request, "docs/manual.html", context)


def manual_detail(request, slug):
    page = get_object_or_404(ManualPage, slug=slug)
    content_html = markdownify(page.content)
    context = {
        "page": page,
        "content_html": content_html,
    }
    return render(request, "docs/manual.html", context)

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


def _get_or_create_state():
    state, created = OperationalChecklistState.objects.get_or_create(
        pk=1,
        defaults={
            "items": operations.default_checklist_state(),
        },
    )
    if created:
        return state

    normalized = operations.normalize_checklist_state(state.items)
    if normalized != state.items:
        state.items = normalized
        state.save(update_fields=["items", "updated_at"])
    return state


def _get_or_create_state_for_update():
    try:
        state = OperationalChecklistState.objects.select_for_update().get(pk=1)
    except OperationalChecklistState.DoesNotExist:
        state = OperationalChecklistState.objects.create(
            pk=1, items=operations.default_checklist_state()
        )
        return state

    normalized = operations.normalize_checklist_state(state.items)
    if normalized != state.items:
        state.items = normalized
        state.save(update_fields=["items", "updated_at"])
    return state


@login_required
def operations_view(request):
    state = _get_or_create_state()
    checklist_items, _ = operations.build_checklist_items(state.items)

    all_checked = all(item["checked"] for item in checklist_items)

    context = {
        "state": state,
        "state_label": state.state_label(),
        "checklist_items": checklist_items,
        "all_checked": all_checked,
        "controller_configured": bool(settings.CONTROLLER_API_BASE_URL),
    }
    return render(request, "operations/operations.html", context)


@login_required
@require_POST
def checklist_toggle(request):
    item_key = request.POST.get("item_key", "").strip()
    desired = request.POST.get("checked") == "on"

    valid_keys = {item["key"] for item in operations.CHECKLIST_ITEMS}
    if item_key not in valid_keys:
        messages.error(request, "Unknown checklist item.")
        return redirect("operations")

    with transaction.atomic():
        state = _get_or_create_state_for_update()

        items = operations.normalize_checklist_state(state.items)
        items[item_key] = desired
        state.items = items
        state.updated_by = request.user
        state.save(update_fields=["items", "updated_by", "updated_at"])

    return redirect("operations")


def _record_action(state, action, status, message, user):
    state.last_action = action
    state.last_action_status = status
    state.last_action_message = message
    state.last_action_at = timezone.now()
    state.last_action_by = user


@login_required
@require_POST
def open_observatory(request):
    with transaction.atomic():
        state = _get_or_create_state_for_update()
        checklist_items, _ = operations.build_checklist_items(state.items)
        all_checked = all(item["checked"] for item in checklist_items)

        if not all_checked:
            messages.error(request, "Complete the checklist before opening the observatory.")
            _record_action(
                state,
                OperationalChecklistState.ACTION_OPEN,
                OperationalChecklistState.ACTION_STATUS_SKIPPED,
                "Checklist incomplete.",
                request.user,
            )
            state.save(
                update_fields=[
                    "last_action",
                    "last_action_status",
                    "last_action_message",
                    "last_action_at",
                    "last_action_by",
                ]
            )
            return redirect("operations")

        success, message = controller_client.open_observatory()
        if success:
            state.observatory_state = OperationalChecklistState.STATE_OPEN
            action_status = OperationalChecklistState.ACTION_STATUS_SUCCESS
            messages.success(request, "Open observatory request sent.")
        else:
            if not settings.CONTROLLER_API_BASE_URL:
                action_status = OperationalChecklistState.ACTION_STATUS_SKIPPED
                messages.warning(request, message)
            else:
                action_status = OperationalChecklistState.ACTION_STATUS_FAILED
                messages.error(request, message)

        _record_action(state, OperationalChecklistState.ACTION_OPEN, action_status, message, request.user)
        state.updated_by = request.user
        state.save(
            update_fields=[
                "observatory_state",
                "last_action",
                "last_action_status",
                "last_action_message",
                "last_action_at",
                "last_action_by",
                "updated_by",
                "updated_at",
            ]
        )

    return redirect("operations")


@login_required
@require_POST
def close_observatory(request):
    with transaction.atomic():
        state = _get_or_create_state_for_update()

        success, message = controller_client.close_observatory()
        if success:
            state.observatory_state = OperationalChecklistState.STATE_CLOSED
            action_status = OperationalChecklistState.ACTION_STATUS_SUCCESS
            messages.success(request, "Close observatory request sent.")
        else:
            if not settings.CONTROLLER_API_BASE_URL:
                action_status = OperationalChecklistState.ACTION_STATUS_SKIPPED
                messages.warning(request, message)
            else:
                action_status = OperationalChecklistState.ACTION_STATUS_FAILED
                messages.error(request, message)

        _record_action(state, OperationalChecklistState.ACTION_CLOSE, action_status, message, request.user)
        state.updated_by = request.user
        state.save(
            update_fields=[
                "observatory_state",
                "last_action",
                "last_action_status",
                "last_action_message",
                "last_action_at",
                "last_action_by",
                "updated_by",
                "updated_at",
            ]
        )

    return redirect("operations")
