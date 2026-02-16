import re
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

from hub import operations
from hub.models import ManualPage, OperationalChecklistState
from hub.safety import fetch_safety_status


def project_info(request):
    return {
        "PROJECT_VERSION": settings.PROJECT_VERSION,
        "PROJECT_SOURCE_URL": settings.PROJECT_SOURCE_URL
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


def manual_pages(request):
    try:
        pages = list(ManualPage.objects.order_by("section", "slug"))
    except (OperationalError, ProgrammingError):
        pages = []

    current_slug = ""
    if (
        request.resolver_match
        and request.resolver_match.url_name == "manual_detail"
        and request.resolver_match.kwargs.get("slug")
    ):
        current_slug = request.resolver_match.kwargs.get("slug")

    sections = []
    def strip_order_prefix(value):
        return re.sub(r"^\s*\d+\s*[-._]\s*", "", value or "").strip()

    for page in pages:
        key = page.section or ""
        if not sections or sections[-1]["key"] != key:
            label_source = key.split("/")[-1] if key else ""
            sections.append(
                {
                    "key": key,
                    "label": strip_order_prefix(label_source).replace("-", " ").replace("_", " ").title()
                    or "General",
                    "pages": [],
                    "is_active": False,
                }
            )
        sections[-1]["pages"].append(page)
        if current_slug and page.slug == current_slug:
            sections[-1]["is_active"] = True

    return {
        "manual_sections": sections,
    }


def observatory_settings(request):
    return {
        "OBS_LATITUDE": settings.OBS_LATITUDE,
        "OBS_LONGITUDE": settings.OBS_LONGITUDE,
        "OBS_ELEVATION": getattr(settings, "OBS_ELEVATION", 0),
    }


def observatory_status(request):
    try:
        state, _ = OperationalChecklistState.objects.get_or_create(
            pk=1,
            defaults={"items": operations.default_checklist_state()},
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
