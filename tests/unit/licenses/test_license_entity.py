"""
Unit tests for License domain entity.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.domain.value_objects import LicenseStatus
from licenses.domain.license import License


class TestLicenseEntity:
    """Tests for License domain entity."""

    def test_create_license(self):
        """Test creating a license entity."""
        license_key_id = uuid.uuid4()
        product_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)

        license = License.create(
            license_key_id=license_key_id,
            product_id=product_id,
            seat_limit=5,
            expires_at=expires_at,
        )

        assert license.license_key_id == license_key_id
        assert license.product_id == product_id
        assert license.status == LicenseStatus.VALID
        assert license.seat_limit == 5
        assert license.expires_at == expires_at

    def test_create_license_default_seats(self):
        """Test creating license with default seat limit."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )

        assert license.seat_limit == 1

    def test_is_valid_valid_license(self):
        """Test is_valid for valid license."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            expires_at=expires_at,
        )

        assert license.is_valid() is True

    def test_is_valid_expired_license(self):
        """Test is_valid for expired license."""
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            expires_at=expires_at,
        )

        assert license.is_valid() is False

    def test_is_valid_suspended_license(self):
        """Test is_valid for suspended license."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        suspended = license.suspend()

        assert suspended.is_valid() is False
        assert suspended.status == LicenseStatus.SUSPENDED

    def test_renew_license(self):
        """Test renewing a license."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            expires_at=expires_at,
        )

        new_expiration = datetime.now(timezone.utc) + timedelta(days=365)
        renewed = license.renew(new_expiration)

        assert renewed.expires_at == new_expiration
        assert renewed.status == LicenseStatus.VALID

    def test_renew_expired_license(self):
        """Test renewing an expired license."""
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            expires_at=expires_at,
        )
        expired = license.mark_expired()

        new_expiration = datetime.now(timezone.utc) + timedelta(days=365)
        renewed = expired.renew(new_expiration)

        assert renewed.status == LicenseStatus.VALID

    def test_renew_past_expiration(self):
        """Test renewing with past expiration date."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )

        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        with pytest.raises(ValueError, match="cannot be in the past"):
            license.renew(past_date)

    def test_suspend_license(self):
        """Test suspending a license."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )

        suspended = license.suspend()

        assert suspended.status == LicenseStatus.SUSPENDED
        assert suspended.id == license.id

    def test_suspend_cancelled_license(self):
        """Test suspending a cancelled license fails."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        cancelled = license.cancel()

        with pytest.raises(ValueError, match="Cannot suspend"):
            cancelled.suspend()

    def test_resume_license(self):
        """Test resuming a suspended license."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        suspended = license.suspend()

        resumed = suspended.resume()

        assert resumed.status == LicenseStatus.VALID
        assert resumed.id == license.id

    def test_resume_valid_license(self):
        """Test resuming a valid license fails."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )

        with pytest.raises(ValueError, match="Can only resume"):
            license.resume()

    def test_cancel_license(self):
        """Test cancelling a license."""
        license = License.create(
            license_key_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )

        cancelled = license.cancel()

        assert cancelled.status == LicenseStatus.CANCELLED
        assert cancelled.id == license.id

    def test_invalid_seat_limit(self):
        """Test invalid seat limit."""
        with pytest.raises(ValueError, match="at least 1"):
            License.create(
                license_key_id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                seat_limit=0,
            )
