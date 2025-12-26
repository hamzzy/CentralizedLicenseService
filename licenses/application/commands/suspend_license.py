"""
SuspendLicenseCommand - US2.

Command to suspend a license.
"""
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class SuspendLicenseCommand:
    """Command to suspend a license."""

    license_id: uuid.UUID
    reason: Optional[str] = None

