"""
ActivateLicenseHandler - US3.

Handler for activating a license.
"""

import hashlib

from activations.application.commands.activate_license import ActivateLicenseCommand
from activations.application.dto.activation_dto import ActivateLicenseResponseDTO
from activations.domain.events import LicenseActivated
from activations.domain.services import SeatManager
from activations.ports.activation_repository import ActivationRepository
from brands.ports.product_repository import ProductRepository
from core.domain.exceptions import InvalidLicenseKeyError, LicenseNotFoundError
from core.infrastructure.events import event_bus
from licenses.application.services.license_cache_service import LicenseCacheService
from licenses.ports.license_key_repository import LicenseKeyRepository
from licenses.ports.license_repository import LicenseRepository


class ActivateLicenseHandler:
    """Handler for ActivateLicenseCommand."""

    def __init__(
        self,
        license_key_repository: LicenseKeyRepository,
        license_repository: LicenseRepository,
        product_repository: ProductRepository,
        activation_repository: ActivationRepository,
    ):
        """Initialize handler with repositories."""
        self.license_key_repository = license_key_repository
        self.license_repository = license_repository
        self.product_repository = product_repository
        self.activation_repository = activation_repository

    async def handle(self, command: ActivateLicenseCommand) -> ActivateLicenseResponseDTO:
        """
        Handle activate license command.

        Args:
            command: ActivateLicenseCommand

        Returns:
            ActivateLicenseResponseDTO with activation details

        Raises:
            InvalidLicenseKeyError: If license key not found
            LicenseNotFoundError: If license not found
            ValueError: If activation not allowed
        """
        # Find license key
        key_hash = hashlib.sha256(command.license_key.encode()).hexdigest()
        license_key = await self.license_key_repository.find_by_key_hash(key_hash)

        if not license_key:
            raise InvalidLicenseKeyError("Invalid license key")

        # Find product by slug
        product = await self.product_repository.find_by_slug(
            license_key.brand_id, command.product_slug
        )
        if not product:
            raise ValueError(f"Product {command.product_slug} not found")

        # Find license by license key and product
        license = await self.license_repository.find_by_license_key_and_product(
            license_key.id, product.id
        )

        if not license:
            raise LicenseNotFoundError(f"License not found for product {command.product_slug}")

        # Activate license using SeatManager
        activation = await SeatManager.activate_license(
            license=license,
            instance_identifier=command.instance_identifier,
            instance_type=command.instance_type,
            instance_metadata=command.instance_metadata,
            activation_repository=self.activation_repository,
        )

        # Publish event
        await event_bus.publish(
            LicenseActivated(
                activation_id=activation.id,
                license_id=license.id,
                instance_identifier=command.instance_identifier,
                instance_type=command.instance_type.value,
            )
        )

        # Invalidate license status cache
        await LicenseCacheService.invalidate_license_status(command.license_key)

        # Calculate remaining seats
        active_count = await SeatManager.count_active_seats(license.id, self.activation_repository)
        seats_remaining = max(0, license.seat_limit - active_count)

        return ActivateLicenseResponseDTO(
            activation_id=activation.id,
            license_id=license.id,
            seats_remaining=seats_remaining,
            message="License activated successfully",
        )
