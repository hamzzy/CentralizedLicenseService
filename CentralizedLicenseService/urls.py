"""
URL configuration for CentralizedLicenseService project.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from core.views import HealthCacheView, HealthDBView, HealthView, ReadyView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health check endpoints
    path("health/", HealthView.as_view(), name="health"),
    path("health/db/", HealthDBView.as_view(), name="health-db"),
    path("health/cache/", HealthCacheView.as_view(), name="health-cache"),
    path("ready/", ReadyView.as_view(), name="ready"),
    # API endpoints
    path("api/v1/brand/", include("api.v1.brand.urls")),
    path("api/v1/product/", include("api.v1.product.urls")),
    # OpenAPI Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # ReDoc
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
