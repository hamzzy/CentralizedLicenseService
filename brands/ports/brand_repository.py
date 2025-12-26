"""
Brand repository port (interface).

This defines the contract for brand persistence operations.
Implementations are in the infrastructure layer.
"""

import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from brands.domain.brand import Brand


class BrandRepository(ABC):
    """
    Abstract repository for Brand entities.

    This is a port in hexagonal architecture - it defines
    what operations are available, not how they're implemented.
    """

    @abstractmethod
    async def save(self, brand: Brand) -> Brand:
        """
        Save a brand entity.

        Args:
            brand: Brand entity to save

        Returns:
            Saved brand entity
        """
        pass

    @abstractmethod
    async def find_by_id(self, brand_id: uuid.UUID) -> Optional[Brand]:
        """
        Find a brand by ID.

        Args:
            brand_id: Brand UUID

        Returns:
            Brand entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_slug(self, slug: str) -> Optional[Brand]:
        """
        Find a brand by slug.

        Args:
            slug: Brand slug

        Returns:
            Brand entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_prefix(self, prefix: str) -> Optional[Brand]:
        """
        Find a brand by prefix.

        Args:
            prefix: Brand prefix

        Returns:
            Brand entity or None if not found
        """
        pass

    @abstractmethod
    async def exists(self, brand_id: uuid.UUID) -> bool:
        """
        Check if a brand exists.

        Args:
            brand_id: Brand UUID

        Returns:
            True if brand exists, False otherwise
        """
        pass

    @abstractmethod
    async def list_all(self) -> List[Brand]:
        """
        List all brands.

        Returns:
            List of Brand entities
        """
        pass
