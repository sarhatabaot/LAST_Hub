from django.urls import path
from . import views

urlpatterns = [
    path("hub/", views.hub_view, name="hub"),
    path("forecast/", views.forecast_view, name="forecast"),
    path("forecast/api/", views.forecast_api, name="forecast_api")
]