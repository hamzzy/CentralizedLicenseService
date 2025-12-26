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

from core.domain.exceptions import (
    DomainException,
    LicenseNotFoundError,
    BrandNotFoundError,
    ActivationNotFoundError,
    InvalidLicenseKeyError,
    InvalidAPIKeyError,
)

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
    2. Adds error codes and trace IDs to headers
    3. Logs errors appropriately
    4. Returns consistent error format

    Args:
        exc: The exception that was raised
        context: Context dictionary with request, view, etc.

    Returns:
        Response with error details
    """
    # Get trace ID from request if available (for Tempo integration)
    request = context.get("request")
    trace_id = None
    if request:
        # Try to get trace_id from request attributes (set by tracing middleware)
        trace_id = getattr(request, "trace_id", None)
        # Fallback to correlation_id if trace_id not available
        if not trace_id:
            trace_id = getattr(request, "correlation_id", None)

    # Handle domain exceptions
    if isinstance(exc, DomainException):
        status_code = status.HTTP_400_BAD_REQUEST
        
        # Map specific exceptions to status codes
        if isinstance(exc, (LicenseNotFoundError, BrandNotFoundError, ActivationNotFoundError)):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, (InvalidLicenseKeyError, InvalidAPIKeyError)):
            status_code = status.HTTP_401_UNAUTHORIZED
            
        logger.warning(
            f"Domain exception: {exc.code} - {exc.message}",
            extra={"trace_id": trace_id},
        )
        
        # Error body never includes trace_id (always in header)
        error_data = {
            "code": exc.code,
            "message": exc.message,
        }
        
        response = Response(
            {"error": error_data},
            status=status_code,
        )
        
        # Always add trace_id to headers
        if trace_id:
            response["X-Trace-ID"] = trace_id
        
        return response

    # Handle API exceptions
    if isinstance(exc, APIException):
        response = exception_handler(exc, context)
        if response:
            error_data = {
                "code": exc.default_code.upper().replace("-", "_") if hasattr(exc, 'default_code') else "API_ERROR",
                "message": response.data.get("detail", exc.default_detail),
            }
            
            response.data = {"error": error_data}
            
            if trace_id:
                response["X-Trace-ID"] = trace_id
            
            return response

    # Handle 404
    if isinstance(exc, Http404):
        error_data = {
            "code": "NOT_FOUND",
            "message": "Resource not found",
        }
        
        response = Response(
            {"error": error_data},
            status=status.HTTP_404_NOT_FOUND,
        )
        
        if trace_id:
            response["X-Trace-ID"] = trace_id
        
        return response

    # Handle unexpected errors
    logger.error(
        f"Unexpected error: {exc}",
        extra={"trace_id": trace_id},
        exc_info=True,
    )

    # Use default DRF exception handler
    response = exception_handler(exc, context)
    if response:
        error_data = {
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
        }
        
        response.data = {"error": error_data}
        
        if trace_id:
            response["X-Trace-ID"] = trace_id
        
        return response

    # Fallback for unhandled exceptions
    error_data = {
        "code": "INTERNAL_ERROR",
        "message": "An internal error occurred",
    }
    
    response = Response(
        {"error": error_data},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    
    if trace_id:
        response["X-Trace-ID"] = trace_id
    
    return response
