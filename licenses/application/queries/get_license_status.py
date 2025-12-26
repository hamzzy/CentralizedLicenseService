"""
GetLicenseStatusQuery - US4.

Query to get license status and entitlements.
"""
from dataclasses import dataclass


@dataclass
class GetLicenseStatusQuery:
    """Query to get license status for a license key."""

    license_key: str

