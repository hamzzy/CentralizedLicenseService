"""
Unit tests for ProvisionLicenseHandler.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from brands.domain.product import Product
from licenses.application.commands.provision_license import (
    ProvisionLicenseCommand,
)
from licenses.application.handlers.provision_license_handler import (
    ProvisionLicenseHandler,
)
from core.domain.exceptions import BrandNotFoundError


@pytest.mark.asyncio
class TestProvisionLicenseHandler:
    """Tests for ProvisionLicenseHandler."""

    async def test_provision_license_success(
        self,
        brand_repository,
        product_repository,
        license_key_repository,
        license_repository,
        db_brand,
        db_product,
    ):
        """Test successful license provisioning."""
        handler = ProvisionLicenseHandler(
            brand_repository=brand_repository,
            product_repository=product_repository,
            license_key_repository=license_key_repository,
            license_repository=license_repository,
        )

        command = ProvisionLicenseCommand(
            brand_id=db_brand.id,
            customer_email="customer@example.com",
            products=[db_product.id],
            expiration_date=datetime.utcnow() + timedelta(days=365),
            max_seats=3,
        )

        result = await handler.handle(command)

        assert result.license_key is not None
        assert result.license_key.customer_email == "customer@example.com"
        assert len(result.licenses) == 1
        assert result.licenses[0].seat_limit == 3

    async def test_provision_license_brand_not_found(
        self,
        brand_repository,
        product_repository,
        license_key_repository,
        license_repository,
    ):
        """Test provisioning with non-existent brand."""
        handler = ProvisionLicenseHandler(
            brand_repository=brand_repository,
            product_repository=product_repository,
            license_key_repository=license_key_repository,
            license_repository=license_repository,
        )

        command = ProvisionLicenseCommand(
            brand_id=uuid.uuid4(),
            customer_email="customer@example.com",
            products=[uuid.uuid4()],
        )

        with pytest.raises(BrandNotFoundError):
            await handler.handle(command)

    async def test_provision_multiple_licenses(
        self,
        brand_repository,
        product_repository,
        license_key_repository,
        license_repository,
        db_brand,
        db_product,
    ):
        """Test provisioning multiple licenses for one key."""
        # Create second product
        product2 = Product.create(
            brand_id=db_brand.id,
            name="Content AI",
            slug="content-ai",
        )
        saved_product2 = await product_repository.save(product2)

        handler = ProvisionLicenseHandler(
            brand_repository=brand_repository,
            product_repository=product_repository,
            license_key_repository=license_key_repository,
            license_repository=license_repository,
        )

        command = ProvisionLicenseCommand(
            brand_id=db_brand.id,
            customer_email="customer@example.com",
            products=[db_product.id, saved_product2.id],
            expiration_date=datetime.utcnow() + timedelta(days=365),
        )

        result = await handler.handle(command)

        assert result.license_key is not None
        assert len(result.licenses) == 2
