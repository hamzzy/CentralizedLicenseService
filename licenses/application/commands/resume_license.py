"""
ResumeLicenseCommand - US2.

Command to resume a suspended license.
"""
import uuid
from dataclasses import dataclass


@dataclass
class ResumeLicenseCommand:
    """Command to resume a suspended license."""

    license_id: uuid.UUID

