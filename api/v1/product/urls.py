"""
URL configuration for product API endpoints.
"""

from django.urls import path

from api.v1.product import views

urlpatterns = [
    path("activate", views.activate_license, name="activate-license"),
    path("status", views.get_license_status, name="get-license-status"),
    path(
        "activations/<uuid:activation_id>",
        views.deactivate_seat,
        name="deactivate-seat",
    ),
]
