"""
Core views for health checks and system status.
"""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt


@method_decorator(csrf_exempt, name="dispatch")
class HealthView(View):
    """Health check endpoint."""

    def get(self, _request):
        """Return service health status."""
        return JsonResponse({"status": "healthy", "service": "license-service"})


@method_decorator(csrf_exempt, name="dispatch")
class HealthDBView(View):
    """Database health check endpoint."""

    def get(self, _request):
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return JsonResponse({"status": "healthy", "database": "connected"})
        except Exception as e:  # pylint: disable=broad-exception-caught
            return JsonResponse(
                {"status": "unhealthy", "database": "disconnected", "error": str(e)},
                status=503,
            )


@method_decorator(csrf_exempt, name="dispatch")
class HealthCacheView(View):
    """Cache health check endpoint."""

    def get(self, _request):
        """Check cache connectivity."""
        try:
            cache.set("health_check", "ok", 10)
            value = cache.get("health_check")
            if value == "ok":
                return JsonResponse({"status": "healthy", "cache": "connected"})
            return JsonResponse(
                {"status": "unhealthy", "cache": "disconnected"},
                status=503,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return JsonResponse(
                {"status": "unhealthy", "cache": "disconnected", "error": str(e)},
                status=503,
            )


@method_decorator(csrf_exempt, name="dispatch")
class ReadyView(View):
    """Readiness check endpoint."""

    def get(self, _request):
        """Check if service is ready to accept traffic."""
        checks = {
            "database": self._check_database(),
            "cache": self._check_cache(),
        }

        all_healthy = all(checks.values())
        status_code = 200 if all_healthy else 503

        return JsonResponse(
            {
                "status": "ready" if all_healthy else "not_ready",
                "checks": checks,
            },
            status=status_code,
        )

    async def _check_database(self) -> bool:
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    async def _check_cache(self) -> bool:
        """Check cache connectivity."""
        try:
            cache.set("ready_check", "ok", 10)
            return cache.get("ready_check") == "ok"
        except Exception:  # pylint: disable=broad-exception-caught
            return False
