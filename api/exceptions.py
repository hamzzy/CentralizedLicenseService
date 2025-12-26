"""
API exception handlers.

This module provides custom exception handling for REST API responses.
"""

import logging
from typing import Any, Dict

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.domain.exceptions import DomainException

logger = logging.getLogger(__name__)


class APIError(APIException):
    """Base API exception with error code."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred"
    default_code = "api_error"

    def __init__(self, detail=None, code=None, status_code=None):
        """
        Initialize API error.

        Args:
            detail: Error message
            code: Error code
            status_code: HTTP status code
        """
        if status_code:
            self.status_code = status_code
        if code:
            self.default_code = code
        super().__init__(detail)


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Custom exception handler for REST API.

    This handler:
    1. Converts domain exceptions to API responses
    2. Adds error codes and correlation IDs
    3. Logs errors appropriately
    4. Returns consistent error format

    Args:
        exc: The exception that was raised
        context: Context dictionary with request, view, etc.

    Returns:
        Response with error details
    """
    # Get correlation ID from request if available
    request = context.get("request")
    correlation_id = getattr(request, "correlation_id", None) if request else None

    # Handle domain exceptions
    if isinstance(exc, DomainException):
        logger.warning(
            f"Domain exception: {exc.code} - {exc.message}",
            extra={"correlation_id": correlation_id},
        )
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "correlation_id": correlation_id,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Handle API exceptions
    if isinstance(exc, APIException):
        response = exception_handler(exc, context)
        if response:
            response.data = {
                "error": {
                    "code": exc.default_code,
                    "message": response.data.get("detail", exc.default_detail),
                    "correlation_id": correlation_id,
                }
            }
            return response

    # Handle 404
    if isinstance(exc, Http404):
        return Response(
            {
                "error": {
                    "code": "not_found",
                    "message": "Resource not found",
                    "correlation_id": correlation_id,
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Handle unexpected errors
    logger.error(
        f"Unexpected error: {exc}",
        extra={"correlation_id": correlation_id},
        exc_info=True,
    )

    # Use default DRF exception handler
    response = exception_handler(exc, context)
    if response:
        response.data = {
            "error": {
                "code": "internal_error",
                "message": "An internal error occurred",
                "correlation_id": correlation_id,
            }
        }
        return response

    # Fallback for unhandled exceptions
    return Response(
        {
            "error": {
                "code": "internal_error",
                "message": "An internal error occurred",
                "correlation_id": correlation_id,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
