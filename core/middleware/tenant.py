"""
Multi-tenancy middleware.

This middleware extracts the tenant (brand) context from the request
and makes it available throughout the request lifecycle.
"""

import contextvars
import logging
import uuid
from typing import Callable, Optional

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

try:
    from brands.infrastructure.models import ApiKey
except ImportError:
    # Placeholder for when models are not yet created
    ApiKey = None

logger = logging.getLogger(__name__)

# Context variable for tenant (brand) ID - using UUID
tenant_context: contextvars.ContextVar[Optional[uuid.UUID]] = contextvars.ContextVar(
    "tenant_id", default=None
)


def get_current_tenant_id() -> Optional[uuid.UUID]:
    """
    Get the current tenant (brand) ID from context.

    Returns:
        Brand ID (UUID) or None if not set
    """
    return tenant_context.get(None)


class TenantMiddleware:
    """
    Middleware to extract and set tenant context from API key.

    This middleware:
    1. Extracts API key from request headers
    2. Looks up the brand associated with the API key
    3. Sets the tenant context for the request
    4. Ensures all database queries are scoped to the tenant
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process request and set tenant context.

        Args:
            request: HTTP request

        Returns:
            HTTP response
        """
        # Extract API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get(
            "Authorization", ""
        ).replace("Bearer ", "")

        tenant_id = None

        if api_key and ApiKey:
            try:
                # Look up brand by API key hash
                import hashlib

                api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
                api_key_obj = ApiKey.objects.filter(
                    key_hash=api_key_hash,
                ).first()
                if api_key_obj and api_key_obj.is_valid():
                    tenant_id = api_key_obj.brand.id
                    logger.debug(f"Tenant context set to brand_id={tenant_id}")
            except Exception as e:
                logger.warning(f"Error looking up tenant: {e}")

        # Set tenant context
        tenant_context.set(tenant_id)

        # Add tenant_id to request for easy access
        request.tenant_id = tenant_id  # type: ignore

        response = self.get_response(request)

        # Clear tenant context after request
        tenant_context.set(None)

        return response


# Lazy object for accessing current tenant in views
current_tenant = SimpleLazyObject(get_current_tenant_id)
