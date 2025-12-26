"""
API key authentication middleware.

This middleware validates API keys for brand integration APIs
and license keys for product-facing APIs.
"""

import hashlib
import logging
from typing import Optional

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

try:
    from brands.infrastructure.models import ApiKey
except ImportError:
    ApiKey = None

try:
    from licenses.infrastructure.models import LicenseKey
except ImportError:
    LicenseKey = None

logger = logging.getLogger(__name__)


class APIKeyAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware for API key authentication.

    This middleware:
    1. Validates API keys for brand APIs (/api/v1/brand/*)
    2. Validates license keys for product APIs (/api/v1/product/*)
    3. Returns 401 Unauthorized if authentication fails
    """

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Process request and validate authentication.

        Args:
            request: HTTP request

        Returns:
            HttpResponse with 401 if authentication fails, None otherwise
        """
        # Skip authentication for admin, health checks, etc.
        if self._should_skip_auth(request.path):
            return None

        # Brand APIs require API key
        if request.path.startswith("/api/v1/brand/"):
            return self._authenticate_brand_api(request)

        # Product APIs require license key
        if request.path.startswith("/api/v1/product/"):
            return self._authenticate_product_api(request)

        return None

    def _should_skip_auth(self, path: str) -> bool:
        """
        Check if authentication should be skipped for this path.

        Args:
            path: Request path

        Returns:
            True if auth should be skipped
        """
        skip_paths = [
            "/admin/",
            "/health/",
            "/health",
            "/api/docs/",
            "/static/",
            "/media/",
        ]
        return any(path.startswith(skip) for skip in skip_paths)

    def _authenticate_brand_api(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Authenticate brand API request.

        Args:
            request: HTTP request

        Returns:
            HttpResponse with 401 if auth fails, None if successful
        """
        api_key = request.headers.get("X-API-Key") or request.headers.get(
            "Authorization", ""
        ).replace("Bearer ", "")

        if not api_key:
            return JsonResponse(
                {"error": "Missing API key. Provide X-API-Key header."},
                status=401,
            )

        if not ApiKey:
            return JsonResponse({"error": "ApiKey model not available"}, status=503)

        # Hash the API key for comparison
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            # pylint: disable=no-member
            api_key_obj = ApiKey.objects.filter(key_hash=api_key_hash).first()
            if not api_key_obj:
                logger.warning("Invalid API key attempted: %s...", api_key[:8])
                return JsonResponse({"error": "Invalid API key"}, status=401)

            # Check if API key is valid (not expired)
            if not api_key_obj.is_valid():
                logger.warning("Expired API key attempted: %s...", api_key[:8])
                return JsonResponse({"error": "API key expired"}, status=401)

            # Mark API key as used
            api_key_obj.mark_used()

            # Store brand and API key in request for use in views
            request.brand = api_key_obj.brand  # type: ignore
            request.api_key = api_key_obj  # type: ignore
            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error authenticating brand API: %s", e, exc_info=True)
            return JsonResponse({"error": "Authentication error"}, status=500)

    def _authenticate_product_api(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Authenticate product API request with license key.

        Args:
            request: HTTP request

        Returns:
            HttpResponse with 401 if auth fails, None if successful
        """
        # License key can be in header or query parameter
        license_key = (
            request.headers.get("X-License-Key")
            or request.GET.get("license_key")
            or request.headers.get("Authorization", "").replace("Bearer ", "")
        )

        if not license_key:
            return JsonResponse(
                {
                    "error": "Missing license key. Provide X-License-Key header "
                    "or license_key query param."
                },
                status=401,
            )

        if not LicenseKey:
            return JsonResponse({"error": "LicenseKey model not available"}, status=503)

        # Hash the license key for comparison
        license_key_hash = hashlib.sha256(license_key.encode()).hexdigest()

        try:
            # pylint: disable=no-member
            license_key_obj = LicenseKey.objects.filter(key_hash=license_key_hash).first()
            if not license_key_obj:
                logger.warning("Invalid license key attempted: %s...", license_key[:8])
                return JsonResponse({"error": "Invalid license key"}, status=401)

            # Store license key in request for use in views
            request.license_key = license_key_obj  # type: ignore
            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error authenticating product API: %s", e, exc_info=True)
            return JsonResponse({"error": "Authentication error"}, status=500)
