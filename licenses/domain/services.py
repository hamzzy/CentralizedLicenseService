"""
License domain services.

Domain services contain business logic that doesn't naturally
fit within a single entity.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from brands.ports.brand_repository import BrandRepository
from licenses.domain.license import License
from licenses.domain.license_key import LicenseKey


class LicenseKeyGenerator:
    """Domain service for license key generation."""

    @staticmethod
    def generate(brand_prefix: str) -> str:
        """
        Generate a license key.

        Args:
            brand_prefix: Brand prefix

        Returns:
            Generated license key string
        """
        from licenses.domain.license_key import generate_license_key

        return generate_license_key(brand_prefix)


class LicenseValidator:
    """Domain service for license validation."""

    @staticmethod
    def validate_license(license: License) -> tuple[bool, Optional[str]]:
        """
        Validate a license.

        Args:
            license: License entity to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not license.is_valid():
            if license.status.value == "expired":
                return False, "License has expired"
            if license.status.value == "suspended":
                return False, "License is suspended"
            if license.status.value == "cancelled":
                return False, "License is cancelled"
            return False, "License is not valid"

        return True, None

    @staticmethod
    def can_activate(
        license: License, seats_used: int
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a license can be activated.

        Args:
            license: License entity
            seats_used: Number of seats currently used

        Returns:
            Tuple of (can_activate, error_message)
        """
        is_valid, error = LicenseValidator.validate_license(license)
        if not is_valid:
            return False, error

        if seats_used >= license.seat_limit:
            return False, "License seat limit exceeded"

        return True, None


class LicenseLifecycleManager:
    """Domain service for managing license lifecycle."""

    @staticmethod
    async def renew_license(
        license: License,
        new_expiration: datetime,
        repository: "LicenseRepository",  # noqa: F821
    ) -> License:
        """
        Renew a license.

        Args:
            license: License entity to renew
            new_expiration: New expiration datetime
            repository: License repository

        Returns:
            Renewed license entity
        """
        renewed = license.renew(new_expiration)
        return await repository.save(renewed)

    @staticmethod
    async def suspend_license(
        license: License,
        repository: "LicenseRepository",  # noqa: F821
    ) -> License:
        """
        Suspend a license.

        Args:
            license: License entity to suspend
            repository: License repository

        Returns:
            Suspended license entity
        """
        suspended = license.suspend()
        return await repository.save(suspended)

    @staticmethod
    async def resume_license(
        license: License,
        repository: "LicenseRepository",  # noqa: F821
    ) -> License:
        """
        Resume a license.

        Args:
            license: License entity to resume
            repository: License repository

        Returns:
            Resumed license entity
        """
        resumed = license.resume()
        return await repository.save(resumed)

    @staticmethod
    async def cancel_license(
        license: License,
        repository: "LicenseRepository",  # noqa: F821
    ) -> License:
        """
        Cancel a license.

        Args:
            license: License entity to cancel
            repository: License repository

        Returns:
            Cancelled license entity
        """
        cancelled = license.cancel()
        return await repository.save(cancelled)

