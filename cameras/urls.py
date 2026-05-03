from django.urls import path

from . import views

app_name = "cameras"

urlpatterns = [
    path("", views.index, name="index"),
]
