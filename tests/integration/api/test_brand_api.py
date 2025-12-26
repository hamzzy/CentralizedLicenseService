"""
Integration tests for Brand API endpoints.
"""
import uuid
from datetime import datetime, timedelta

import pytest
from django.urls import reverse

from brands.infrastructure.models import Brand, ApiKey


@pytest.mark.django_db
@pytest.mark.integration
class TestBrandAPI:
    """Integration tests for Brand API."""

    def test_provision_license_success(self, api_client):
        """Test successful license provisioning via API."""
        # Create brand and API key
        brand = Brand.objects.create(
            name="RankMath",
            slug="rankmath",
            prefix="RM",
        )
        # Create API key and capture raw key
        import secrets
        import hashlib

        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = ApiKey.objects.create(
            brand=brand,
            key_prefix=raw_key[:8],
            key_hash=key_hash,
        )

        # Create product
        from products.infrastructure.models import Product

        product = Product.objects.create(
            brand=brand,
            name="RankMath Pro",
            slug="rankmath-pro",
        )

        url = reverse("api:v1:brand:provision-license")
        response = api_client.post(
            url,
            {
                "customer_email": "test@example.com",
                "products": [str(product.id)],
                "expiration_date": (
                    datetime.utcnow() + timedelta(days=365)
                ).isoformat(),
                "max_seats": 5,
            },
            HTTP_X_API_KEY=raw_key,
        )

        assert response.status_code == 201
        data = response.json()
        assert "license_key" in data
        assert "licenses" in data
        assert len(data["licenses"]) == 1

    def test_provision_license_invalid_api_key(self, api_client):
        """Test provisioning with invalid API key."""
        url = reverse("api:v1:brand:provision-license")
        response = api_client.post(
            url,
            {
                "customer_email": "test@example.com",
                "products": [str(uuid.uuid4())],
            },
            HTTP_X_API_KEY="invalid-key",
        )

        assert response.status_code == 401

    def test_renew_license_success(self, api_client, db_license):
        """Test successful license renewal via API."""
        # Get brand and create API key
        import secrets
        import hashlib

        from licenses.infrastructure.models import License

        license_obj = License.objects.get(id=db_license.id)
        brand = license_obj.license_key.brand
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        ApiKey.objects.create(
            brand=brand,
            key_prefix=raw_key[:8],
            key_hash=key_hash,
        )

        new_expiration = datetime.utcnow() + timedelta(days=730)
        url = reverse(
            "api:v1:brand:renew-license", kwargs={"license_id": db_license.id}
        )
        response = api_client.post(
            url,
            {"expiration_date": new_expiration.isoformat()},
            HTTP_X_API_KEY=raw_key,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "valid"

    def test_suspend_license_success(self, api_client, db_license):
        """Test successful license suspension via API."""
        import secrets
        import hashlib

        from licenses.infrastructure.models import License

        license_obj = License.objects.get(id=db_license.id)
        brand = license_obj.license_key.brand
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        ApiKey.objects.create(
            brand=brand,
            key_prefix=raw_key[:8],
            key_hash=key_hash,
        )

        url = reverse(
            "api:v1:brand:suspend-license",
            kwargs={"license_id": db_license.id},
        )
        response = api_client.post(url, HTTP_X_API_KEY=raw_key)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"

    def test_list_licenses_by_email(self, api_client, db_license):
        """Test listing licenses by customer email."""
        import secrets
        import hashlib

        from licenses.infrastructure.models import License

        license_obj = License.objects.get(id=db_license.id)
        brand = license_obj.license_key.brand
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        ApiKey.objects.create(
            brand=brand,
            key_prefix=raw_key[:8],
            key_hash=key_hash,
        )

        url = reverse("api:v1:brand:list-licenses")
        response = api_client.get(
            url,
            {"email": "test@example.com"},
            HTTP_X_API_KEY=raw_key,
        )

        assert response.status_code == 200
        data = response.json()
        assert "licenses" in data
        assert len(data["licenses"]) >= 1

