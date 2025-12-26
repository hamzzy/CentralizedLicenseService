"""
Product repository port (interface).

This defines the contract for product persistence operations.
Implementations are in the infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from brands.domain.product import Product


class ProductRepository(ABC):
    """
    Abstract repository for Product entities.

    This is a port in hexagonal architecture - it defines
    what operations are available, not how they're implemented.
    """

    @abstractmethod
    async def save(self, product: Product) -> Product:
        """
        Save a product entity.

        Args:
            product: Product entity to save

        Returns:
            Saved product entity
        """
        pass

    @abstractmethod
    async def find_by_id(self, product_id: uuid.UUID) -> Optional[Product]:
        """
        Find a product by ID.

        Args:
            product_id: Product UUID

        Returns:
            Product entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_slug(
        self, brand_id: uuid.UUID, slug: str
    ) -> Optional[Product]:
        """
        Find a product by brand and slug.

        Args:
            brand_id: Brand UUID
            slug: Product slug

        Returns:
            Product entity or None if not found
        """
        pass

    @abstractmethod
    async def list_by_brand(self, brand_id: uuid.UUID) -> List[Product]:
        """
        List all products for a brand.

        Args:
            brand_id: Brand UUID

        Returns:
            List of Product entities
        """
        pass

    @abstractmethod
    async def exists(self, product_id: uuid.UUID) -> bool:
        """
        Check if a product exists.

        Args:
            product_id: Product UUID

        Returns:
            True if product exists, False otherwise
        """
        pass

