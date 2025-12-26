"""
Brand domain entity.

This is the core domain entity representing a brand/tenant.
It contains business logic and is independent of infrastructure.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.domain.value_objects import BrandSlug


@dataclass(frozen=True)
class Brand:
    """
    Brand domain entity.

    Represents a brand/tenant in the system.
    This is an immutable value object with business logic.
    """

    id: uuid.UUID
    name: str
    slug: BrandSlug
    prefix: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate brand entity."""
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Brand name cannot be empty")
        if len(self.name) > 255:
            raise ValueError("Brand name too long")
        if not self.prefix or len(self.prefix.strip()) == 0:
            raise ValueError("Brand prefix cannot be empty")
        if len(self.prefix) < 2 or len(self.prefix) > 10:
            raise ValueError("Brand prefix must be between 2 and 10 characters")
        if not self.prefix.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Brand prefix must contain only alphanumeric characters, hyphens, or underscores"
            )

    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        prefix: str,
        brand_id: Optional[uuid.UUID] = None,
    ) -> "Brand":
        """
        Create a new Brand entity.

        Args:
            name: Brand display name
            slug: Brand slug (URL-safe identifier)
            prefix: License key prefix
            brand_id: Optional UUID (generated if not provided)

        Returns:
            Brand entity instance
        """
        now = datetime.utcnow()
        return cls(
            id=brand_id or uuid.uuid4(),
            name=name.strip(),
            slug=BrandSlug(slug),
            prefix=prefix.strip().upper(),
            created_at=now,
            updated_at=now,
        )

    def update_name(self, new_name: str) -> "Brand":
        """
        Create a new Brand instance with updated name.

        Args:
            new_name: New brand name

        Returns:
            New Brand instance with updated name
        """
        return Brand(
            id=self.id,
            name=new_name.strip(),
            slug=self.slug,
            prefix=self.prefix,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )
