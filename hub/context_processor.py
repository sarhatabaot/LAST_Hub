from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

from hub.models import ManualPage
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
        pages = list(ManualPage.objects.order_by("title"))
    except (OperationalError, ProgrammingError):
        pages = []
    return {
        "manual_pages": pages,
    }
