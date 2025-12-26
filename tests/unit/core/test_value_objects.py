"""
Unit tests for core value objects.
"""
import pytest

from core.domain.exceptions import DomainException
from core.domain.value_objects import (
    BrandSlug,
    Email,
    InstanceIdentifier,
    InstanceType,
    LicenseStatus,
    ProductSlug,
)


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email(self):
        """Test valid email creation."""
        email = Email("test@example.com")
        assert str(email) == "test@example.com"
        assert email.value == "test@example.com"

    def test_invalid_email_no_at(self):
        """Test invalid email without @."""
        with pytest.raises(ValueError, match="Invalid email"):
            Email("invalid-email")

    def test_invalid_email_empty(self):
        """Test invalid empty email."""
        with pytest.raises(ValueError, match="Invalid email"):
            Email("")


class TestBrandSlug:
    """Tests for BrandSlug value object."""

    def test_valid_slug(self):
        """Test valid brand slug."""
        slug = BrandSlug("rankmath")
        assert str(slug) == "rankmath"

    def test_valid_slug_with_hyphens(self):
        """Test valid slug with hyphens."""
        slug = BrandSlug("wp-rocket")
        assert str(slug) == "wp-rocket"

    def test_invalid_slug_empty(self):
        """Test invalid empty slug."""
        with pytest.raises(ValueError, match="cannot be empty"):
            BrandSlug("")

    def test_invalid_slug_special_chars(self):
        """Test invalid slug with special characters."""
        with pytest.raises(ValueError, match="Invalid brand slug"):
            BrandSlug("rank@math")


class TestProductSlug:
    """Tests for ProductSlug value object."""

    def test_valid_slug(self):
        """Test valid product slug."""
        slug = ProductSlug("rankmath-pro")
        assert str(slug) == "rankmath-pro"

    def test_invalid_slug_empty(self):
        """Test invalid empty slug."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ProductSlug("")


class TestLicenseStatus:
    """Tests for LicenseStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert LicenseStatus.VALID.value == "valid"
        assert LicenseStatus.SUSPENDED.value == "suspended"
        assert LicenseStatus.CANCELLED.value == "cancelled"
        assert LicenseStatus.EXPIRED.value == "expired"

    def test_status_string(self):
        """Test status string representation."""
        assert str(LicenseStatus.VALID) == "valid"


class TestInstanceType:
    """Tests for InstanceType enum."""

    def test_instance_type_values(self):
        """Test instance type enum values."""
        assert InstanceType.URL.value == "url"
        assert InstanceType.HOSTNAME.value == "hostname"
        assert InstanceType.MACHINE_ID.value == "machine_id"


class TestInstanceIdentifier:
    """Tests for InstanceIdentifier value object."""

    def test_valid_identifier(self):
        """Test valid instance identifier."""
        identifier = InstanceIdentifier(
            "https://example.com", InstanceType.URL
        )
        assert str(identifier) == "https://example.com"
        assert identifier.instance_type == InstanceType.URL

    def test_invalid_identifier_empty(self):
        """Test invalid empty identifier."""
        with pytest.raises(ValueError, match="cannot be empty"):
            InstanceIdentifier("", InstanceType.URL)

    def test_invalid_identifier_too_long(self):
        """Test invalid identifier too long."""
        long_string = "x" * 501
        with pytest.raises(ValueError, match="too long"):
            InstanceIdentifier(long_string, InstanceType.URL)

