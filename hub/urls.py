from django.urls import include, path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("hub/", views.hub_view, name="hub"),
    path("forecast/", views.forecast_view, name="forecast"),
    path("forecast/api/", views.forecast_api, name="forecast_api"),
    path("observations/allsky/", views.allsky_view, name="allsky"),
    path("observations/zorg/", views.zorg_view, name="zorg"),
    path("operations/", views.operations_view, name="operations"),
    path("operations/toggle/", views.checklist_toggle, name="operations_toggle"),
    path("operations/open/", views.open_observatory, name="operations_open"),
    path("operations/close/", views.close_observatory, name="operations_close"),
    path("accounts/request/", views.account_request, name="account_request"),
    path("accounts/", include("django.contrib.auth.urls")),
]
