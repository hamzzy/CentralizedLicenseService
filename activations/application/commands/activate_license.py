"""
ActivateLicenseCommand - US3.

Command to activate a license for a specific instance.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from core.domain.value_objects import InstanceType


@dataclass
class ActivateLicenseCommand:
    """Command to activate a license for an instance."""

    license_key: str
    product_slug: str
    instance_identifier: str
    instance_type: InstanceType
    instance_metadata: Optional[Dict] = None
