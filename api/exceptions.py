"""
API exception handlers.

This module provides custom exception handling for REST API responses.
"""

import logging
from typing import Any, Dict, Optional

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.domain.exceptions import (
    ActivationNotFoundError,
    BrandNotFoundError,
    DomainException,
    InvalidAPIKeyError,
    InvalidLicenseKeyError,
    LicenseNotFoundError,
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
    """Custom exception handler for REST API."""
    trace_id = _get_trace_id(context)

    if isinstance(exc, DomainException):
        response = _handle_domain_exception(exc, trace_id)
        if trace_id:
            response["X-Trace-ID"] = trace_id
        return response

    if isinstance(exc, APIException):
        response = exception_handler(exc, context)
        if response:
            code = (
                exc.default_code.upper().replace("-", "_")
                if hasattr(exc, "default_code")
                else "API_ERROR"
            )
            response.data = {
                "error": {"code": code, "message": response.data.get("detail", exc.default_detail)}
            }
            if trace_id:
                response["X-Trace-ID"] = trace_id
            return response

    if isinstance(exc, Http404):
        response = Response(
            {"error": {"code": "NOT_FOUND", "message": "Resource not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )
        if trace_id:
            response["X-Trace-ID"] = trace_id
        return response

    return _handle_unexpected_exception(exc, context, trace_id)


def _get_trace_id(context: Dict[str, Any]) -> Optional[str]:
    """Extract trace ID from request context."""
    request = context.get("request")
    if not request:
        return None
    return getattr(request, "trace_id", getattr(request, "correlation_id", None))


def _handle_domain_exception(exc: DomainException, trace_id: Optional[str]) -> Response:
    """Handle domain-specific exceptions."""
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, (LicenseNotFoundError, BrandNotFoundError, ActivationNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, (InvalidLicenseKeyError, InvalidAPIKeyError)):
        status_code = status.HTTP_401_UNAUTHORIZED

    logger.warning("Domain exception: %s - %s", exc.code, exc.message, extra={"trace_id": trace_id})
    return Response({"error": {"code": exc.code, "message": exc.message}}, status=status_code)


def _handle_unexpected_exception(
    exc: Exception, context: Dict[str, Any], trace_id: Optional[str]
) -> Response:
    """Handle unexpected or untracked exceptions."""
    logger.error("Unexpected error: %s", exc, extra={"trace_id": trace_id}, exc_info=True)
    response = exception_handler(exc, context)
    if not response:
        response = Response(
            {"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    else:
        response.data = {
            "error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"}
        }
    if trace_id:
        response["X-Trace-ID"] = trace_id
    return response
