"""
Integration tests for repository implementations.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from activations.domain.activation import Activation
from brands.domain.brand import Brand
from brands.domain.product import Product
from core.domain.value_objects import InstanceType
from licenses.domain.license import License
from licenses.domain.license_key import LicenseKey


@pytest.mark.django_db
@pytest.mark.integration
class TestBrandRepository:
    """Integration tests for BrandRepository."""

    @pytest.mark.asyncio
    async def test_save_and_find(self, brand_repository):
        """Test saving and finding a brand."""
        brand = Brand.create(
            name="Test Brand",
            slug="test-brand",
            prefix="TB",
        )

        saved = await brand_repository.save(brand)
        assert saved.id is not None

        found = await brand_repository.find(saved.id)
        assert found is not None
        assert found.name == "Test Brand"
        assert found.slug.value == "test-brand"

    @pytest.mark.asyncio
    async def test_find_not_found(self, brand_repository):
        """Test finding non-existent brand."""
        found = await brand_repository.find(uuid.uuid4())
        assert found is None

    @pytest.mark.asyncio
    async def test_exists(self, brand_repository):
        """Test checking brand existence."""
        brand = Brand.create(
            name="Test Brand",
            slug="test-brand-2",
            prefix="TB2",
        )
        saved = await brand_repository.save(brand)

        exists = await brand_repository.exists(saved.id)
        assert exists is True

        exists = await brand_repository.exists(uuid.uuid4())
        assert exists is False


@pytest.mark.django_db
@pytest.mark.integration
class TestLicenseRepository:
    """Integration tests for LicenseRepository."""

    @pytest.mark.asyncio
    async def test_save_and_find(
        self,
        license_repository,
        db_license_key,
        db_product,
    ):
        """Test saving and finding a license."""
        expires_at = datetime.utcnow() + timedelta(days=365)
        license = License.create(
            license_key_id=db_license_key.id,
            product_id=db_product.id,
            seat_limit=10,
            expires_at=expires_at,
        )

        saved = await license_repository.save(license)
        assert saved.id is not None

        found = await license_repository.find(saved.id)
        assert found is not None
        assert found.seat_limit == 10

    @pytest.mark.asyncio
    async def test_find_by_license_key(
        self,
        license_repository,
        db_license_key,
        db_product,
    ):
        """Test finding licenses by license key."""
        expires_at = datetime.utcnow() + timedelta(days=365)
        license1 = License.create(
            license_key_id=db_license_key.id,
            product_id=db_product.id,
            expires_at=expires_at,
        )
        await license_repository.save(license1)

        licenses = await license_repository.find_by_license_key(db_license_key.id)
        assert len(licenses) >= 1


@pytest.mark.django_db
@pytest.mark.integration
class TestActivationRepository:
    """Integration tests for ActivationRepository."""

    @pytest.mark.asyncio
    async def test_save_and_find(self, activation_repository, db_license):
        """Test saving and finding an activation."""
        activation = Activation.create(
            license_id=db_license.id,
            instance_identifier="https://test.com",
            instance_type=InstanceType.URL,
        )

        saved = await activation_repository.save(activation)
        assert saved.id is not None

        found = await activation_repository.find(saved.id)
        assert found is not None
        assert found.instance_identifier.value == "https://test.com"

    @pytest.mark.asyncio
    async def test_find_by_license(self, activation_repository, db_license):
        """Test finding activations by license."""
        activation1 = Activation.create(
            license_id=db_license.id,
            instance_identifier="https://site1.com",
            instance_type=InstanceType.URL,
        )
        activation2 = Activation.create(
            license_id=db_license.id,
            instance_identifier="https://site2.com",
            instance_type=InstanceType.URL,
        )

        await activation_repository.save(activation1)
        await activation_repository.save(activation2)

        activations = await activation_repository.find_by_license(db_license.id)
        assert len(activations) >= 2

    @pytest.mark.asyncio
    async def test_find_by_instance(self, activation_repository, db_license):
        """Test finding activation by instance identifier."""
        activation = Activation.create(
            license_id=db_license.id,
            instance_identifier="https://unique.com",
            instance_type=InstanceType.URL,
        )
        await activation_repository.save(activation)

        found = await activation_repository.find_by_instance(db_license.id, "https://unique.com")
        assert found is not None
        assert found.instance_identifier.value == "https://unique.com"
