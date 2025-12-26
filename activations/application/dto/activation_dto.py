"""
Activation DTOs for API responses.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class ActivationDTO:
    """DTO for activation information."""

    id: uuid.UUID
    license_id: uuid.UUID
    instance_identifier: str
    instance_type: str
    instance_metadata: Dict
    activated_at: datetime
    last_checked_at: datetime
    is_active: bool


@dataclass
class ActivateLicenseResponseDTO:
    """DTO for activate license response - US3."""

    activation_id: uuid.UUID
    license_id: uuid.UUID
    seats_remaining: int
    message: str


@dataclass
class ActivationStatusDTO:
    """DTO for activation status response."""

    is_activated: bool
    activation_id: Optional[uuid.UUID]
    activated_at: Optional[datetime]
    instance_identifier: str

