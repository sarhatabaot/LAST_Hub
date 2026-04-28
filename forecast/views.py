from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .services import get_forecast_aggregate


def forecast_view(request):
    context = {
        "forecast_data": get_forecast_aggregate(),
    }
    return render(request, "forecast/forecast.html", context)


@require_GET
def forecast_api(request):
    payload = get_forecast_aggregate()
    status = 200 if any(provider["status"] == "ok" for provider in payload["providers"]) else 503
    return JsonResponse(payload, status=status)

