from django.urls import path

from . import views

app_name = "checklist"

urlpatterns = [
    path("", views.checklist_view, name="index"),
    path("toggle/", views.checklist_toggle, name="toggle"),
    path("open/", views.open_observatory, name="open"),
    path("close/", views.close_observatory, name="close"),
]

