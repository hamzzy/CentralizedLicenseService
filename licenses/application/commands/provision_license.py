"""
ProvisionLicenseCommand - US1.

Command to provision a license key and licenses for a customer.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ProvisionLicenseCommand:
    """
    Command to provision a license key and licenses.

    This command creates:
    - A license key for the customer
    - One or more licenses associated with that key
    """

    brand_id: uuid.UUID
    customer_email: str
    products: List[uuid.UUID]  # Product IDs
    expiration_date: Optional[datetime] = None
    max_seats: int = 1  # Default seat limit per license
