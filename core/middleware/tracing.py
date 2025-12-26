"""
Tracing middleware for OpenTelemetry.

Adds distributed tracing to all requests.
"""

import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

from core.instrumentation import get_tracer

tracer = get_tracer(__name__)


class TracingMiddleware:
    """
    Middleware to add distributed tracing to requests.

    Creates a span for each request and adds context to logs.
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request with tracing."""
        from opentelemetry import trace

        span_name = f"{request.method} {request.path}"
        with tracer.start_as_current_span(span_name) as span:
            # Add request span attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", request.build_absolute_uri())
            span.set_attribute("http.route", request.path)
            span.set_attribute("http.user_agent", request.META.get("HTTP_USER_AGENT", ""))
            span.set_attribute("http.remote_addr", request.META.get("REMOTE_ADDR", ""))
            span.set_attribute("http.scheme", request.scheme)

            # Add request headers (excluding sensitive ones)
            if hasattr(request, "headers"):
                content_type = request.headers.get("Content-Type", "")
                if content_type:
                    span.set_attribute("http.request.content_type", content_type)
                
                # Add API key presence (but not the value)
                if "X-API-Key" in request.headers:
                    span.set_attribute("http.request.has_api_key", True)
                if "X-License-Key" in request.headers:
                    span.set_attribute("http.request.has_license_key", True)

            # Add query parameters (for GET requests)
            if request.GET:
                query_params = dict(request.GET)
                # Limit query params to avoid too much data
                for key, value in list(query_params.items())[:10]:
                    # Skip sensitive params
                    if key not in ["password", "secret", "token"]:
                        param_value = (
                            value[0] if isinstance(value, list) else value
                        )
                        span.set_attribute(
                            f"http.request.query.{key}", str(param_value)
                        )

            # Add tenant context if available
            tenant_id = getattr(request, "tenant_id", None)
            if tenant_id:
                span.set_attribute("tenant.id", str(tenant_id))

            # Add brand context if available
            brand = getattr(request, "brand", None)
            if brand:
                span.set_attribute("brand.id", str(brand.id))
                span.set_attribute("brand.name", brand.name)

            # Add license key context if available
            license_key = getattr(request, "license_key", None)
            if license_key:
                span.set_attribute("license_key.id", str(license_key.id))
                span.set_attribute("license_key.customer_email", license_key.customer_email)

            # Process request
            start_time = time.time()
            try:
                response = self.get_response(request)
                duration = time.time() - start_time

                # Add response span attributes
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.response_size", len(response.content))
                span.set_attribute("http.duration_ms", round(duration * 1000, 2))

                # Add response content type
                content_type = response.get("Content-Type", "")
                if content_type:
                    span.set_attribute("http.response.content_type", content_type)

                # Add correlation ID if available
                correlation_id = getattr(request, "correlation_id", None)
                if correlation_id:
                    span.set_attribute("correlation.id", str(correlation_id))

                    # Set span status based on HTTP status code
                if response.status_code >= 500:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {response.status_code}"))
                elif response.status_code >= 400:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {response.status_code}"))
                else:
                    span.set_status(trace.Status(trace.StatusCode.OK))

                return response
            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("http.duration_ms", round(duration * 1000, 2))
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
