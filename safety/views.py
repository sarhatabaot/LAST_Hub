from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .services import fetch_safety_status


def status_view(request):
    return render(
        request,
        "safety/status.html",
        {"safety_data": fetch_safety_status(timeout=3)},
    )


@require_GET
def status_api(request):
    payload = fetch_safety_status(timeout=3)
    status = 503 if payload.get("error") else 200
    return JsonResponse(payload, status=status)
