"""
Activation repository port (interface).

This defines the contract for activation persistence operations.
Implementations are in the infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from activations.domain.activation import Activation


class ActivationRepository(ABC):
    """
    Abstract repository for Activation entities.

    This is a port in hexagonal architecture - it defines
    what operations are available, not how they're implemented.
    """

    @abstractmethod
    async def save(self, activation: Activation) -> Activation:
        """
        Save an activation entity.

        Args:
            activation: Activation entity to save

        Returns:
            Saved activation entity
        """
        pass

    @abstractmethod
    async def find_by_id(
        self, activation_id: uuid.UUID
    ) -> Optional[Activation]:
        """
        Find an activation by ID.

        Args:
            activation_id: Activation UUID

        Returns:
            Activation entity or None if not found
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def find_active_by_license(
        self, license_id: uuid.UUID
    ) -> List[Activation]:
        """
        Find all active activations for a license.

        Args:
            license_id: License UUID

        Returns:
            List of active Activation entities
        """
        pass

    @abstractmethod
    async def find_all_by_license(
        self, license_id: uuid.UUID
    ) -> List[Activation]:
        """
        Find all activations for a license (active and inactive).

        Args:
            license_id: License UUID

        Returns:
            List of Activation entities
        """
        pass

    @abstractmethod
    async def exists(self, activation_id: uuid.UUID) -> bool:
        """
        Check if an activation exists.

        Args:
            activation_id: Activation UUID

        Returns:
            True if activation exists, False otherwise
        """
        pass

