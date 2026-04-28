from django.urls import include, path
from . import views

urlpatterns = [
    path("", views.overview_view, name="hub_overview"),
    path("resources/", views.resources_view, name="hub_resources"),
    path("forecast/", include(("forecast.urls", "forecast"), namespace="forecast")),
    path("safety/", include(("safety.urls", "safety"), namespace="safety")),
    path("checklist/", include(("checklist.urls", "checklist"), namespace="checklist")),
    path("docs/", include(("docs.urls", "docs"), namespace="docs")),
    path("observations/allsky/", views.allsky_view, name="allsky"),
    path("observations/zorg/", views.zorg_view, name="zorg"),
    path("operations/", views.operations_redirect, name="operations"),
    path("accounts/request/", views.account_request, name="account_request"),
    path("accounts/", include("django.contrib.auth.urls")),
]
