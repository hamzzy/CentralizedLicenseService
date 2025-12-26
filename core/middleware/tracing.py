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
            # Add span attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", request.build_absolute_uri())
            span.set_attribute("http.route", request.path)
            span.set_attribute("http.user_agent", request.META.get("HTTP_USER_AGENT", ""))

            # Add tenant context if available
            tenant_id = getattr(request, "tenant_id", None)
            if tenant_id:
                span.set_attribute("tenant.id", str(tenant_id))

            # Add brand context if available
            brand = getattr(request, "brand", None)
            if brand:
                span.set_attribute("brand.id", str(brand.id))
                span.set_attribute("brand.name", brand.name)

            # Process request
            start_time = time.time()
            response = self.get_response(request)
            duration = time.time() - start_time

            # Add response attributes
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response_size", len(response.content))
            span.set_attribute("http.duration_ms", duration * 1000)

            # Set span status
            if response.status_code >= 500:
                span.set_status(trace.Status(trace.StatusCode.ERROR))
            elif response.status_code >= 400:
                span.set_status(trace.Status(trace.StatusCode.ERROR))

            return response

