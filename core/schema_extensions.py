"""
Custom schema extensions for drf-spectacular to add API key authentication.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class ApiKeyAuthenticationExtension(OpenApiAuthenticationExtension):
    """Extension to add API key authentication to OpenAPI schema."""

    target_class = "core.middleware.auth.APIKeyAuthenticationMiddleware"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        """Return security scheme definition."""
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for brand authentication. Get your API key from the brand admin panel.",
        }
