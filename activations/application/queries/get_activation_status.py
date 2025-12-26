"""
GetActivationStatusQuery.

Query to get activation status for a license key and instance.
"""
from dataclasses import dataclass


@dataclass
class GetActivationStatusQuery:
    """Query to get activation status."""

    license_key: str
    instance_identifier: str
