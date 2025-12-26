"""
Product domain entity.

This is the core domain entity representing a product.
It contains business logic and is independent of infrastructure.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.domain.value_objects import ProductSlug


@dataclass(frozen=True)
class Product:
    """
    Product domain entity.

    Represents a product that can be licensed.
    This is an immutable value object with business logic.
    """

    id: uuid.UUID
    brand_id: uuid.UUID
    name: str
    slug: ProductSlug
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate product entity."""
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Product name cannot be empty")
        if len(self.name) > 255:
            raise ValueError("Product name too long")
        if not self.brand_id:
            raise ValueError("Brand ID is required")

    @classmethod
    def create(
        cls,
        brand_id: uuid.UUID,
        name: str,
        slug: str,
        product_id: Optional[uuid.UUID] = None,
    ) -> "Product":
        """
        Create a new Product entity.

        Args:
            brand_id: Brand UUID this product belongs to
            name: Product display name
            slug: Product slug (URL-safe identifier)
            product_id: Optional UUID (generated if not provided)

        Returns:
            Product entity instance
        """
        now = datetime.utcnow()
        return cls(
            id=product_id or uuid.uuid4(),
            brand_id=brand_id,
            name=name.strip(),
            slug=ProductSlug(slug),
            created_at=now,
            updated_at=now,
        )

    def update_name(self, new_name: str) -> "Product":
        """
        Create a new Product instance with updated name.

        Args:
            new_name: New product name

        Returns:
            New Product instance with updated name
        """
        return Product(
            id=self.id,
            brand_id=self.brand_id,
            name=new_name.strip(),
            slug=self.slug,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

