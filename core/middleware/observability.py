"""
Observability middleware.

This middleware adds logging, metrics, and request tracing.
Integrates with Loki for log aggregation and OpenTelemetry for tracing.
"""

import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

try:
    try:
        from opentelemetry import trace
        from opentelemetry.trace import format_trace_id

        OPENTELEMETRY_AVAILABLE = True
    except ImportError:
        OPENTELEMETRY_AVAILABLE = False
        trace = None
        format_trace_id = None

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class ObservabilityMiddleware:
    """
    Middleware for request observability.

    This middleware:
    1. Generates correlation IDs for request tracing
    2. Logs request/response information
    3. Tracks request duration
    4. Adds correlation ID to response headers
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process request and add observability.

        Args:
            request: HTTP request

        Returns:
            HTTP response with observability headers
        """
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.correlation_id = correlation_id  # type: ignore

        # Get trace context if available
        trace_id = None
        span_id = None
        if OTEL_AVAILABLE and OPENTELEMETRY_AVAILABLE and trace and format_trace_id:
            try:
                span = trace.get_current_span()
                if span and span.get_span_context().is_valid:
                    trace_context = span.get_span_context()
                    trace_id = format_trace_id(trace_context.trace_id)
                    span_id = format_trace_id(trace_context.span_id)
            except Exception:  # pylint: disable=broad-exception-caught
                # OpenTelemetry not fully initialized, skip trace context
                pass

        # Log request (structured for Loki)
        start_time = time.time()
        log_extra = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.path,
            "remote_addr": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        if trace_id:
            log_extra["trace_id"] = trace_id
            log_extra["span_id"] = span_id

        logger.info("Request started", extra=log_extra)

        # Process request
        try:
            response = self.get_response(request)
            duration = time.time() - start_time

            # Determine request status
            request_status = self._get_request_status(response)

            # Log response
            self._log_response(
                request, response, correlation_id, request_status, duration, trace_id, span_id
            )

            # Add observability headers
            self._add_observability_headers(
                response, correlation_id, request_status, duration, trace_id
            )

            return response
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._handle_exception(request, e, start_time, correlation_id)
            raise

    def _get_request_status(self, response: HttpResponse) -> str:
        """Determine request status based on status code."""
        if response.status_code >= 500:
            return "server_error"
        if response.status_code >= 400:
            return "client_error"
        return "success"

    def _log_response(self, request, response, correlation_id, status, duration, trace_id, span_id):
        """Log structured response information."""
        log_extra = {
            "correlation_id": correlation_id,
            "request_status": status,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "response_size": len(response.content) if hasattr(response, "content") else 0,
        }
        if trace_id:
            log_extra["trace_id"] = trace_id
            log_extra["span_id"] = span_id

        # Add brand context
        brand = getattr(request, "brand", None)
        if brand:
            log_extra["brand_id"] = str(brand.id)
            log_extra["brand_name"] = brand.name

        # Add license key context
        license_key = getattr(request, "license_key", None)
        if license_key:
            log_extra["license_key_id"] = str(license_key.id)

        # Log based on status code
        if response.status_code >= 500:
            logger.error("Request completed with server error", extra=log_extra)
        elif response.status_code >= 400:
            logger.warning("Request completed with client error", extra=log_extra)
        else:
            logger.info("Request completed successfully", extra=log_extra)

    def _add_observability_headers(self, response, correlation_id, status, duration, trace_id):
        """Add observability headers to response."""
        response["X-Correlation-ID"] = correlation_id
        response["X-Request-Status"] = status
        response["X-Request-Duration"] = f"{duration:.3f}"
        if trace_id:
            response["X-Trace-ID"] = trace_id

    def _handle_exception(self, request, e, start_time, correlation_id):
        """Handle and log request exception."""
        duration = time.time() - start_time
        logger.error(
            "Request failed",
            extra={
                "correlation_id": correlation_id,
                "request_status": "exception",
                "method": request.method,
                "path": request.path,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration * 1000, 2),
            },
            exc_info=True,
        )
