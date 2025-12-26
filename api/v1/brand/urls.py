"""
URL configuration for brand API endpoints.
"""

from django.urls import path

from api.v1.brand import views

urlpatterns = [
    path(
        "licenses/provision",
        views.provision_license,
        name="provision-license",
    ),
    path(
        "licenses/<uuid:license_id>/renew",
        views.renew_license,
        name="renew-license",
    ),
    path(
        "licenses/<uuid:license_id>/suspend",
        views.suspend_license,
        name="suspend-license",
    ),
    path(
        "licenses/<uuid:license_id>/resume",
        views.resume_license,
        name="resume-license",
    ),
    path(
        "licenses/<uuid:license_id>/cancel",
        views.cancel_license,
        name="cancel-license",
    ),
    path("licenses", views.list_licenses_by_email, name="list-licenses"),
]
