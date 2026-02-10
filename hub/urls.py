from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("hub/", views.hub_view, name="hub"),
    path("forecast/", views.forecast_view, name="forecast"),
    path("forecast/api/", views.forecast_api, name="forecast_api"),
    path("observations/allsky/", views.allsky_view, name="allsky"),
    path("observations/zorg/", views.zorg_view, name="zorg"),
]
