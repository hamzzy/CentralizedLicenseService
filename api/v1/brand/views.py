"""
Brand API views - US1, US2, US6.

These endpoints are used by brand systems to:
- Provision licenses
- Manage license lifecycle
- Query licenses by customer email
"""
import uuid
from typing import Any

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from activations.infrastructure.repositories.django_activation_repository import (
    DjangoActivationRepository,
)
from api.exceptions import APIError
from brands.infrastructure.repositories.django_brand_repository import (
    DjangoBrandRepository,
)
from brands.infrastructure.repositories.django_product_repository import (
    DjangoProductRepository,
)
from core.domain.exceptions import DomainException
from licenses.application.commands.cancel_license import CancelLicenseCommand
from licenses.application.commands.provision_license import (
    ProvisionLicenseCommand,
)
from licenses.application.commands.renew_license import RenewLicenseCommand
from licenses.application.commands.resume_license import ResumeLicenseCommand
from licenses.application.commands.suspend_license import SuspendLicenseCommand
from licenses.application.handlers.get_license_status_handler import (
    GetLicenseStatusHandler,
)
from licenses.application.handlers.license_lifecycle_handlers import (
    CancelLicenseHandler,
    RenewLicenseHandler,
    ResumeLicenseHandler,
    SuspendLicenseHandler,
)
from licenses.application.handlers.list_licenses_by_email_handler import (
    ListLicensesByEmailHandler,
)
from licenses.application.handlers.provision_license_handler import (
    ProvisionLicenseHandler,
)
from licenses.application.queries.list_licenses_by_email import (
    ListLicensesByEmailQuery,
)
from licenses.infrastructure.repositories.django_license_key_repository import (
    DjangoLicenseKeyRepository,
)
from licenses.infrastructure.repositories.django_license_repository import (
    DjangoLicenseRepository,
)
from api.v1.brand.serializers import (
    CancelLicenseRequestSerializer,
    LicenseListItemSerializer,
    ProvisionLicenseRequestSerializer,
    ProvisionLicenseResponseSerializer,
    RenewLicenseRequestSerializer,
    ResumeLicenseRequestSerializer,
    SuspendLicenseRequestSerializer,
)


# Initialize repositories (in production, use DI container)
_brand_repo = DjangoBrandRepository()
_product_repo = DjangoProductRepository()
_license_key_repo = DjangoLicenseKeyRepository()
_license_repo = DjangoLicenseRepository()
_activation_repo = DjangoActivationRepository()


