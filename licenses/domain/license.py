"""
License domain entity.

This is the core domain entity representing a license.
It contains business logic and is independent of infrastructure.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.domain.value_objects import LicenseStatus


@dataclass(frozen=True)
class License:
    """
    License domain entity.

    Represents a license that grants access to a specific product.
    This is an immutable value object with business logic.
    """

    id: uuid.UUID
    license_key_id: uuid.UUID
    product_id: uuid.UUID
    status: LicenseStatus
    seat_limit: int
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate license entity."""
        if not self.license_key_id:
            raise ValueError("License key ID is required")
        if not self.product_id:
            raise ValueError("Product ID is required")
        if self.seat_limit < 1:
            raise ValueError("Seat limit must be at least 1")

    @classmethod
    def create(
        cls,
        license_key_id: uuid.UUID,
        product_id: uuid.UUID,
        seat_limit: int = 1,
        expires_at: Optional[datetime] = None,
        license_id: Optional[uuid.UUID] = None,
    ) -> "License":
        """
        Create a new License entity.

        Args:
            license_key_id: License key UUID
            product_id: Product UUID
            seat_limit: Maximum number of activations
            expires_at: Optional expiration datetime
            license_id: Optional UUID (generated if not provided)

        Returns:
            License entity instance
        """
        now = datetime.utcnow()
        return cls(
            id=license_id or uuid.uuid4(),
            license_key_id=license_key_id,
            product_id=product_id,
            status=LicenseStatus.VALID,
            seat_limit=seat_limit,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )

    def is_valid(self, current_time: Optional[datetime] = None) -> bool:
        """
        Check if license is currently valid.

        Args:
            current_time: Current time (defaults to utcnow)

        Returns:
            True if license is valid and not expired
        """
        if self.status != LicenseStatus.VALID:
            return False
        if self.expires_at:
            check_time = current_time or datetime.utcnow()
            if self.expires_at < check_time:
                return False
        return True

    def renew(self, new_expiration: datetime) -> "License":
        """
        Create a new License instance with renewed expiration.

        Args:
            new_expiration: New expiration datetime

        Returns:
            New License instance with updated expiration
        """
        if new_expiration < datetime.utcnow():
            raise ValueError("Expiration date cannot be in the past")

        new_status = (
            LicenseStatus.VALID
            if self.status == LicenseStatus.EXPIRED
            else self.status
        )

        return License(
            id=self.id,
            license_key_id=self.license_key_id,
            product_id=self.product_id,
            status=new_status,
            seat_limit=self.seat_limit,
            expires_at=new_expiration,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

    def suspend(self) -> "License":
        """
        Create a new License instance with suspended status.

        Returns:
            New License instance with suspended status
        """
        if self.status == LicenseStatus.CANCELLED:
            raise ValueError("Cannot suspend a cancelled license")

        return License(
            id=self.id,
            license_key_id=self.license_key_id,
            product_id=self.product_id,
            status=LicenseStatus.SUSPENDED,
            seat_limit=self.seat_limit,
            expires_at=self.expires_at,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

    def resume(self) -> "License":
        """
        Create a new License instance with resumed status.

        Returns:
            New License instance with valid status
        """
        if self.status != LicenseStatus.SUSPENDED:
            raise ValueError("Can only resume a suspended license")

        return License(
            id=self.id,
            license_key_id=self.license_key_id,
            product_id=self.product_id,
            status=LicenseStatus.VALID,
            seat_limit=self.seat_limit,
            expires_at=self.expires_at,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

    def cancel(self) -> "License":
        """
        Create a new License instance with cancelled status.

        Returns:
            New License instance with cancelled status
        """
        return License(
            id=self.id,
            license_key_id=self.license_key_id,
            product_id=self.product_id,
            status=LicenseStatus.CANCELLED,
            seat_limit=self.seat_limit,
            expires_at=self.expires_at,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

    def mark_expired(self) -> "License":
        """
        Create a new License instance with expired status.

        Returns:
            New License instance with expired status
        """
        return License(
            id=self.id,
            license_key_id=self.license_key_id,
            product_id=self.product_id,
            status=LicenseStatus.EXPIRED,
            seat_limit=self.seat_limit,
            expires_at=self.expires_at,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

