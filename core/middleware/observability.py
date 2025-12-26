"""
Observability middleware.

This middleware adds logging, metrics, and request tracing.
"""
import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


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

        # Log request
        start_time = time.time()
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.path,
                "remote_addr": request.META.get("REMOTE_ADDR"),
            },
        )

        # Process request
        try:
            response = self.get_response(request)
            duration = time.time() - start_time

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            # Add correlation ID to response headers
            response["X-Correlation-ID"] = correlation_id
            response["X-Request-Duration"] = f"{duration:.3f}"

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,
            )
            raise

