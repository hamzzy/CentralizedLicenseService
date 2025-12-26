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
        # Check if tracer is available
        # (NoOpTracer if OpenTelemetry not available)
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
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            span.set_attribute("http.user_agent", user_agent)
            remote_addr = request.META.get("REMOTE_ADDR", "")
            span.set_attribute("http.remote_addr", remote_addr)
            span.set_attribute("http.scheme", request.scheme)

            # Add request headers (excluding sensitive ones)
            if hasattr(request, "headers"):
                content_type = request.headers.get("Content-Type", "")
                if content_type:
                    attr = "http.request.content_type"
                    span.set_attribute(attr, content_type)

                # Add API key presence (but not the value)
                if "X-API-Key" in request.headers:
                    span.set_attribute("http.request.has_api_key", True)
                if "X-License-Key" in request.headers:
                    has_license_key = True
                    attr = "http.request.has_license_key"
                    span.set_attribute(attr, has_license_key)

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
                        attr_key = f"http.request.query.{key}"
                        span.set_attribute(attr_key, str(param_value))

            # Add request body (sanitized, limited size)
            try:
                if hasattr(request, "body") and request.body:
                    body_str = request.body.decode("utf-8", errors="ignore")
                    # Limit body size to avoid huge payloads
                    max_body_size = 10000
                    if len(body_str) > max_body_size:
                        body_str = body_str[:max_body_size] + "... (truncated)"
                    # Sanitize sensitive fields
                    import json

                    try:
                        body_json = json.loads(body_str)
                        sanitized = self._sanitize_dict(body_json)
                        sanitized_json = json.dumps(sanitized)
                        body_attr = "http.request.body"
                        span.set_attribute(body_attr, sanitized_json[:5000])
                        body_size_attr = "http.request.body_size"
                        span.set_attribute(body_size_attr, len(body_str))
                    except (json.JSONDecodeError, ValueError):
                        # Not JSON, just store first 1000 chars
                        body_attr = "http.request.body"
                        span.set_attribute(body_attr, body_str[:1000])
                        body_size_attr = "http.request.body_size"
                        span.set_attribute(body_size_attr, len(body_str))
            except Exception:
                # Ignore errors reading body
                pass

            # Add tenant context if available
            tenant_id = getattr(request, "tenant_id", None)
            if tenant_id:
                tenant_attr = "tenant.id"
                span.set_attribute(tenant_attr, str(tenant_id))

            # Add brand context if available
            brand = getattr(request, "brand", None)
            if brand:
                span.set_attribute("brand.id", str(brand.id))
                span.set_attribute("brand.name", brand.name)

            # Add license key context if available
            license_key = getattr(request, "license_key", None)
            if license_key:
                key_id_attr = "license_key.id"
                span.set_attribute(key_id_attr, str(license_key.id))
                email = license_key.customer_email
                email_attr = "license_key.customer_email"
                span.set_attribute(email_attr, email)

            # Store trace_id on request for error responses (Tempo integration)
            if hasattr(span, 'get_span_context') and callable(span.get_span_context):
                trace_context = span.get_span_context()
                if trace_context and hasattr(trace_context, 'trace_id'):
                    trace_id_hex = format(trace_context.trace_id, '032x')
                    request.trace_id = trace_id_hex

            # Process request
            start_time = time.time()
            try:
                response = self.get_response(request)
                duration = time.time() - start_time

                # Add response span attributes
                span.set_attribute("http.status_code", response.status_code)
                response_size = len(response.content)
                span.set_attribute("http.response_size", response_size)
                duration_ms = round(duration * 1000, 2)
                span.set_attribute("http.duration_ms", duration_ms)

                # Add response content type
                content_type = response.get("Content-Type", "")
                if content_type:
                    attr = "http.response.content_type"
                    span.set_attribute(attr, content_type)

                # Add response body (for all responses, more detail for errors)
                try:
                    if hasattr(response, "content") and response.content:
                        response_body = response.content.decode(
                            "utf-8", errors="ignore"
                        )
                        # For successful responses, limit size more
                        max_size = (
                            10000 if response.status_code >= 400 else 2000
                        )
                        if len(response_body) > max_size:
                            truncated = "... (truncated)"
                            response_body = (
                                response_body[:max_size] + truncated
                            )

                        # Sanitize response body
                        import json
                        try:
                            body_json = json.loads(response_body)
                            sanitized = self._sanitize_dict(body_json)
                            sanitized_str = json.dumps(sanitized)[:max_size]
                            body_attr = "http.response.body"
                            span.set_attribute(body_attr, sanitized_str)

                            # Extract error details if JSON and error response
                            is_error = response.status_code >= 400
                            if is_error and isinstance(body_json, dict):
                                if "error" in body_json:
                                    error_info = body_json["error"]
                                    if isinstance(error_info, dict):
                                        code = error_info.get("code", "")
                                        error_code = str(code)
                                        code_attr = "error.code"
                                        span.set_attribute(
                                            code_attr, error_code
                                        )
                                        msg = error_info.get("message", "")
                                        error_msg = str(msg)
                                        msg_attr = "error.message"
                                        span.set_attribute(
                                            msg_attr, error_msg
                                        )
                                        # Add error type if available
                                        if "type" in error_info:
                                            err_type = error_info.get("type")
                                            error_type = str(err_type)
                                            span.set_attribute(
                                                "error.type", error_type
                                            )
                        except (json.JSONDecodeError, ValueError):
                            # Not JSON, just store sanitized string
                            body_attr = "http.response.body"
                            span.set_attribute(
                                body_attr, response_body[:max_size]
                            )
                except Exception:
                    pass

                # Add request status information
                request_status = (
                    "success" if response.status_code < 400 else "error"
                )
                if response.status_code >= 500:
                    request_status = "server_error"
                elif response.status_code >= 400:
                    request_status = "client_error"

                span.set_attribute("request.status", request_status)
                span.set_attribute("request.status_code", response.status_code)

                # Add correlation ID if available (for traceability)
                correlation_id = getattr(request, "correlation_id", None)
                if correlation_id:
                    span.set_attribute("correlation.id", str(correlation_id))

                # Set span status based on HTTP status code
                from core.instrumentation import Status, StatusCode

                if response.status_code >= 500:
                    status_code = response.status_code
                    error_msg = f"HTTP {status_code} - Server Error"
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                elif response.status_code >= 400:
                    status_code = response.status_code
                    error_msg = f"HTTP {status_code} - Client Error"
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                else:
                    span.set_status(Status(StatusCode.OK))

                return response
            except Exception as e:
                duration = time.time() - start_time
                duration_ms = round(duration * 1000, 2)
                span.set_attribute("http.duration_ms", duration_ms)
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_attribute("request.status", "exception")
                span.set_attribute("request.status_code", 500)

                # Add exception details with stack trace
                import traceback

                try:
                    tb_str = "".join(
                        traceback.format_exception(
                            type(e), e, e.__traceback__
                        )
                    )
                    # Limit stack trace size
                    if len(tb_str) > 10000:
                        tb_str = tb_str[:10000] + "... (truncated)"
                    span.set_attribute("error.stack_trace", tb_str)

                    # Add exception attributes if available
                    if hasattr(e, "code"):
                        span.set_attribute("error.code", str(e.code))
                    if hasattr(e, "message"):
                        span.set_attribute("error.message", str(e.message))
                    if hasattr(e, "status_code"):
                        status_code = str(e.status_code)
                        span.set_attribute("error.status_code", status_code)

                    # Add request context for debugging
                    span.set_attribute("error.request_method", request.method)
                    span.set_attribute("error.request_path", request.path)
                except Exception:
                    pass

                from core.instrumentation import Status, StatusCode

                error_type = type(e).__name__
                error_description = f"{error_type}: {str(e)}"
                span.set_status(Status(StatusCode.ERROR, error_description))
                raise
