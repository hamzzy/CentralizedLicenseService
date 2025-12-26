"""
Metrics middleware for Prometheus.

Records HTTP request metrics for monitoring.
"""

import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

from core.metrics import (
    http_request_duration_seconds,
    http_requests_total,
)


class MetricsMiddleware:
    """
    Middleware to record HTTP metrics for Prometheus.

    Records:
    - Request count by method, endpoint, status
    - Request duration histogram
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request and record metrics."""
        start_time = time.time()

        # Extract endpoint (remove query params and normalize)
        endpoint = request.path.split("?")[0]
        # Normalize UUIDs in paths for better metric aggregation
        import re
        endpoint = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", endpoint)
        endpoint = re.sub(r"/\d+", "/{id}", endpoint)

        try:
            # Process request
            response = self.get_response(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code,
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)

            return response
        except Exception as e:
            # Calculate duration even on error
            duration = time.time() - start_time
            
            # Record error metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=500,
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)
            
            raise
