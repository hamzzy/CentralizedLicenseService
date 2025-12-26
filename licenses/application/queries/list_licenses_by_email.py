"""
ListLicensesByEmailQuery - US6.

Query to list all licenses for a customer email across all brands.
"""

import uuid
from dataclasses import dataclass


@dataclass
class ListLicensesByEmailQuery:
    """
    Query to list licenses by customer email.

    Note: brand_id is extracted from tenant context (API key).
    """

    customer_email: str
    brand_id: uuid.UUID  # From tenant context
