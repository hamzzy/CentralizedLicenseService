"""
DeactivateSeatHandler - US5.

Handler for deactivating a seat.
"""

import hashlib

from activations.application.commands.deactivate_seat import DeactivateSeatCommand
from activations.domain.events import SeatDeactivated
from activations.domain.services import SeatManager
from activations.ports.activation_repository import ActivationRepository
from core.domain.exceptions import ActivationNotFoundError, InvalidLicenseKeyError
from core.infrastructure.events import event_bus
from licenses.ports.license_key_repository import LicenseKeyRepository


class DeactivateSeatHandler:
    """Handler for DeactivateSeatCommand."""

    def __init__(
        self,
        license_key_repository: LicenseKeyRepository,
        activation_repository: ActivationRepository,
    ):
        """Initialize handler with repositories."""
        self.license_key_repository = license_key_repository
        self.activation_repository = activation_repository

    async def handle(self, command: DeactivateSeatCommand):
        """
        Handle deactivate seat command.

        Args:
            command: DeactivateSeatCommand

        Returns:
            Deactivated Activation entity

        Raises:
            InvalidLicenseKeyError: If license key not found
            ActivationNotFoundError: If activation not found
        """
        # Find license key
        key_hash = hashlib.sha256(command.license_key.encode()).hexdigest()
        license_key = await self.license_key_repository.find_by_key_hash(key_hash)

        if not license_key:
            raise InvalidLicenseKeyError("Invalid license key")

        # Find license by license key (we need to get the license)
        # Note: This handler should receive LicenseRepository via DI
        # For now, we'll find activation directly by instance identifier
        # across all licenses for this key
        from licenses.infrastructure.repositories.django_license_repository import (
            DjangoLicenseRepository,
        )
        from licenses.ports.license_repository import LicenseRepository

        license_repo: LicenseRepository = DjangoLicenseRepository()
        licenses = await license_repo.find_by_license_key(license_key.id)

        # Find activation by license and instance
        activation = None
        for license in licenses:
            activation = await self.activation_repository.find_by_license_and_instance(
                license.id, command.instance_identifier
            )
            if activation:
                break

        if not activation:
            raise ActivationNotFoundError(
                f"Activation not found for instance {command.instance_identifier}"
            )

        # Deactivate using SeatManager
        deactivated = await SeatManager.deactivate_seat(activation, self.activation_repository)

        # Publish event
        await event_bus.publish(
            SeatDeactivated(
                activation_id=deactivated.id,
                license_id=activation.license_id,
                instance_identifier=command.instance_identifier,
            )
        )

        return deactivated
