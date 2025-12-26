"""
CancelLicenseCommand - US2.

Command to cancel a license.
"""

import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class CancelLicenseCommand:
    """Command to cancel a license."""

    license_id: uuid.UUID
    reason: Optional[str] = None
