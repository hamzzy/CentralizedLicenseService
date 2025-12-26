"""
Brand domain events.

Domain events represent something that happened in the brand domain.
"""
import uuid
from datetime import datetime
from typing import Optional

from core.domain.events import DomainEvent


class BrandCreated(DomainEvent):
    """Event raised when a brand is created."""

    def __init__(
        self,
        brand_id: uuid.UUID,
        name: str,
        slug: str,
        prefix: str,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize BrandCreated event.

        Args:
            brand_id: Brand UUID
            name: Brand name
            slug: Brand slug
            prefix: Brand prefix
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(brand_id),
            event_type="BrandCreated",
        )
        self.brand_id = brand_id
        self.name = name
        self.slug = slug
        self.prefix = prefix


class ProductCreated(DomainEvent):
    """Event raised when a product is created."""

    def __init__(
        self,
        product_id: uuid.UUID,
        brand_id: uuid.UUID,
        name: str,
        slug: str,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize ProductCreated event.

        Args:
            product_id: Product UUID
            brand_id: Brand UUID
            name: Product name
            slug: Product slug
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(product_id),
            event_type="ProductCreated",
        )
        self.product_id = product_id
        self.brand_id = brand_id
        self.name = name
        self.slug = slug

