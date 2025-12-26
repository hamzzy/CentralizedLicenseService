"""
Activation domain services.

Domain services contain business logic that doesn't naturally
fit within a single entity.
"""
import uuid
from typing import Optional

from activations.domain.activation import Activation
from activations.ports.activation_repository import ActivationRepository
from licenses.domain.license import License
from licenses.ports.license_repository import LicenseRepository


class SeatManager:
    """Domain service for managing license seats."""

    @staticmethod
    async def count_active_seats(
        license_id: uuid.UUID,
        repository: ActivationRepository,
    ) -> int:
        """
        Count active activations for a license.

        Args:
            license_id: License UUID
            repository: Activation repository

        Returns:
            Number of active activations
        """
        activations = await repository.find_active_by_license(license_id)
        return len(activations)

    @staticmethod
    async def has_available_seats(
        license: License,
        repository: ActivationRepository,
    ) -> bool:
        """
        Check if license has available seats.

        Args:
            license: License entity
            repository: Activation repository

        Returns:
            True if seats are available, False otherwise
        """
        active_count = await SeatManager.count_active_seats(
            license.id, repository
        )
        return active_count < license.seat_limit

    @staticmethod
    async def can_activate(
        license: License,
        instance_identifier: str,
        repository: ActivationRepository,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a license can be activated for an instance.

        Args:
            license: License entity
            instance_identifier: Instance identifier
            repository: Activation repository

        Returns:
            Tuple of (can_activate, error_message)
        """
        # Check if license is valid
        if not license.is_valid():
            if license.status.value == "expired":
                return False, "License has expired"
            if license.status.value == "suspended":
                return False, "License is suspended"
            if license.status.value == "cancelled":
                return False, "License is cancelled"
            return False, "License is not valid"

        # Check if instance is already activated
        existing = await repository.find_by_license_and_instance(
            license.id, instance_identifier
        )
        if existing and existing.is_active:
            return False, "Instance already activated"

        # Check seat availability
        has_seats = await SeatManager.has_available_seats(
            license, repository
        )
        if not has_seats:
            return False, "License seat limit exceeded"

        return True, None

    @staticmethod
    async def activate_license(
        license: License,
        instance_identifier: str,
        instance_type: "InstanceType",  # noqa: F821
        instance_metadata: Optional[dict] = None,
        activation_repository: ActivationRepository = None,
        license_repository: LicenseRepository = None,
    ) -> Activation:
        """
        Activate a license for an instance.

        Args:
            license: License entity
            instance_identifier: Instance identifier
            instance_type: Instance type
            instance_metadata: Optional metadata
            activation_repository: Activation repository
            license_repository: License repository (unused, for future)

        Returns:
            Created Activation entity
        """
        from core.domain.value_objects import InstanceType

        # Check if activation is allowed
        can_activate, error = await SeatManager.can_activate(
            license, instance_identifier, activation_repository
        )
        if not can_activate:
            raise ValueError(error)

        # Create activation
        activation = Activation.create(
            license_id=license.id,
            instance_identifier=instance_identifier,
            instance_type=instance_type,
            instance_metadata=instance_metadata,
        )

        # Save activation
        return await activation_repository.save(activation)

    @staticmethod
    async def deactivate_seat(
        activation: Activation,
        repository: ActivationRepository,
    ) -> Activation:
        """
        Deactivate a seat (free a license seat).

        Args:
            activation: Activation entity to deactivate
            repository: Activation repository

        Returns:
            Deactivated Activation entity
        """
        deactivated = activation.deactivate()
        return await repository.save(deactivated)

