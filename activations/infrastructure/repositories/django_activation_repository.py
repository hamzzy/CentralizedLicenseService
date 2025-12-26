"""
Django implementation of ActivationRepository port.

This adapter converts between domain entities and Django ORM models.
"""

import uuid
from typing import List, Optional

from asgiref.sync import sync_to_async

from activations.domain.activation import Activation
from activations.infrastructure.models import Activation as ActivationModel
from activations.ports.activation_repository import ActivationRepository
from core.domain.value_objects import InstanceIdentifier, InstanceType


class DjangoActivationRepository(ActivationRepository):
    """
    Django ORM implementation of ActivationRepository.

    This adapter:
    1. Converts Django models to domain entities
    2. Converts domain entities to Django models
    3. Implements repository interface
    """

    def _to_domain(self, model: ActivationModel) -> Activation:
        """
        Convert Django model to domain entity.

        Args:
            model: Django Activation model

        Returns:
            Activation domain entity
        """
        # Determine instance type from metadata or infer from identifier
        instance_type = InstanceType.URL  # Default
        if model.instance_metadata:
            type_str = model.instance_metadata.get("instance_type")
            if type_str:
                try:
                    instance_type = InstanceType(type_str)
                except ValueError:
                    pass

        return Activation(
            id=model.id,
            license_id=model.license_id,
            instance_identifier=InstanceIdentifier(model.instance_identifier, instance_type),
            instance_metadata=model.instance_metadata or {},
            activated_at=model.activated_at,
            last_checked_at=model.last_checked_at,
            deactivated_at=model.deactivated_at,
            is_active=model.is_active,
        )

    def _to_model(self, activation: Activation) -> ActivationModel:
        """
        Convert domain entity to Django model.

        Args:
            activation: Activation domain entity

        Returns:
            Django Activation model
        """
        # Store instance type in metadata
        metadata = activation.instance_metadata.copy()
        metadata["instance_type"] = activation.instance_identifier.instance_type.value

        # pylint: disable=no-member
        model, created = ActivationModel.objects.get_or_create(
            id=activation.id,
            defaults={
                "license_id": activation.license_id,
                "instance_identifier": str(activation.instance_identifier),
                "instance_metadata": metadata,
                "activated_at": activation.activated_at,
                "last_checked_at": activation.last_checked_at,
                "deactivated_at": activation.deactivated_at,
                "is_active": activation.is_active,
            },
        )
        # Update if exists
        if not created:
            model.instance_identifier = str(activation.instance_identifier)
            model.instance_metadata = metadata
            model.last_checked_at = activation.last_checked_at
            model.deactivated_at = activation.deactivated_at
            model.is_active = activation.is_active
        return model

    async def save(self, activation: Activation) -> Activation:
        """
        Save an activation entity.

        Args:
            activation: Activation entity to save

        Returns:
            Saved activation entity
        """
        model = await sync_to_async(self._to_model)(activation)
        await sync_to_async(model.save)()
        return self._to_domain(model)

    async def find_by_id(self, activation_id: uuid.UUID) -> Optional[Activation]:
        """
        Find an activation by ID.

        Args:
            activation_id: Activation UUID

        Returns:
            Activation entity or None if not found
        """
        try:
            # pylint: disable=no-member
            model = await sync_to_async(ActivationModel.objects.get)(id=activation_id)
            return self._to_domain(model)
        except ActivationModel.DoesNotExist:  # pylint: disable=no-member
            return None

    async def find_by_license_and_instance(
        self, license_id: uuid.UUID, instance_identifier: str
    ) -> Optional[Activation]:
        """
        Find an activation by license and instance identifier.

        Args:
            license_id: License UUID
            instance_identifier: Instance identifier

        Returns:
            Activation entity or None if not found
        """
        try:
            # pylint: disable=no-member
            model = await sync_to_async(ActivationModel.objects.get)(
                license_id=license_id,
                instance_identifier=instance_identifier,
            )
            return self._to_domain(model)
        except ActivationModel.DoesNotExist:  # pylint: disable=no-member
            return None

    async def find_active_by_license(self, license_id: uuid.UUID) -> List[Activation]:
        """
        Find all active activations for a license.

        Args:
            license_id: License UUID

        Returns:
            List of active Activation entities
        """
        models = await sync_to_async(
            lambda: list(
                ActivationModel.objects.filter(  # pylint: disable=no-member
                    license_id=license_id, is_active=True
                )
            )
        )()
        return [self._to_domain(model) for model in models]

    async def find_all_by_license(self, license_id: uuid.UUID) -> List[Activation]:
        """
        Find all activations for a license (active and inactive).

        Args:
            license_id: License UUID

        Returns:
            List of Activation entities
        """
        models = await sync_to_async(
            lambda: list(
                ActivationModel.objects.filter(license_id=license_id)  # pylint: disable=no-member
            )
        )()
        return [self._to_domain(model) for model in models]

    async def exists(self, activation_id: uuid.UUID) -> bool:
        """
        Check if an activation exists.

        Args:
            activation_id: Activation UUID

        Returns:
            True if activation exists, False otherwise
        """
        return await sync_to_async(
            lambda: ActivationModel.objects.filter(
                id=activation_id
            ).exists()  # pylint: disable=no-member
        )()
