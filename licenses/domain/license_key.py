"""
LicenseKey domain entity.

This is the core domain entity representing a license key.
It contains business logic and is independent of infrastructure.
"""

import hashlib
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.domain.value_objects import Email


def generate_license_key(brand_prefix: str) -> str:
    """
    Generate a license key in format: PREFIX-XXXX-XXXX-XXXX-XXXX.

    Args:
        brand_prefix: Brand prefix (e.g., 'RM' for RankMath)

    Returns:
        Generated license key string
    """
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
    return f"{brand_prefix}-{'-'.join(parts)}"


@dataclass(frozen=True)
class LicenseKey:
    """
    LicenseKey domain entity.

    Represents a license key that can contain multiple licenses.
    This is an immutable value object with business logic.
    """

    id: uuid.UUID
    brand_id: uuid.UUID
    key: str
    key_hash: str
    customer_email: Email
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate license key entity."""
        if not self.key or len(self.key.strip()) == 0:
            raise ValueError("License key cannot be empty")
        if len(self.key) > 100:
            raise ValueError("License key too long")
        if not self.key_hash or len(self.key_hash) != 64:
            raise ValueError("Invalid key hash")
        if not self.brand_id:
            raise ValueError("Brand ID is required")

    @classmethod
    def create(
        cls,
        brand_id: uuid.UUID,
        brand_prefix: str,
        customer_email: str,
        license_key_id: Optional[uuid.UUID] = None,
    ) -> "LicenseKey":
        """
        Create a new LicenseKey entity.

        Args:
            brand_id: Brand UUID
            brand_prefix: Brand prefix for key generation
            customer_email: Customer email address
            license_key_id: Optional UUID (generated if not provided)

        Returns:
            LicenseKey entity instance
        """
        now = datetime.utcnow()
        key = generate_license_key(brand_prefix)
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        return cls(
            id=license_key_id or uuid.uuid4(),
            brand_id=brand_id,
            key=key,
            key_hash=key_hash,
            customer_email=Email(customer_email),
            created_at=now,
            updated_at=now,
        )

    def verify_key(self, raw_key: str) -> bool:
        """
        Verify a raw license key against the stored hash.

        Args:
            raw_key: The raw license key to verify

        Returns:
            True if key matches, False otherwise
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return secrets.compare_digest(self.key_hash, key_hash)
