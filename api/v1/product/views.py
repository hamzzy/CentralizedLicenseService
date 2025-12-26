"""
Product API views - US3, US4, US5.

These endpoints are used by end-user products to:
- Activate licenses
- Check license status
- Deactivate seats
"""

import hashlib
import uuid

from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from activations.application.commands.activate_license import ActivateLicenseCommand
from activations.application.commands.deactivate_seat import DeactivateSeatCommand
from activations.application.handlers.activate_license_handler import ActivateLicenseHandler
from activations.application.handlers.deactivate_seat_handler import DeactivateSeatHandler
from activations.infrastructure.repositories.django_activation_repository import (
    DjangoActivationRepository,
)
from api.exceptions import APIError
from api.v1.product.serializers import (
    ActivateLicenseRequestSerializer,
    ActivateLicenseResponseSerializer,
    DeactivateSeatRequestSerializer,
    LicenseStatusResponseSerializer,
)
from brands.infrastructure.repositories.django_product_repository import DjangoProductRepository
from core.domain.exceptions import DomainException
from core.domain.value_objects import InstanceType
from core.instrumentation import Status, StatusCode, get_tracer
from licenses.application.handlers.get_license_status_handler import GetLicenseStatusHandler
from licenses.application.queries.get_license_status import GetLicenseStatusQuery
from licenses.infrastructure.repositories.django_license_key_repository import (
    DjangoLicenseKeyRepository,
)
from licenses.infrastructure.repositories.django_license_repository import DjangoLicenseRepository

# Initialize repositories (in production, use DI container)
_license_key_repo = DjangoLicenseKeyRepository()
_license_repo = DjangoLicenseRepository()
_product_repo = DjangoProductRepository()
_activation_repo = DjangoActivationRepository()

tracer = get_tracer(__name__)


