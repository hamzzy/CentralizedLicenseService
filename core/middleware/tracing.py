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
        if isinstance(data, list):
            return [
                self._sanitize_dict(item, max_depth - 1) for item in data[:10]
            ]  # Limit list size
        return str(data)[:500]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request with tracing."""
        # Check if tracer is available (NoOpTracer if OpenTelemetry not available)
        if not hasattr(tracer, "start_as_current_span") or not callable(
            getattr(tracer, "start_as_current_span", None)
        ):
            return self.get_response(request)

        span_name = f"{request.method} {request.path}"
        with tracer.start_as_current_span(span_name) as span:
            self._set_request_attributes(span, request)
            self._process_request_body(span, request)

            # Store trace_id on request for error responses
            if hasattr(span, "get_span_context") and callable(span.get_span_context):
                trace_context = span.get_span_context()
                if trace_context and hasattr(trace_context, "trace_id"):
                    request.trace_id = format(trace_context.trace_id, "032x")

            start_time = time.time()
            try:
                response = self.get_response(request)
                self._set_response_attributes(span, response, time.time() - start_time)
                return response
            except Exception as e:
                self._handle_exception(span, request, e, time.time() - start_time)
                raise

    def _set_request_attributes(self, span, request: HttpRequest):
        """Set attributes from the request."""
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.build_absolute_uri())
        span.set_attribute("http.route", request.path)
        span.set_attribute("http.user_agent", request.META.get("HTTP_USER_AGENT", ""))
        span.set_attribute("http.remote_addr", request.META.get("REMOTE_ADDR", ""))
        span.set_attribute("http.scheme", request.scheme)

        if hasattr(request, "headers"):
            if "Content-Type" in request.headers:
                span.set_attribute("http.request.content_type", request.headers["Content-Type"])
            if "X-API-Key" in request.headers:
                span.set_attribute("http.request.has_api_key", True)
            if "X-License-Key" in request.headers:
                span.set_attribute("http.request.has_license_key", True)

        if request.GET:
            for key, value in list(request.GET.items())[:10]:
                if key.lower() not in ["password", "secret", "token", "key", "api_key"]:
                    val = value[0] if isinstance(value, list) else value
                    span.set_attribute(f"http.request.query.{key}", str(val))

        # Add context if available
        for attr in ["tenant_id", "brand", "license_key"]:
            val = getattr(request, attr, None)
            if val:
                if attr == "brand":
                    span.set_attribute("brand.id", str(val.id))
                    span.set_attribute("brand.name", str(val.name))
                elif attr == "license_key":
                    span.set_attribute("license_key.id", str(val.id))
                    span.set_attribute("license_key.customer_email", str(val.customer_email))
                else:
                    span.set_attribute(f"{attr.replace('_', '.')}", str(val))

    def _process_request_body(self, span, request: HttpRequest):
        """Process and sanitize request body."""
        try:
            if hasattr(request, "body") and request.body:
                import json

                body_str = request.body.decode("utf-8", errors="ignore")
                span.set_attribute("http.request.body_size", len(body_str))

                if len(body_str) > 10000:
                    body_str = body_str[:10000] + "... (truncated)"

                try:
                    body_json = json.loads(body_str)
                    sanitized = self._sanitize_dict(body_json)
                    span.set_attribute("http.request.body", json.dumps(sanitized)[:5000])
                except (json.JSONDecodeError, ValueError):
                    span.set_attribute("http.request.body", body_str[:1000])
        except Exception:
            pass

    def _set_response_attributes(self, span, response, duration: float):
        """Set attributes from the response."""
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.duration_ms", round(duration * 1000, 2))
        if hasattr(response, "content") and response.content:
            span.set_attribute("http.response_size", len(response.content))
            self._process_response_body(span, response)

        # Set span status
        from core.instrumentation import Status, StatusCode

        if response.status_code >= 400:
            span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
        else:
            span.set_status(Status(StatusCode.OK))

    def _process_response_body(self, span, response):
        """Process and sanitize response body."""
        try:
            import json

            content_type = response.get("Content-Type", "")
            if content_type:
                span.set_attribute("http.response.content_type", content_type)

            response_body = response.content.decode("utf-8", errors="ignore")
            max_size = 10000 if response.status_code >= 400 else 2000
            try:
                body_json = json.loads(response_body)
                sanitized = self._sanitize_dict(body_json)
                span.set_attribute("http.response.body", json.dumps(sanitized)[:max_size])
                self._extract_error_details(span, response, body_json)
            except (json.JSONDecodeError, ValueError):
                span.set_attribute("http.response.body", response_body[:max_size])
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def _extract_error_details(self, span, response, body_json):
        """Extract error details from response JSON."""
        if response.status_code >= 400 and isinstance(body_json, dict):
            error_info = body_json.get("error", {})
            if isinstance(error_info, dict):
                for key in ["code", "message", "type"]:
                    if key in error_info:
                        span.set_attribute(f"error.{key}", str(error_info[key]))

    def _handle_exception(self, span, _request, e: Exception, duration: float):
        """Handle exception and update span."""
        import traceback

        from core.instrumentation import Status, StatusCode

        span.set_attribute("http.duration_ms", round(duration * 1000, 2))
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(e).__name__)
        span.set_attribute("error.message", str(e))

        try:
            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            span.set_attribute("error.stack_trace", tb_str[:10000])
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        span.set_status(Status(StatusCode.ERROR, f"{type(e).__name__}: {str(e)}"))
