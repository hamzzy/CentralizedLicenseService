"""
Activation domain entity.

This is the core domain entity representing a license activation.
It contains business logic and is independent of infrastructure.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from core.domain.value_objects import InstanceIdentifier, InstanceType


@dataclass(frozen=True)
class Activation:
    """
    Activation domain entity.

    Represents a specific instance where a license is activated.
    This is an immutable value object with business logic.
    """

    id: uuid.UUID
    license_id: uuid.UUID
    instance_identifier: InstanceIdentifier
    instance_metadata: Dict
    activated_at: datetime
    last_checked_at: datetime
    deactivated_at: Optional[datetime]
    is_active: bool

    def __post_init__(self):
        """Validate activation entity."""
        if not self.license_id:
            raise ValueError("License ID is required")
        if not self.instance_identifier:
            raise ValueError("Instance identifier is required")

    @classmethod
    def create(
        cls,
        license_id: uuid.UUID,
        instance_identifier: str,
        instance_type: InstanceType,
        instance_metadata: Optional[Dict] = None,
        activation_id: Optional[uuid.UUID] = None,
    ) -> "Activation":
        """
        Create a new Activation entity.

        Args:
            license_id: License UUID
            instance_identifier: Instance identifier (URL, hostname, etc.)
            instance_type: Type of instance
            instance_metadata: Optional metadata dictionary
            activation_id: Optional UUID (generated if not provided)

        Returns:
            Activation entity instance
        """
        now = datetime.utcnow()
        return cls(
            id=activation_id or uuid.uuid4(),
            license_id=license_id,
            instance_identifier=InstanceIdentifier(instance_identifier, instance_type),
            instance_metadata=instance_metadata or {},
            activated_at=now,
            last_checked_at=now,
            deactivated_at=None,
            is_active=True,
        )

    def update_last_checked(self) -> "Activation":
        """
        Create a new Activation instance with updated last_checked_at.

        Returns:
            New Activation instance with updated timestamp
        """
        return Activation(
            id=self.id,
            license_id=self.license_id,
            instance_identifier=self.instance_identifier,
            instance_metadata=self.instance_metadata,
            activated_at=self.activated_at,
            last_checked_at=datetime.utcnow(),
            deactivated_at=self.deactivated_at,
            is_active=self.is_active,
        )

    def deactivate(self) -> "Activation":
        """
        Create a new Activation instance with deactivated status.

        Returns:
            New Activation instance with deactivated status
        """
        if not self.is_active:
            return self  # Already deactivated

        return Activation(
            id=self.id,
            license_id=self.license_id,
            instance_identifier=self.instance_identifier,
            instance_metadata=self.instance_metadata,
            activated_at=self.activated_at,
            last_checked_at=datetime.utcnow(),
            deactivated_at=datetime.utcnow(),
            is_active=False,
        )

    def reactivate(self) -> "Activation":
        """
        Create a new Activation instance with reactivated status.

        Returns:
            New Activation instance with active status
        """
        now = datetime.utcnow()
        return Activation(
            id=self.id,
            license_id=self.license_id,
            instance_identifier=self.instance_identifier,
            instance_metadata=self.instance_metadata,
            activated_at=now,  # Update activation time? Or keep original? Usually update.
            last_checked_at=now,
            deactivated_at=None,
            is_active=True,
        )
