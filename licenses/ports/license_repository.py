"""
License repository port (interface).

This defines the contract for license persistence operations.
Implementations are in the infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from licenses.domain.license import License


class LicenseRepository(ABC):
    """
    Abstract repository for License entities.

    This is a port in hexagonal architecture - it defines
    what operations are available, not how they're implemented.
    """

    @abstractmethod
    async def save(self, license: License) -> License:
        """
        Save a license entity.

        Args:
            license: License entity to save

        Returns:
            Saved license entity
        """
        pass

    @abstractmethod
    async def find_by_id(self, license_id: uuid.UUID) -> Optional[License]:
        """
        Find a license by ID.

        Args:
            license_id: License UUID

        Returns:
            License entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_license_key(
        self, license_key_id: uuid.UUID
    ) -> List[License]:
        """
        Find all licenses for a license key.

        Args:
            license_key_id: License key UUID

        Returns:
            List of License entities
        """
        pass

    @abstractmethod
    async def find_by_license_key_and_product(
        self, license_key_id: uuid.UUID, product_id: uuid.UUID
    ) -> Optional[License]:
        """
        Find a license by license key and product.

        Args:
            license_key_id: License key UUID
            product_id: Product UUID

        Returns:
            License entity or None if not found
        """
        pass

    @abstractmethod
    async def exists(self, license_id: uuid.UUID) -> bool:
        """
        Check if a license exists.

        Args:
            license_id: License UUID

        Returns:
            True if license exists, False otherwise
        """
        pass

