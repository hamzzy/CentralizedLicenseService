"""
DeactivateSeatCommand - US5.

Command to deactivate a seat (free a license seat).
"""
from dataclasses import dataclass


@dataclass
class DeactivateSeatCommand:
    """Command to deactivate a seat for an instance."""

    license_key: str
    instance_identifier: str

