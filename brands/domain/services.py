"""
Brand domain services.

Domain services contain business logic that doesn't naturally
fit within a single entity.
"""
import uuid
from typing import Optional

from brands.domain.brand import Brand
from brands.domain.product import Product


class BrandValidator:
    """Domain service for brand validation."""

    @staticmethod
    def validate_prefix(prefix: str) -> bool:
        """
        Validate brand prefix format.

        Args:
            prefix: Brand prefix to validate

        Returns:
            True if valid, False otherwise
        """
        if not prefix or len(prefix.strip()) == 0:
            return False
        if len(prefix) < 2 or len(prefix) > 10:
            return False
        if not prefix.replace("-", "").replace("_", "").isalnum():
            return False
        return True

    @staticmethod
    def validate_name(name: str) -> bool:
        """
        Validate brand name.

        Args:
            name: Brand name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or len(name.strip()) == 0:
            return False
        if len(name) > 255:
            return False
        return True


class ProductValidator:
    """Domain service for product validation."""

    @staticmethod
    def validate_name(name: str) -> bool:
        """
        Validate product name.

        Args:
            name: Product name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or len(name.strip()) == 0:
            return False
        if len(name) > 255:
            return False
        return True

    @staticmethod
    def belongs_to_brand(
        product: Product, brand_id: Optional[uuid.UUID]
    ) -> bool:
        """
        Check if product belongs to a brand.

        Args:
            product: Product entity
            brand_id: Brand UUID to check

        Returns:
            True if product belongs to brand
        """
        if not brand_id:
            return False
        return product.brand_id == brand_id