class ActivateLicenseView(APIView):
    """View for activating licenses - US3."""

    @extend_schema(
        operation_id="activate_license",
        summary="Activate License",
        description=(
            "Activate a license on a specific instance (URL, hostname, or machine ID). "
            "This consumes a seat from the license's seat limit."
        ),
        tags=["Product API"],
        parameters=[
            OpenApiParameter(
                name="X-License-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="License key for product authentication",
            ),
        ],
        request=ActivateLicenseRequestSerializer,
        responses={
            201: ActivateLicenseResponseSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "License key not found"},
            409: {"description": "License already activated on this instance"},
            422: {"description": "License invalid, expired, or seat limit exceeded"},
        },
    )
    def post(self, request: Request) -> Response:
        """Activate a license for an instance - US3."""
        return async_to_sync(self._handle_activate_license)(request)

    async def _handle_activate_license(self, request: Request) -> Response:
        """Async handler for activate license."""
        with tracer.start_as_current_span("activate_license") as span:
            span.set_attribute("operation", "activate_license")

            serializer = ActivateLicenseRequestSerializer(data=request.data)
            if not serializer.is_valid():
                span.set_attribute("error", "validation_failed")
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            # Get license key from request (set by middleware)
            license_key_obj = getattr(request, "license_key", None)
            if not license_key_obj:
                span.set_attribute("error", "license_key_not_found")
                span.set_status(Status(StatusCode.ERROR, "License key not found"))
                return Response(
                    {"error": "License key not found"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            license_key = license_key_obj.key
            span.set_attribute("license_key", license_key)
            span.set_attribute("product_slug", serializer.validated_data["product_slug"])
            span.set_attribute(
                "instance_identifier", serializer.validated_data["instance_identifier"]
            )
            span.set_attribute("instance_type", serializer.validated_data["instance_type"])

            handler = ActivateLicenseHandler(
                license_key_repository=_license_key_repo,
                license_repository=_license_repo,
                product_repository=_product_repo,
                activation_repository=_activation_repo,
            )

            # Map instance type string to enum
            instance_type_map = {
                "url": InstanceType.URL,
                "hostname": InstanceType.HOSTNAME,
                "machine_id": InstanceType.MACHINE_ID,
            }
            instance_type = instance_type_map.get(serializer.validated_data["instance_type"])
            if not instance_type:
                span.set_attribute("error", "invalid_instance_type")
                span.set_status(Status(StatusCode.ERROR, "Invalid instance type"))
                return Response(
                    {"error": "Invalid instance_type"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            command = ActivateLicenseCommand(
                license_key=license_key,
                product_slug=serializer.validated_data["product_slug"],
                instance_identifier=serializer.validated_data["instance_identifier"],
                instance_type=instance_type,
                instance_metadata=serializer.validated_data.get("instance_metadata", {}),
            )

            result = await handler.handle(command)

            response_serializer = ActivateLicenseResponseSerializer(result)
            span.set_attribute("activation.id", str(result.activation_id))
            span.set_attribute("license.id", str(result.license_id))
            span.set_status(Status(StatusCode.OK))

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class GetLicenseStatusView(APIView):
    """View for checking license status - US4."""

    @extend_schema(
        operation_id="get_license_status",
        summary="Check License Status",
        description=(
            "Verify license validity and seat availability for a specific instance. "
            "Returns license details and activation status. "
            "Requires either X-License-Key header or license_key query parameter."
        ),
        tags=["Product API"],
        parameters=[
            OpenApiParameter(
                name="X-License-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
                description="License key for product authentication (provide either this or license_key query parameter)",
            ),
            OpenApiParameter(
                name="license_key",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="License key string (provide either this or X-License-Key header)",
            ),
            OpenApiParameter(
                name="instance_identifier",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Instance identifier to check activation status",
            ),
        ],
        responses={
            200: LicenseStatusResponseSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "License key not found"},
            422: {"description": "License invalid, expired, or suspended"},
        },
    )
    def get(self, request: Request) -> Response:
        """Get license status and entitlements - US4."""
        return async_to_sync(self._handle_get_license_status)(request)

    async def _handle_get_license_status(self, request: Request) -> Response:
        """Async handler for get license status."""
        with tracer.start_as_current_span("get_license_status") as span:
            span.set_attribute("operation", "get_license_status")

            license_key = request.query_params.get("license_key") or request.headers.get(
                "X-License-Key"
            )

            if not license_key:
                span.set_attribute("error", "license_key_required")
                span.set_status(Status(StatusCode.ERROR, "License key required"))
                return Response(
                    {"error": "license_key parameter or X-License-Key header required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            span.set_attribute("license_key", license_key)
            instance_identifier = request.query_params.get("instance_identifier")
            if instance_identifier:
                span.set_attribute("instance_identifier", instance_identifier)

            handler = GetLicenseStatusHandler(
                license_key_repository=_license_key_repo,
                license_repository=_license_repo,
                product_repository=_product_repo,
                activation_repository=_activation_repo,
            )

            query = GetLicenseStatusQuery(license_key=license_key)

            result = await handler.handle(query)

            serializer = LicenseStatusResponseSerializer(result)
            span.set_attribute("status", result.status)
            span.set_attribute("is_valid", str(result.is_valid))
            span.set_attribute("licenses.count", len(result.licenses))
            span.set_status(Status(StatusCode.OK))

            return Response(serializer.data, status=status.HTTP_200_OK)


class DeactivateSeatView(APIView):
    """View for deactivating seats - US5."""

    @extend_schema(
        operation_id="deactivate_seat",
        summary="Deactivate Seat",
        description=(
            "Release a seat for reuse. This deactivates the license on a specific instance. "
            "The seat becomes available for activation on another instance."
        ),
        tags=["Product API"],
        parameters=[
            OpenApiParameter(
                name="X-License-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="License key for product authentication",
            ),
        ],
        request=DeactivateSeatRequestSerializer,
        responses={
            200: {"description": "Seat deactivated successfully"},
            400: {"description": "Bad Request"},
            404: {"description": "License key or activation not found"},
        },
    )
    def delete(self, request: Request, activation_id: uuid.UUID) -> Response:
        """Deactivate a seat - US5."""
        return async_to_sync(self._handle_deactivate_seat)(request, activation_id)

    async def _handle_deactivate_seat(self, request: Request, activation_id: uuid.UUID) -> Response:
        """Async handler for deactivate seat."""
        with tracer.start_as_current_span("deactivate_seat") as span:
            span.set_attribute("operation", "deactivate_seat")
            span.set_attribute("activation.id", str(activation_id))

            # Get license key from request (set by middleware)
            license_key_obj = getattr(request, "license_key", None)
            if not license_key_obj:
                span.set_attribute("error", "license_key_not_found")
                span.set_status(Status(StatusCode.ERROR, "License key not found"))
                return Response(
                    {"error": "License key not found"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            license_key = license_key_obj.key
            span.set_attribute("license_key", license_key)

            # Find activation by ID
            activation = await _activation_repo.find_by_id(activation_id)
            if not activation:
                span.set_attribute("error", "activation_not_found")
                span.set_status(Status(StatusCode.ERROR, "Activation not found"))
                response = Response(
                    {"error": {"code": "ACTIVATION_NOT_FOUND", "message": "Activation not found"}},
                    status=status.HTTP_404_NOT_FOUND,
                )
                if hasattr(request, "trace_id") and request.trace_id:
                    response["X-Trace-ID"] = request.trace_id
                return response

            # Verify the activation belongs to a license with the provided license key
            license_obj = await _license_repo.find_by_id(activation.license_id)
            if not license_obj:
                span.set_attribute("error", "license_not_found")
                span.set_status(Status(StatusCode.ERROR, "License not found"))
                response = Response(
                    {"error": {"code": "LICENSE_NOT_FOUND", "message": "License not found"}},
                    status=status.HTTP_404_NOT_FOUND,
                )
                if hasattr(request, "trace_id") and request.trace_id:
                    response["X-Trace-ID"] = request.trace_id
                return response

            # Verify license belongs to this license key
            if license_obj.license_key_id != license_key_obj.id:
                span.set_attribute("error", "license_key_mismatch")
                span.set_status(Status(StatusCode.ERROR, "License key mismatch"))
                response = Response(
                    {
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "License key does not match activation",
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
                if hasattr(request, "trace_id") and request.trace_id:
                    response["X-Trace-ID"] = request.trace_id
                return response

            handler = DeactivateSeatHandler(
                license_key_repository=_license_key_repo,
                activation_repository=_activation_repo,
            )

            command = DeactivateSeatCommand(
                license_key=license_key,
                instance_identifier=activation.instance_identifier,
            )

            span.set_attribute("instance_identifier", activation.instance_identifier)

            await handler.handle(command)

            span.set_status(Status(StatusCode.OK))
            return Response(
                {"message": "Seat deactivated successfully", "status": "deactivated"},
                status=status.HTTP_200_OK,
            )
