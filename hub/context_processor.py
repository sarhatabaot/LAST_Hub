from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse

from checklist.services import default_checklist_state
from hub.models import OperationalChecklistState
from safety.services import fetch_safety_status


def project_info(request):
    return {
        "PROJECT_VERSION": settings.PROJECT_VERSION,
        "PROJECT_SOURCE_URL": settings.PROJECT_SOURCE_URL
    }


def primary_navigation(request):
    current_url_name = request.resolver_match.url_name if request.resolver_match else ""
    current_namespace = request.resolver_match.namespace if request.resolver_match else ""
    return {
        "primary_navigation": [
            {
                "label": "Overview",
                "url": reverse("hub_overview"),
                "is_active": current_url_name == "hub_overview",
            },
            {
                "label": "Operations",
                "url": reverse("hub_operations"),
                "is_active": current_url_name == "hub_operations",
                "badge": {
                    "text": "new",
                    "tooltip": "Mission Control: sensors, checklist, commands, and forecast in one view.",
                    "variant": "new",
                },
            },
            {
                "label": "Forecast",
                "url": reverse("forecast:index"),
                "is_active": current_namespace == "forecast",
                "badge": {
                    "text": "new",
                    "tooltip": "Added in 0.3.0",
                    "variant": "new",
                },
            },
            {
                "label": "Safety",
                "url": reverse("safety:index"),
                "is_active": current_namespace == "safety",
                "badge": {
                    "text": "new",
                    "tooltip": "Added in 0.3.0",
                    "variant": "new",
                },
                "children": [
                    {
                        "label": "Grafana",
                        "url": "http://10.23.1.25/grafana-new/",
                        "external": True,
                    },
                ],
            },
            {
                "label": "Checklist",
                "url": reverse("checklist:index"),
                "is_active": current_namespace == "checklist",
                "badge": {
                    "text": "WIP",
                    "tooltip": "Work in progress — open/close don't drive real hardware yet.",
                    "variant": "wip",
                },
            },
            {
                "label": "Controller",
                "url": reverse("hub_controller"),
                "is_active": current_url_name == "hub_controller",
                "badge": {
                    "text": "WIP",
                    "tooltip": "Work in progress — backed by a mock; commands don't reach hardware yet.",
                    "variant": "wip",
                },
            },
            {
                "label": "Cameras",
                "url": reverse("cameras:index"),
                "is_active": current_namespace == "cameras",
                "badge": {
                    "text": "WIP",
                    "tooltip": "Placeholder — camera tools land here.",
                    "variant": "wip",
                },
            },
            {
                "label": "Docs",
                "url": reverse("docs:index"),
                "is_active": current_namespace == "docs",
                "badge": {
                    "text": "WIP",
                    "tooltip": "Work in progress — information may not be 100% up to date.",
                    "variant": "wip",
                },
            },
        ],
        "current_url_name": current_url_name,
        "current_namespace": current_namespace,
    }


def safety_status(request):
    status = fetch_safety_status(timeout=2)
    if status["error"]:
        label = "Unknown"
    elif status["safe"]:
        label = "SAFE"
    else:
        label = "UNSAFE"

    return {
        "safety_sidebar": {
            "safe": status["safe"],
            "label": label,
            "error": status["error"],
        }
    }


def observatory_settings(request):
    return {
        "OBS_LATITUDE": settings.OBS_LATITUDE,
        "OBS_LONGITUDE": settings.OBS_LONGITUDE,
        "OBS_ELEVATION": getattr(settings, "OBS_ELEVATION", 0),
    }


def analytics(request):
    return {
        "UMAMI_SCRIPT_URL": getattr(settings, "UMAMI_SCRIPT_URL", ""),
        "UMAMI_WEBSITE_ID": getattr(settings, "UMAMI_WEBSITE_ID", ""),
    }


def observatory_status(request):
    try:
        state, _ = OperationalChecklistState.objects.get_or_create(
            pk=1,
            defaults={"items": default_checklist_state()},
        )
        status = state.observatory_state
        label = state.state_label()
    except (OperationalError, ProgrammingError):
        status = OperationalChecklistState.STATE_UNKNOWN
        label = "Unknown"
    return {
        "observatory_status": {
            "state": status,
            "label": label,
        }
    }
