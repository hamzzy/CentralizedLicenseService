"""
Pytest configuration and shared fixtures.
"""

import uuid
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from activations.domain.activation import Activation
from activations.infrastructure.repositories.django_activation_repository import (
    DjangoActivationRepository,
)
from brands.domain.brand import Brand
from brands.domain.product import Product
from brands.infrastructure.repositories.django_brand_repository import DjangoBrandRepository
from brands.infrastructure.repositories.django_product_repository import DjangoProductRepository
from core.domain.value_objects import BrandSlug, InstanceType, ProductSlug
from licenses.domain.license import License
from licenses.domain.license_key import LicenseKey
from licenses.infrastructure.repositories.django_license_key_repository import (
    DjangoLicenseKeyRepository,
)
from licenses.infrastructure.repositories.django_license_repository import DjangoLicenseRepository


@pytest.fixture
def brand_repository():
    """Fixture for BrandRepository."""
    return DjangoBrandRepository()


@pytest.fixture
def product_repository():
    """Fixture for ProductRepository."""
    return DjangoProductRepository()


@pytest.fixture
def license_key_repository():
    """Fixture for LicenseKeyRepository."""
    return DjangoLicenseKeyRepository()


@pytest.fixture
def license_repository():
    """Fixture for LicenseRepository."""
    return DjangoLicenseRepository()


@pytest.fixture
def activation_repository():
    """Fixture for ActivationRepository."""
    return DjangoActivationRepository()


@pytest.fixture
def sample_brand():
    """Fixture for a sample Brand entity."""
    import uuid

    # Use unique values to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    return Brand.create(
        name=f"TestBrand{unique_id}",
        slug=f"testbrand{unique_id}",
        prefix=f"TB{unique_id[:2]}",
    )


@pytest.fixture
def sample_product(sample_brand):
    """Fixture for a sample Product entity."""
    return Product.create(
        brand_id=sample_brand.id,
        name="RankMath Pro",
        slug="rankmath-pro",
    )


@pytest.fixture
def sample_license_key(sample_brand):
    """Fixture for a sample LicenseKey entity."""
    return LicenseKey.create(
        brand_id=sample_brand.id,
        brand_prefix=sample_brand.prefix,
        customer_email="test@example.com",
    )


@pytest.fixture
def sample_license(sample_license_key, sample_product):
    """Fixture for a sample License entity."""
    expires_at = timezone.now() + timedelta(days=365)
    return License.create(
        license_key_id=sample_license_key.id,
        product_id=sample_product.id,
        seat_limit=5,
        expires_at=expires_at,
    )


@pytest.fixture
def sample_activation(sample_license):
    """Fixture for a sample Activation entity."""
    return Activation.create(
        license_id=sample_license.id,
        instance_identifier="https://example.com",
        instance_type=InstanceType.URL,
    )


@pytest.fixture
def db_brand(db, brand_repository):
    """Fixture for a Brand saved in database."""
    import asyncio
    import uuid

    async def save_brand():
        # Create unique brand for each test to avoid conflicts
        # Use full UUID to ensure uniqueness
        unique_id = str(uuid.uuid4()).replace("-", "")[:8]
        brand = Brand.create(
            name=f"TestBrand{unique_id}",
            slug=f"testbrand{unique_id}",
            prefix=f"TB{unique_id[:6]}",  # Use 6 chars for prefix to reduce collisions
        )
        return await brand_repository.save(brand)

    return asyncio.run(save_brand())


@pytest.fixture
def db_product(db, db_brand, sample_product, product_repository):
    """Fixture for a Product saved in database."""
    import asyncio

    async def save_product():
        product = Product.create(
            brand_id=db_brand.id,
            name=sample_product.name,
            slug=sample_product.slug.value,
        )
        return await product_repository.save(product)

    return asyncio.run(save_product())


@pytest.fixture
def db_license_key(db, db_brand, license_key_repository):
    """Fixture for a LicenseKey saved in database."""
    import asyncio

    async def save_key():
        key = LicenseKey.create(
            brand_id=db_brand.id,
            brand_prefix=db_brand.prefix,
            customer_email="test@example.com",
        )
        return await license_key_repository.save(key)

    return asyncio.run(save_key())


@pytest.fixture
def db_license(db, db_license_key, db_product, license_repository):
    """Fixture for a License saved in database."""
    import asyncio

    async def save_license():
        expires_at = timezone.now() + timedelta(days=365)
        license = License.create(
            license_key_id=db_license_key.id,
            product_id=db_product.id,
            seat_limit=5,
            expires_at=expires_at,
        )
        return await license_repository.save(license)

    return asyncio.run(save_license())


@pytest.fixture
def api_client():
    """Fixture for DRF API client."""
    from rest_framework.test import APIClient

    return APIClient()
