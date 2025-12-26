"""
License domain events.

Domain events represent something that happened in the license domain.
"""

import uuid
from datetime import datetime
from typing import Optional

from core.domain.events import DomainEvent


class LicenseKeyCreated(DomainEvent):
    """Event raised when a license key is created."""

    def __init__(
        self,
        license_key_id: uuid.UUID,
        brand_id: uuid.UUID,
        customer_email: str,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize LicenseKeyCreated event.

        Args:
            license_key_id: License key UUID
            brand_id: Brand UUID
            customer_email: Customer email
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(license_key_id),
            event_type="LicenseKeyCreated",
        )
        self.license_key_id = license_key_id
        self.brand_id = brand_id
        self.customer_email = customer_email


class LicenseProvisioned(DomainEvent):
    """Event raised when a license is provisioned."""

    def __init__(
        self,
        license_id: uuid.UUID,
        license_key_id: uuid.UUID,
        product_id: uuid.UUID,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize LicenseProvisioned event.

        Args:
            license_id: License UUID
            license_key_id: License key UUID
            product_id: Product UUID
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(license_id),
            event_type="LicenseProvisioned",
        )
        self.license_id = license_id
        self.license_key_id = license_key_id
        self.product_id = product_id


class LicenseRenewed(DomainEvent):
    """Event raised when a license is renewed."""

    def __init__(
        self,
        license_id: uuid.UUID,
        new_expiration: datetime,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize LicenseRenewed event.

        Args:
            license_id: License UUID
            new_expiration: New expiration datetime
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(license_id),
            event_type="LicenseRenewed",
        )
        self.license_id = license_id
        self.new_expiration = new_expiration


class LicenseSuspended(DomainEvent):
    """Event raised when a license is suspended."""

    def __init__(
        self,
        license_id: uuid.UUID,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize LicenseSuspended event.

        Args:
            license_id: License UUID
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(license_id),
            event_type="LicenseSuspended",
        )
        self.license_id = license_id


class LicenseResumed(DomainEvent):
    """Event raised when a license is resumed."""

    def __init__(
        self,
        license_id: uuid.UUID,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize LicenseResumed event.

        Args:
            license_id: License UUID
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(license_id),
            event_type="LicenseResumed",
        )
        self.license_id = license_id


class LicenseCancelled(DomainEvent):
    """Event raised when a license is cancelled."""

    def __init__(
        self,
        license_id: uuid.UUID,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize LicenseCancelled event.

        Args:
            license_id: License UUID
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(license_id),
            event_type="LicenseCancelled",
        )
        self.license_id = license_id
