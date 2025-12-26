"""
RenewLicenseCommand - US2.

Command to renew (extend) a license.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RenewLicenseCommand:
    """Command to renew a license with a new expiration date."""

    license_id: uuid.UUID
    expiration_date: datetime

