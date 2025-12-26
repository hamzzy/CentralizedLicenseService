"""
LicenseKey repository port (interface).

This defines the contract for license key persistence operations.
Implementations are in the infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from licenses.domain.license_key import LicenseKey


class LicenseKeyRepository(ABC):
    """
    Abstract repository for LicenseKey entities.

    This is a port in hexagonal architecture - it defines
    what operations are available, not how they're implemented.
    """

    @abstractmethod
    async def save(self, license_key: LicenseKey) -> LicenseKey:
        """
        Save a license key entity.

        Args:
            license_key: LicenseKey entity to save

        Returns:
            Saved license key entity
        """
        pass

    @abstractmethod
    async def find_by_id(
        self, license_key_id: uuid.UUID
    ) -> Optional[LicenseKey]:
        """
        Find a license key by ID.

        Args:
            license_key_id: License key UUID

        Returns:
            LicenseKey entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_key(self, key: str) -> Optional[LicenseKey]:
        """
        Find a license key by key string.

        Args:
            key: License key string

        Returns:
            LicenseKey entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_key_hash(
        self, key_hash: str
    ) -> Optional[LicenseKey]:
        """
        Find a license key by key hash.

        Args:
            key_hash: License key hash

        Returns:
            LicenseKey entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_customer_email(
        self, brand_id: uuid.UUID, email: str
    ) -> List[LicenseKey]:
        """
        Find license keys by customer email and brand.

        Args:
            brand_id: Brand UUID
            email: Customer email

        Returns:
            List of LicenseKey entities
        """
        pass

    @abstractmethod
    async def exists(self, license_key_id: uuid.UUID) -> bool:
        """
        Check if a license key exists.

        Args:
            license_key_id: License key UUID

        Returns:
            True if license key exists, False otherwise
        """
        pass

