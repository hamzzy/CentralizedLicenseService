"""
Brand API views - US1, US2, US6.

These endpoints are used by brand systems to:
- Provision licenses
- Manage license lifecycle
- Query licenses by customer email
"""

import uuid

from asgiref.sync import async_to_sync
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from activations.infrastructure.repositories.django_activation_repository import (
    DjangoActivationRepository,
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
from brands.infrastructure.repositories.django_brand_repository import DjangoBrandRepository
from brands.infrastructure.repositories.django_product_repository import DjangoProductRepository
from core.domain.exceptions import DomainException
from core.instrumentation import Status, StatusCode, get_tracer
from licenses.application.commands.cancel_license import CancelLicenseCommand
from licenses.application.commands.provision_license import ProvisionLicenseCommand
from licenses.application.commands.renew_license import RenewLicenseCommand
from licenses.application.commands.resume_license import ResumeLicenseCommand
from licenses.application.commands.suspend_license import SuspendLicenseCommand
from licenses.application.handlers.license_lifecycle_handlers import (
    CancelLicenseHandler,
    RenewLicenseHandler,
    ResumeLicenseHandler,
    SuspendLicenseHandler,
)
from licenses.application.handlers.list_licenses_by_email_handler import ListLicensesByEmailHandler
from licenses.application.handlers.provision_license_handler import ProvisionLicenseHandler
from licenses.application.queries.list_licenses_by_email import ListLicensesByEmailQuery
from licenses.infrastructure.repositories.django_license_key_repository import (
    DjangoLicenseKeyRepository,
)
from licenses.infrastructure.repositories.django_license_repository import DjangoLicenseRepository

# Initialize repositories (in production, use DI container)
_brand_repo = DjangoBrandRepository()
_product_repo = DjangoProductRepository()
_license_key_repo = DjangoLicenseKeyRepository()
_license_repo = DjangoLicenseRepository()
_activation_repo = DjangoActivationRepository()

tracer = get_tracer(__name__)


class ProvisionLicenseView(APIView):
    """View for provisioning licenses - US1."""

    @extend_schema(
        operation_id="provision_license",
        summary="Provision License",
        description=(
            "Create a new license key and associated licenses for a customer. "
            "This endpoint requires brand API key authentication via X-API-Key header."
        ),
        tags=["Brand API"],
        request=ProvisionLicenseRequestSerializer,
        responses={
            201: ProvisionLicenseResponseSerializer,
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized - Missing or invalid API key"},
            404: {"description": "Not Found"},
        },
    )
    def post(self, request: Request) -> Response:
        """Provision a license key and licenses - US1."""
        return async_to_sync(self._handle_provision_license)(request)

    async def _handle_provision_license(self, request: Request) -> Response:
        """Async handler for provision license."""
        with tracer.start_as_current_span("provision_license") as span:
            span.set_attribute("operation", "provision_license")

            serializer = ProvisionLicenseRequestSerializer(data=request.data)
            if not serializer.is_valid():
                span.set_attribute("error", "validation_failed")
                span.set_attribute("error.details", str(serializer.errors))
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                print(f"DEBUG: Validation failed: {serializer.errors}")
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            # Get brand from request (set by middleware)
            brand = getattr(request, "brand", None)
            if not brand:
                span.set_attribute("error", "brand_not_found")
                span.set_status(Status(StatusCode.ERROR, "Brand not found"))
                return Response({"error": "Brand not found"}, status=status.HTTP_401_UNAUTHORIZED)

            span.set_attribute("brand.id", str(brand.id))
            span.set_attribute("brand.name", brand.name)
            span.set_attribute("customer_email", serializer.validated_data["customer_email"])

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

            span.set_attribute("products.count", len(serializer.validated_data["products"]))
            span.set_attribute("max_seats", serializer.validated_data.get("max_seats", 1))

            result = await handler.handle(command)

            response_serializer = ProvisionLicenseResponseSerializer(result)
            span.set_attribute("license_key.id", str(result.license_key.id))
            span.set_attribute("licenses.count", len(result.licenses))
            span.set_status(Status(StatusCode.OK))

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class RenewLicenseView(APIView):
    """View for renewing licenses - US2."""

    @extend_schema(
        operation_id="renew_license",
        summary="Renew License",
        description="Extend a license's expiration date.",
        tags=["Brand API"],
        request=RenewLicenseRequestSerializer,
        responses={
            200: {"description": "License renewed successfully"},
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized - Missing or invalid API key"},
            404: {"description": "License not found"},
        },
    )
    def patch(self, request: Request, license_id: uuid.UUID) -> Response:
        """Renew a license - US2."""
        return async_to_sync(self._handle_renew_license)(request, license_id)

    async def _handle_renew_license(self, request: Request, license_id: uuid.UUID) -> Response:
        """Async handler for renew license."""
        with tracer.start_as_current_span("renew_license") as span:
            span.set_attribute("operation", "renew_license")
            span.set_attribute("license.id", str(license_id))

            serializer = RenewLicenseRequestSerializer(data=request.data)
            if not serializer.is_valid():
                span.set_attribute("error", "validation_failed")
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            brand = getattr(request, "brand", None)
            if brand:
                span.set_attribute("brand.id", str(brand.id))

            handler = RenewLicenseHandler(
                license_repository=_license_repo,
                license_key_repository=_license_key_repo,
            )

            command = RenewLicenseCommand(
                license_id=license_id,
                expiration_date=serializer.validated_data["expiration_date"],
            )

            span.set_attribute("expiration_date", str(serializer.validated_data["expiration_date"]))

            await handler.handle(command)

            span.set_status(Status(StatusCode.OK))
            return Response(
                {"message": "License renewed successfully"},
                status=status.HTTP_200_OK,
            )


class SuspendLicenseView(APIView):
    """View for suspending licenses - US2."""

    @extend_schema(
        operation_id="suspend_license",
        summary="Suspend License",
        description="Temporarily disable a license. Suspended licenses cannot be activated.",
        tags=["Brand API"],
        request=SuspendLicenseRequestSerializer,
        responses={
            200: {"description": "License suspended successfully"},
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized - Missing or invalid API key"},
            404: {"description": "License not found"},
        },
    )
    def patch(self, request: Request, license_id: uuid.UUID) -> Response:
        """Suspend a license - US2."""
        return async_to_sync(self._handle_suspend_license)(request, license_id)

    async def _handle_suspend_license(self, request: Request, license_id: uuid.UUID) -> Response:
        """Async handler for suspend license."""
        with tracer.start_as_current_span("suspend_license") as span:
            span.set_attribute("operation", "suspend_license")
            span.set_attribute("license.id", str(license_id))

            serializer = SuspendLicenseRequestSerializer(data=request.data)
            if not serializer.is_valid():
                span.set_attribute("error", "validation_failed")
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            brand = getattr(request, "brand", None)
            if brand:
                span.set_attribute("brand.id", str(brand.id))

            handler = SuspendLicenseHandler(
                license_repository=_license_repo,
                license_key_repository=_license_key_repo,
            )

            command = SuspendLicenseCommand(
                license_id=license_id,
                reason=serializer.validated_data.get("reason"),
            )

            if serializer.validated_data.get("reason"):
                span.set_attribute("reason", serializer.validated_data.get("reason"))

            await handler.handle(command)

            span.set_status(Status(StatusCode.OK))
            return Response(
                {"message": "License suspended successfully"},
                status=status.HTTP_200_OK,
            )


class ResumeLicenseView(APIView):
    """View for resuming licenses - US2."""

    @extend_schema(
        operation_id="resume_license",
        summary="Resume License",
        description="Re-enable a suspended license.",
        tags=["Brand API"],
        request=ResumeLicenseRequestSerializer,
        responses={
            200: {"description": "License resumed successfully"},
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized - Missing or invalid API key"},
            404: {"description": "License not found"},
        },
    )
    def patch(self, request: Request, license_id: uuid.UUID) -> Response:
        """Resume a license - US2."""
        return async_to_sync(self._handle_resume_license)(request, license_id)

    async def _handle_resume_license(self, request: Request, license_id: uuid.UUID) -> Response:
        """Async handler for resume license."""
        with tracer.start_as_current_span("resume_license") as span:
            span.set_attribute("operation", "resume_license")
            span.set_attribute("license.id", str(license_id))

            serializer = ResumeLicenseRequestSerializer(data=request.data)
            if not serializer.is_valid():
                span.set_attribute("error", "validation_failed")
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            brand = getattr(request, "brand", None)
            if brand:
                span.set_attribute("brand.id", str(brand.id))

            handler = ResumeLicenseHandler(
                license_repository=_license_repo,
                license_key_repository=_license_key_repo,
            )

            command = ResumeLicenseCommand(license_id=license_id)

            await handler.handle(command)

            span.set_status(Status(StatusCode.OK))
            return Response(
                {"message": "License resumed successfully"},
                status=status.HTTP_200_OK,
            )


class CancelLicenseView(APIView):
    """View for cancelling licenses - US2."""

    @extend_schema(
        operation_id="cancel_license",
        summary="Cancel License",
        description="Permanently cancel a license. Cancelled licenses cannot be reactivated.",
        tags=["Brand API"],
        request=CancelLicenseRequestSerializer,
        responses={
            200: {"description": "License cancelled successfully"},
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized - Missing or invalid API key"},
            404: {"description": "License not found"},
        },
    )
    def patch(self, request: Request, license_id: uuid.UUID) -> Response:
        """Cancel a license - US2."""
        return async_to_sync(self._handle_cancel_license)(request, license_id)

    async def _handle_cancel_license(self, request: Request, license_id: uuid.UUID) -> Response:
        """Async handler for cancel license."""
        with tracer.start_as_current_span("cancel_license") as span:
            span.set_attribute("operation", "cancel_license")
            span.set_attribute("license.id", str(license_id))

            serializer = CancelLicenseRequestSerializer(data=request.data)
            if not serializer.is_valid():
                span.set_attribute("error", "validation_failed")
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            brand = getattr(request, "brand", None)
            if brand:
                span.set_attribute("brand.id", str(brand.id))

            handler = CancelLicenseHandler(
                license_repository=_license_repo,
                license_key_repository=_license_key_repo,
            )

            command = CancelLicenseCommand(
                license_id=license_id,
                reason=serializer.validated_data.get("reason"),
            )

            if serializer.validated_data.get("reason"):
                span.set_attribute("reason", serializer.validated_data.get("reason"))

            await handler.handle(command)

            span.set_status(Status(StatusCode.OK))
            return Response(
                {"message": "License cancelled successfully"},
                status=status.HTTP_200_OK,
            )


class ListLicensesByEmailView(APIView):
    """View for listing licenses by customer email - US6."""

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
            401: {"description": "Unauthorized - Missing or invalid API key"},
        },
    )
    def get(self, request: Request) -> Response:
        """List licenses by customer email - US6."""
        return async_to_sync(self._handle_list_licenses_by_email)(request)

    async def _handle_list_licenses_by_email(self, request: Request) -> Response:
        """Async handler for list licenses by email."""
        with tracer.start_as_current_span("list_licenses_by_email") as span:
            span.set_attribute("operation", "list_licenses_by_email")

            # Get brand from request (set by middleware)
            brand = getattr(request, "brand", None)
            if not brand:
                span.set_attribute("error", "brand_not_found")
                span.set_status(Status(StatusCode.ERROR, "Brand not found"))
                return Response({"error": "Brand not found"}, status=status.HTTP_401_UNAUTHORIZED)

            span.set_attribute("brand.id", str(brand.id))

            email = request.query_params.get("email")
            if not email:
                span.set_attribute("error", "email_required")
                span.set_status(Status(StatusCode.ERROR, "Email required"))
                return Response(
                    {"error": "email query parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            span.set_attribute("customer_email", email)

            handler = ListLicensesByEmailHandler(
                license_key_repository=_license_key_repo,
                license_repository=_license_repo,
                brand_repository=_brand_repo,
                product_repository=_product_repo,
                activation_repository=_activation_repo,
            )

            query = ListLicensesByEmailQuery(customer_email=email, brand_id=brand.id)

            result = await handler.handle(query)

            serializer = LicenseListItemSerializer(result, many=True)
            span.set_attribute("licenses.count", len(result))
            span.set_status(Status(StatusCode.OK))

            return Response(serializer.data, status=status.HTTP_200_OK)
