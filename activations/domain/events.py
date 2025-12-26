"""
Activation domain events.

Domain events represent something that happened in the activation domain.
"""
import uuid
from datetime import datetime
from typing import Optional

from core.domain.events import DomainEvent


class LicenseActivated(DomainEvent):
    """Event raised when a license is activated."""

    def __init__(
        self,
        activation_id: uuid.UUID,
        license_id: uuid.UUID,
        instance_identifier: str,
        instance_type: str,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize LicenseActivated event.

        Args:
            activation_id: Activation UUID
            license_id: License UUID
            instance_identifier: Instance identifier
            instance_type: Instance type
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(activation_id),
            event_type="LicenseActivated",
        )
        self.activation_id = activation_id
        self.license_id = license_id
        self.instance_identifier = instance_identifier
        self.instance_type = instance_type


class SeatDeactivated(DomainEvent):
    """Event raised when a seat is deactivated."""

    def __init__(
        self,
        activation_id: uuid.UUID,
        license_id: uuid.UUID,
        instance_identifier: str,
        occurred_at: Optional[datetime] = None,
    ):
        """
        Initialize SeatDeactivated event.

        Args:
            activation_id: Activation UUID
            license_id: License UUID
            instance_identifier: Instance identifier
            occurred_at: When the event occurred
        """
        super().__init__(
            event_id=uuid.uuid4(),
            occurred_at=occurred_at or datetime.utcnow(),
            aggregate_id=str(activation_id),
            event_type="SeatDeactivated",
        )
        self.activation_id = activation_id
        self.license_id = license_id
        self.instance_identifier = instance_identifier

