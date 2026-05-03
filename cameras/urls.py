from django.urls import path

from . import views

app_name = "cameras"

urlpatterns = [
    path("", views.index, name="index"),
    path("stream/<path:suffix>", views.proxy, name="proxy"),
    path(
        "webcam/<str:host>/<int:port>/<path:suffix>",
        views.webcam_proxy,
        name="webcam_proxy",
    ),
]
