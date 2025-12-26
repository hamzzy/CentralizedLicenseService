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

    def _sanitize_dict(self, data, max_depth=3):
        """Sanitize dictionary by removing sensitive fields."""
        if max_depth <= 0:
            return "..."
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = str(key).lower()
                if any(
                    sensitive in key_lower
                    for sensitive in [
                        "password",
                        "secret",
                        "token",
                        "key",
                        "api_key",
                        "license_key",
                    ]
                ):
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_dict(value, max_depth - 1)
                else:
                    sanitized[key] = str(value)[:500]  # Limit string length
            return sanitized
        elif isinstance(data, list):
            return [
                self._sanitize_dict(item, max_depth - 1) for item in data[:10]
            ]  # Limit list size
        else:
            return str(data)[:500]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request with tracing."""
        # Check if tracer is available (NoOpTracer if OpenTelemetry not available)
        if not hasattr(tracer, "start_as_current_span") or not callable(
            getattr(tracer, "start_as_current_span", None)
        ):
            # Skip tracing if OpenTelemetry not available
            return self.get_response(request)

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
                        param_value = value[0] if isinstance(value, list) else value
                        span.set_attribute(f"http.request.query.{key}", str(param_value))

            # Add request body (sanitized, limited size)
            try:
                if hasattr(request, "body") and request.body:
                    body_str = request.body.decode("utf-8", errors="ignore")
                    # Limit body size to avoid huge payloads
                    if len(body_str) > 10000:
                        body_str = body_str[:10000] + "... (truncated)"
                    # Sanitize sensitive fields
                    import json

                    try:
                        body_json = json.loads(body_str)
                        sanitized = self._sanitize_dict(body_json)
                        span.set_attribute("http.request.body", json.dumps(sanitized)[:5000])
                    except (json.JSONDecodeError, ValueError):
                        # Not JSON, just store first 1000 chars
                        span.set_attribute("http.request.body", body_str[:1000])
            except Exception:
                # Ignore errors reading body
                pass

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

                # Add response body for errors (limited size)
                if response.status_code >= 400:
                    try:
                        if hasattr(response, "content"):
                            response_body = response.content.decode("utf-8", errors="ignore")
                            if len(response_body) > 5000:
                                response_body = response_body[:5000] + "... (truncated)"
                            span.set_attribute("http.response.body", response_body)
                            # Extract error details if JSON
                            try:
                                import json

                                error_json = json.loads(response_body)
                                if isinstance(error_json, dict):
                                    if "error" in error_json:
                                        error_info = error_json["error"]
                                        if isinstance(error_info, dict):
                                            span.set_attribute(
                                                "error.code", str(error_info.get("code", ""))
                                            )
                                            span.set_attribute(
                                                "error.message", str(error_info.get("message", ""))
                                            )
                            except (json.JSONDecodeError, ValueError):
                                pass
                    except Exception:
                        pass

                # Add correlation ID if available
                correlation_id = getattr(request, "correlation_id", None)
                if correlation_id:
                    span.set_attribute("correlation.id", str(correlation_id))

                # Set span status based on HTTP status code
                from core.instrumentation import Status, StatusCode

                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                elif response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                else:
                    span.set_status(Status(StatusCode.OK))

                return response
            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("http.duration_ms", round(duration * 1000, 2))
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))

                # Add exception details with stack trace
                import traceback

                try:
                    tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    # Limit stack trace size
                    if len(tb_str) > 10000:
                        tb_str = tb_str[:10000] + "... (truncated)"
                    span.set_attribute("error.stack_trace", tb_str)
                    # Add exception attributes if available
                    if hasattr(e, "code"):
                        span.set_attribute("error.code", str(e.code))
                    if hasattr(e, "status_code"):
                        span.set_attribute("error.status_code", str(e.status_code))
                except Exception:
                    pass

                from core.instrumentation import Status, StatusCode

                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
