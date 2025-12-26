"""
Product API views - US3, US4, US5.

These endpoints are used by end-user products to:
- Activate licenses
- Check license status
- Deactivate seats
"""
import uuid

from core.domain.value_objects import InstanceType
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from activations.application.commands.activate_license import (
    ActivateLicenseCommand,
)
from activations.application.commands.deactivate_seat import (
    DeactivateSeatCommand,
)
from activations.application.handlers.activate_license_handler import (
    ActivateLicenseHandler,
)
from activations.application.handlers.deactivate_seat_handler import (
    DeactivateSeatHandler,
)
from api.exceptions import APIError
from brands.infrastructure.repositories.django_product_repository import (
    DjangoProductRepository,
)
from core.domain.exceptions import DomainException
from licenses.application.handlers.get_license_status_handler import (
    GetLicenseStatusHandler,
)
from licenses.application.queries.get_license_status import (
    GetLicenseStatusQuery,
)
from licenses.infrastructure.repositories.django_license_key_repository import (
    DjangoLicenseKeyRepository,
)
from licenses.infrastructure.repositories.django_license_repository import (
    DjangoLicenseRepository,
)
from activations.infrastructure.repositories.django_activation_repository import (
    DjangoActivationRepository,
)
from api.v1.product.serializers import (
    ActivateLicenseRequestSerializer,
    ActivateLicenseResponseSerializer,
    DeactivateSeatRequestSerializer,
    LicenseStatusResponseSerializer,
)


# Initialize repositories (in production, use DI container)
_license_key_repo = DjangoLicenseKeyRepository()
_license_repo = DjangoLicenseRepository()
_product_repo = DjangoProductRepository()
_activation_repo = DjangoActivationRepository()


@api_view(["POST"])
async def activate_license(request: Request) -> Response:
    """
    Activate a license for an instance - US3.

    POST /api/v1/product/activate
    """
    serializer = ActivateLicenseRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    # Get license key from request (set by middleware)
    license_key_obj = getattr(request, "license_key", None)
    if not license_key_obj:
        return Response(
            {"error": "License key not found"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    license_key = license_key_obj.key

    try:
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
        instance_type = instance_type_map.get(
            serializer.validated_data["instance_type"]
        )
        if not instance_type:
            return Response(
                {"error": "Invalid instance_type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        command = ActivateLicenseCommand(
            license_key=license_key,
            product_slug=serializer.validated_data["product_slug"],
            instance_identifier=serializer.validated_data[
                "instance_identifier"
            ],
            instance_type=instance_type,
            instance_metadata=serializer.validated_data.get(
                "instance_metadata", {}
            ),
        )

        result = await handler.handle(command)

        response_serializer = ActivateLicenseResponseSerializer(result)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED
        )

    except DomainException as e:
        return Response(
            {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
async def get_license_status(request: Request) -> Response:
    """
    Get license status and entitlements - US4.

    GET /api/v1/product/status?license_key={key}
    """
    license_key = (
        request.query_params.get("license_key")
        or request.headers.get("X-License-Key")
    )

    if not license_key:
        return Response(
            {"error": "license_key parameter or X-License-Key header required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        handler = GetLicenseStatusHandler(
            license_key_repository=_license_key_repo,
            license_repository=_license_repo,
            product_repository=_product_repo,
            activation_repository=_activation_repo,
        )

        query = GetLicenseStatusQuery(license_key=license_key)

        result = await handler.handle(query)

        serializer = LicenseStatusResponseSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except DomainException as e:
        return Response(
            {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
async def deactivate_seat(
    request: Request, activation_id: uuid.UUID
) -> Response:
    """
    Deactivate a seat - US5.

    DELETE /api/v1/product/activations/{activation_id}
    """
    # Get license key from request (set by middleware)
    license_key_obj = getattr(request, "license_key", None)
    if not license_key_obj:
        return Response(
            {"error": "License key not found"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    license_key = license_key_obj.key

    # Get instance_identifier from request body or query param
    instance_identifier = (
        request.data.get("instance_identifier")
        or request.query_params.get("instance_identifier")
    )

    if not instance_identifier:
        return Response(
            {"error": "instance_identifier is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        handler = DeactivateSeatHandler(
            license_key_repository=_license_key_repo,
            activation_repository=_activation_repo,
        )

        command = DeactivateSeatCommand(
            license_key=license_key,
            instance_identifier=instance_identifier,
        )

        await handler.handle(command)

        return Response(
            {"message": "Seat deactivated successfully"},
            status=status.HTTP_200_OK,
        )

    except DomainException as e:
        return Response(
            {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

