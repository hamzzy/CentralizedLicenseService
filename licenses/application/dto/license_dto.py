"""
License DTOs for API responses.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class LicenseDTO:
    """DTO for license information."""

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    status: str
    seat_limit: int
    seats_used: int
    seats_remaining: int
    expires_at: Optional[datetime]
    created_at: datetime


@dataclass
class LicenseKeyDTO:
    """DTO for license key information."""

    id: uuid.UUID
    key: str
    brand_id: uuid.UUID
    customer_email: str
    created_at: datetime


@dataclass
class ProvisionLicenseResponseDTO:
    """DTO for provision license response."""

    license_key: LicenseKeyDTO
    licenses: List[LicenseDTO]


@dataclass
class LicenseStatusDTO:
    """DTO for license status response - US4."""

    license_key: str
    status: str  # Overall status (valid if any license is valid)
    is_valid: bool
    licenses: List[LicenseDTO]
    total_seats_used: int
    total_seats_available: int


@dataclass
class LicenseListItemDTO:
    """DTO for license list item - US6."""

    license_key: str
    brand_name: str
    product_name: str
    status: str
    expires_at: Optional[datetime]
    seats_used: int
    seat_limit: int

