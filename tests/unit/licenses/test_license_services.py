"""
Unit tests for License domain services.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.domain.value_objects import LicenseStatus
from licenses.domain.license import License
from licenses.domain.services import LicenseValidator


class TestLicenseValidator:
    """Tests for LicenseValidator service."""

    def test_validate_valid_license(self):
        """Test validating a valid license."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            expires_at=expires_at,
        )

        is_valid, error = LicenseValidator.validate_license(license)

        assert is_valid is True
        assert error is None

    def test_validate_expired_license(self):
        """Test validating an expired license."""
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            expires_at=expires_at,
        )

        is_valid, error = LicenseValidator.validate_license(license)

        assert is_valid is False
        assert "expired" in error.lower()

    def test_validate_suspended_license(self):
        """Test validating a suspended license."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        suspended = license.suspend()

        is_valid, error = LicenseValidator.validate_license(suspended)

        assert is_valid is False
        assert "suspended" in error.lower()

    def test_validate_cancelled_license(self):
        """Test validating a cancelled license."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        cancelled = license.cancel()

        is_valid, error = LicenseValidator.validate_license(cancelled)

        assert is_valid is False
        assert "cancelled" in error.lower()

    def test_can_activate_valid_license_with_seats(self):
        """Test can_activate for valid license with available seats."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            seat_limit=5,
        )

        can_activate, error = LicenseValidator.can_activate(license, 2)

        assert can_activate is True
        assert error is None

    def test_can_activate_seat_limit_exceeded(self):
        """Test can_activate when seat limit is exceeded."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            seat_limit=5,
        )

        can_activate, error = LicenseValidator.can_activate(license, 5)

        assert can_activate is False
        assert "exceeded" in error.lower()

    def test_can_activate_invalid_license(self):
        """Test can_activate for invalid license."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        suspended = license.suspend()

        can_activate, error = LicenseValidator.can_activate(suspended, 0)

        assert can_activate is False
        assert error is not None
