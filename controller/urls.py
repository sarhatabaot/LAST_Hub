from django.urls import path

from . import views

app_name = "controller"

urlpatterns = [
    path("observatory/status", views.status_view, name="status"),
    path("observatory/open", views.open_view, name="open"),
    path("observatory/close", views.close_view, name="close"),
    path("observatory/abort", views.abort_view, name="abort"),
    path("command", views.command_view, name="command"),
]
