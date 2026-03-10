from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction

from controller import client as controller_client
from LAST_Hub import settings
from hub.models import OperationalChecklistState

from .services import (
    CHECKLIST_ITEMS,
    build_checklist_groups,
    build_page_context,
    default_checklist_state,
    get_or_create_state_for_update,
    normalize_checklist_state,
)


def _record_action(state, action, status, message, user):
    state.last_action = action
    state.last_action_status = status
    state.last_action_message = message
    state.last_action_at = timezone.now()
    state.last_action_by = user


def _dynamic_context():
    context = build_page_context()
    context["controller_configured"] = bool(settings.CONTROLLER_API_BASE_URL)
    return context


def checklist_view(request):
    context = _dynamic_context()
    return render(request, "checklist/checklist.html", context)


@login_required
@require_POST
def checklist_toggle(request):
    item_key = request.POST.get("item_key", "").strip()
    desired = request.POST.get("checked") == "on"

    valid_keys = {item["key"] for item in CHECKLIST_ITEMS}
    if item_key not in valid_keys:
        messages.error(request, "Unknown checklist item.")
        return redirect("checklist:index")

    with transaction.atomic():
        state = get_or_create_state_for_update()
        items = normalize_checklist_state(state.items)
        items[item_key] = desired
        state.items = items
        state.updated_by = request.user
        state.save(update_fields=["items", "updated_by", "updated_at"])

    if request.headers.get("HX-Request"):
        return render(request, "checklist/_panel.html", _dynamic_context())

    return redirect("checklist:index")


@login_required
@require_POST
def open_observatory(request):
    with transaction.atomic():
        state = get_or_create_state_for_update()
        _, completed_items, total_items = build_checklist_groups(state.items)
        all_checked = total_items > 0 and completed_items == total_items

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
            return redirect("checklist:index")

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

    if request.headers.get("HX-Request"):
        return render(request, "checklist/_panel.html", _dynamic_context())

    return redirect("checklist:index")


@login_required
@require_POST
def close_observatory(request):
    with transaction.atomic():
        state = get_or_create_state_for_update()

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

        state.items = default_checklist_state()
        _record_action(state, OperationalChecklistState.ACTION_CLOSE, action_status, message, request.user)
        state.updated_by = request.user
        state.save(
            update_fields=[
                "observatory_state",
                "items",
                "last_action",
                "last_action_status",
                "last_action_message",
                "last_action_at",
                "last_action_by",
                "updated_by",
                "updated_at",
            ]
        )

    if request.headers.get("HX-Request"):
        return render(request, "checklist/_panel.html", _dynamic_context())

    return redirect("checklist:index")