@extend_schema(
    operation_id="provision_license",
    summary="Provision License",
    description=(
        "Create a new license key and associated licenses for a customer. "
        "This endpoint requires brand API key authentication."
    ),
    tags=["Brand API"],
    request=ProvisionLicenseRequestSerializer,
    responses={
        201: ProvisionLicenseResponseSerializer,
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
    },
)
@api_view(["POST"])
async def provision_license(request: Request) -> Response:
    """
    Provision a license key and licenses - US1.

    POST /api/v1/brand/licenses/provision
    """
    serializer = ProvisionLicenseRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    # Get brand from request (set by middleware)
    brand = getattr(request, "brand", None)
    if not brand:
        return Response(
            {"error": "Brand not found"}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        handler = ProvisionLicenseHandler(
            brand_repository=_brand_repo,
            product_repository=_product_repo,
            license_key_repository=_license_key_repo,
            license_repository=_license_repo,
        )

        command = ProvisionLicenseCommand(
            brand_id=brand.id,
            customer_email=serializer.validated_data["customer_email"],
            products=serializer.validated_data["products"],
            expiration_date=serializer.validated_data.get("expiration_date"),
            max_seats=serializer.validated_data.get("max_seats", 1),
        )

        result = await handler.handle(command)

        response_serializer = ProvisionLicenseResponseSerializer(result)
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


@extend_schema(
    operation_id="renew_license",
    summary="Renew License",
    description="Extend a license's expiration date.",
    tags=["Brand API"],
    request=RenewLicenseRequestSerializer,
    responses={
        200: {"description": "License renewed successfully"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "License not found"},
    },
)
@api_view(["PATCH"])
async def renew_license(request: Request, license_id: uuid.UUID) -> Response:
    """
    Renew a license - US2.

    PATCH /api/v1/brand/licenses/{license_id}/renew
    """
    serializer = RenewLicenseRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        handler = RenewLicenseHandler(
            license_repository=_license_repo,
            license_key_repository=_license_key_repo,
        )

        command = RenewLicenseCommand(
            license_id=license_id,
            expiration_date=serializer.validated_data["expiration_date"],
        )

        await handler.handle(command)

        return Response(
            {"message": "License renewed successfully"},
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


@extend_schema(
    operation_id="suspend_license",
    summary="Suspend License",
    description="Temporarily disable a license. Suspended licenses cannot be activated.",
    tags=["Brand API"],
    request=SuspendLicenseRequestSerializer,
    responses={
        200: {"description": "License suspended successfully"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "License not found"},
    },
)
@api_view(["PATCH"])
async def suspend_license(request: Request, license_id: uuid.UUID) -> Response:
    """
    Suspend a license - US2.

    PATCH /api/v1/brand/licenses/{license_id}/suspend
    """
    serializer = SuspendLicenseRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        handler = SuspendLicenseHandler(
            license_repository=_license_repo,
            license_key_repository=_license_key_repo,
        )

        command = SuspendLicenseCommand(
            license_id=license_id,
            reason=serializer.validated_data.get("reason"),
        )

        await handler.handle(command)

        return Response(
            {"message": "License suspended successfully"},
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


@extend_schema(
    operation_id="resume_license",
    summary="Resume License",
    description="Re-enable a suspended license.",
    tags=["Brand API"],
    request=ResumeLicenseRequestSerializer,
    responses={
        200: {"description": "License resumed successfully"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "License not found"},
    },
)
@api_view(["PATCH"])
async def resume_license(request: Request, license_id: uuid.UUID) -> Response:
    """
    Resume a license - US2.

    PATCH /api/v1/brand/licenses/{license_id}/resume
    """
    serializer = ResumeLicenseRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        handler = ResumeLicenseHandler(
            license_repository=_license_repo,
            license_key_repository=_license_key_repo,
        )

        command = ResumeLicenseCommand(license_id=license_id)

        await handler.handle(command)

        return Response(
            {"message": "License resumed successfully"},
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


@extend_schema(
    operation_id="cancel_license",
    summary="Cancel License",
    description="Permanently cancel a license. Cancelled licenses cannot be reactivated.",
    tags=["Brand API"],
    request=CancelLicenseRequestSerializer,
    responses={
        200: {"description": "License cancelled successfully"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "License not found"},
    },
)
@api_view(["PATCH"])
async def cancel_license(request: Request, license_id: uuid.UUID) -> Response:
    """
    Cancel a license - US2.

    PATCH /api/v1/brand/licenses/{license_id}/cancel
    """
    serializer = CancelLicenseRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        handler = CancelLicenseHandler(
            license_repository=_license_repo,
            license_key_repository=_license_key_repo,
        )

        command = CancelLicenseCommand(
            license_id=license_id,
            reason=serializer.validated_data.get("reason"),
        )

        await handler.handle(command)

        return Response(
            {"message": "License cancelled successfully"},
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


@extend_schema(
    operation_id="list_licenses_by_email",
    summary="List Licenses by Email",
    description="Query all licenses for a customer by email address.",
    tags=["Brand API"],
    parameters=[
        OpenApiParameter(
            name="email",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Customer email address",
        ),
    ],
    responses={
        200: LicenseListItemSerializer(many=True),
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
    },
)
@api_view(["GET"])
async def list_licenses_by_email(request: Request) -> Response:
    """
    List licenses by customer email - US6.

    GET /api/v1/brand/licenses?email={email}
    """
    # Get brand from request (set by middleware)
    brand = getattr(request, "brand", None)
    if not brand:
        return Response(
            {"error": "Brand not found"}, status=status.HTTP_401_UNAUTHORIZED
        )

    email = request.query_params.get("email")
    if not email:
        return Response(
            {"error": "email query parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        handler = ListLicensesByEmailHandler(
            license_key_repository=_license_key_repo,
            license_repository=_license_repo,
            brand_repository=_brand_repo,
            product_repository=_product_repo,
            activation_repository=_activation_repo,
        )

        query = ListLicensesByEmailQuery(
            customer_email=email, brand_id=brand.id
        )

        result = await handler.handle(query)

        serializer = LicenseListItemSerializer(result, many=True)
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

