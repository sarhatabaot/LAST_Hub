from django.shortcuts import render

from .services import fetch_safety_status


def status_view(request):
    context = fetch_safety_status(timeout=3)
    return render(request, "safety/status.html", context)

