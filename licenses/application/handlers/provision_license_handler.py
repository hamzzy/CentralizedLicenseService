"""
ProvisionLicenseHandler - US1.

Handles the provision license command.
"""

import hashlib
import uuid

from brands.ports.brand_repository import BrandRepository
from brands.ports.product_repository import ProductRepository
from core.domain.exceptions import BrandNotFoundError, DomainException
from core.infrastructure.events import event_bus
from licenses.application.commands.provision_license import ProvisionLicenseCommand
from licenses.application.dto.license_dto import (
    LicenseDTO,
    LicenseKeyDTO,
    ProvisionLicenseResponseDTO,
)
from licenses.domain.events import LicenseKeyCreated, LicenseProvisioned
from licenses.domain.license import License
from licenses.domain.license_key import LicenseKey
from licenses.ports.license_key_repository import LicenseKeyRepository
from licenses.ports.license_repository import LicenseRepository


class ProvisionLicenseHandler:
    """Handler for ProvisionLicenseCommand."""

    def __init__(
        self,
        brand_repository: BrandRepository,
        product_repository: ProductRepository,
        license_key_repository: LicenseKeyRepository,
        license_repository: LicenseRepository,
    ):
        """Initialize handler with repositories."""
        self.brand_repository = brand_repository
        self.product_repository = product_repository
        self.license_key_repository = license_key_repository
        self.license_repository = license_repository

    async def handle(self, command: ProvisionLicenseCommand) -> ProvisionLicenseResponseDTO:
        """
        Handle provision license command.

        Args:
            command: ProvisionLicenseCommand

        Returns:
            ProvisionLicenseResponseDTO with license key and licenses

        Raises:
            BrandNotFoundError: If brand not found
            DomainException: If product not found or other domain error
        """
        # Get brand
        brand = await self.brand_repository.find_by_id(command.brand_id)
        if not brand:
            raise BrandNotFoundError(f"Brand {command.brand_id} not found")

        # Create license key
        license_key = LicenseKey.create(
            brand_id=brand.id,
            brand_prefix=brand.prefix,
            customer_email=command.customer_email,
        )

        # Save license key
        saved_key = await self.license_key_repository.save(license_key)

        # Publish event
        await event_bus.publish(
            LicenseKeyCreated(
                license_key_id=saved_key.id,
                brand_id=brand.id,
                customer_email=command.customer_email,
            )
        )

        # Create licenses for each product
        licenses = []
        for product_id in command.products:
            # Get product
            product = await self.product_repository.find_by_id(product_id)
            if not product:
                raise DomainException(f"Product {product_id} not found")
            if product.brand_id != brand.id:
                raise DomainException(f"Product {product_id} does not belong to brand")

            # Create license
            license = License.create(
                license_key_id=saved_key.id,
                product_id=product.id,
                seat_limit=command.max_seats,
                expires_at=command.expiration_date,
            )

            # Save license
            saved_license = await self.license_repository.save(license)

            # Publish event
            await event_bus.publish(
                LicenseProvisioned(
                    license_id=saved_license.id,
                    license_key_id=saved_key.id,
                    product_id=product.id,
                )
            )

            licenses.append(saved_license)

        # Build response DTO
        license_dtos = [
            LicenseDTO(
                id=license.id,
                product_id=license.product_id,
                product_name="",  # Will be populated from product
                status=license.status.value,
                seat_limit=license.seat_limit,
                seats_used=0,  # New license, no activations yet
                seats_remaining=license.seat_limit,
                expires_at=license.expires_at,
                created_at=license.created_at,
            )
            for license in licenses
        ]

        return ProvisionLicenseResponseDTO(
            license_key=LicenseKeyDTO(
                id=saved_key.id,
                key=saved_key.key,
                brand_id=saved_key.brand_id,
                customer_email=str(saved_key.customer_email),
                created_at=saved_key.created_at,
            ),
            licenses=license_dtos,
        )
