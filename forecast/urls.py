from django.urls import path

from . import views

app_name = "forecast"

urlpatterns = [
    path("", views.forecast_view, name="index"),
    path("api/", views.forecast_api, name="api"),
]

