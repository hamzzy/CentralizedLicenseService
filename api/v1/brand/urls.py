"""
URL configuration for brand API endpoints.
"""

from django.urls import path

from api.v1.brand import views

urlpatterns = [
    path(
        "licenses/provision",
        views.ProvisionLicenseView.as_view(),
        name="provision-license",
    ),
    path(
        "licenses/<uuid:license_id>/renew",
        views.RenewLicenseView.as_view(),
        name="renew-license",
    ),
    path(
        "licenses/<uuid:license_id>/suspend",
        views.SuspendLicenseView.as_view(),
        name="suspend-license",
    ),
    path(
        "licenses/<uuid:license_id>/resume",
        views.ResumeLicenseView.as_view(),
        name="resume-license",
    ),
    path(
        "licenses/<uuid:license_id>/cancel",
        views.CancelLicenseView.as_view(),
        name="cancel-license",
    ),
    path(
        "licenses",
        views.ListLicensesByEmailView.as_view(),
        name="list-licenses",
    ),
]
