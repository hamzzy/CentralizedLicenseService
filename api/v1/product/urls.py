"""
URL configuration for product API endpoints.
"""

from django.urls import path

from api.v1.product import views

urlpatterns = [
    path(
        "activate",
        views.ActivateLicenseView.as_view(),
        name="activate-license",
    ),
    path(
        "status",
        views.GetLicenseStatusView.as_view(),
        name="get-license-status",
    ),
    path(
        "activations/<uuid:activation_id>",
        views.DeactivateSeatView.as_view(),
        name="deactivate-seat",
    ),
]
