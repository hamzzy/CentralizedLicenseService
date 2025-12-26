"""
Rate limiting middleware.

Implements rate limiting per API key with configurable limits.
"""

import time
from typing import Callable, Optional, Tuple

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone

from core.metrics import errors_total


class RateLimitMiddleware:
    """
    Rate limiting middleware per API key.

    Rate limits are configured per API key and stored in cache.
    Default limits: 100 requests per minute per API key.
    """

    # Default rate limits (requests per window)
    DEFAULT_RATE_LIMIT = 100  # requests per minute
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def _get_api_key(self, request: HttpRequest) -> Optional[str]:
        """
        Extract API key from request.

        Checks X-API-Key header or Authorization header.

        Args:
            request: HTTP request

        Returns:
            API key string or None
        """
        api_key = request.META.get("HTTP_X_API_KEY")
        if api_key:
            return api_key

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        return None

    def _get_rate_limit_key(self, api_key: str) -> str:
        """
        Generate cache key for rate limiting.

        Args:
            api_key: API key string

        Returns:
            Cache key string
        """
        # Hash API key for cache key (don't store raw key)
        import hashlib

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"rate_limit:{key_hash}"

    def _check_rate_limit(self, api_key: str, limit: int = None) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            api_key: API key string
            limit: Rate limit (defaults to DEFAULT_RATE_LIMIT)

        Returns:
            Tuple of (is_allowed, remaining, reset_time)
        """
        if limit is None:
            limit = self.DEFAULT_RATE_LIMIT

        cache_key = self._get_rate_limit_key(api_key)
        window_start = int(time.time() / self.RATE_LIMIT_WINDOW)

        # Get current count
        current_count = cache.get(f"{cache_key}:{window_start}", 0)

        if current_count >= limit:
            # Rate limit exceeded
            reset_time = (window_start + 1) * self.RATE_LIMIT_WINDOW
            return False, 0, reset_time

        # Increment counter
        # Use get_or_set to ensure key exists before incrementing
        full_key = f"{cache_key}:{window_start}"
        try:
            new_count = cache.incr(full_key, 1)
        except ValueError:
            # Key doesn't exist, create it with initial value of 1
            cache.set(full_key, 1, timeout=self.RATE_LIMIT_WINDOW)
            new_count = 1

        remaining = max(0, limit - new_count)
        reset_time = (window_start + 1) * self.RATE_LIMIT_WINDOW

        return True, remaining, reset_time

    def _get_rate_limit_for_api_key(self, api_key: str) -> int:
        """
        Get rate limit for specific API key.

        Can be extended to fetch from database or configuration.

        Args:
            api_key: API key string

        Returns:
            Rate limit (requests per window)
        """
        # TODO: Fetch from ApiKey model or configuration
        # For now, return default
        return self.DEFAULT_RATE_LIMIT

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process request with rate limiting.

        Args:
            request: HTTP request

        Returns:
            HTTP response with rate limit headers
        """
        # Skip rate limiting for health checks and admin
        if request.path.startswith(
            ("/health", "/ready", "/admin", "/api/docs", "/api/redoc", "/api/schema")
        ):
            return self.get_response(request)

        # Only rate limit brand APIs (they have API keys)
        if not request.path.startswith("/api/v1/brand"):
            return self.get_response(request)

        # Get API key
        api_key = self._get_api_key(request)
        if not api_key:
            # No API key, let auth middleware handle it
            return self.get_response(request)

        # Get rate limit for this API key
        limit = self._get_rate_limit_for_api_key(api_key)

        # Check rate limit
        is_allowed, remaining, reset_time = self._check_rate_limit(api_key, limit)

        if not is_allowed:
            # Rate limit exceeded
            errors_total.labels(error_type="rate_limit_exceeded", endpoint=request.path).inc()

            response = JsonResponse(
                {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded. Please try again later.",
                    }
                },
                status=429,
            )
        else:
            # Process request
            response = self.get_response(request)

        # Add rate limit headers (RFC 6585)
        response["X-RateLimit-Limit"] = str(limit)
        response["X-RateLimit-Remaining"] = str(remaining)
        response["X-RateLimit-Reset"] = str(reset_time)
        response["Retry-After"] = str(max(0, reset_time - int(time.time())))

        return response
