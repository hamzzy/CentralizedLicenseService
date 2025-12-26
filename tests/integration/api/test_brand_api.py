"""
Integration tests for Brand API endpoints.
"""

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from brands.infrastructure.models import ApiKey, Brand


@pytest.mark.django_db
@pytest.mark.integration
class TestBrandAPI:
    """Integration tests for Brand API."""

    def test_provision_license_success(self, api_client):
        """Test successful license provisioning via API."""
        # Create brand and API key with unique values
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        brand = Brand.objects.create(
            name=f"TestBrand{unique_id}",
            slug=f"testbrand{unique_id}",
            prefix=f"TB{unique_id[:2]}",
        )
        # Create API key and capture raw key
        import hashlib
        import secrets

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

        url = reverse("brand:provision-license")
        response = api_client.post(
            url,
            {
                "customer_email": "test@example.com",
                "products": [str(product.id)],
                "expiration_date": (timezone.now() + timedelta(days=365)).isoformat(),
                "max_seats": 5,
            },
            HTTP_X_API_KEY=raw_key,
            format="json",
        )

        if response.status_code != 201:
            print(f"DEBUG: Response body: {response.content.decode()}")
        assert response.status_code == 201
        data = response.json()
        assert "license_key" in data
        assert "licenses" in data
        assert len(data["licenses"]) == 1

    def test_provision_license_invalid_api_key(self, api_client):
        """Test provisioning with invalid API key."""
        url = reverse("brand:provision-license")
        response = api_client.post(
            url,
            {
                "customer_email": "test@example.com",
                "products": [str(uuid.uuid4())],
            },
            HTTP_X_API_KEY="invalid-key",
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_renew_license_success(self, api_client, db_license):
        """Test successful license renewal via API."""
        # Get brand and create API key
        import hashlib
        import secrets

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

        new_expiration = timezone.now() + timedelta(days=730)
        url = reverse("brand:renew-license", kwargs={"license_id": db_license.id})
        response = api_client.patch(
            url,
            {"expiration_date": new_expiration.isoformat()},
            HTTP_X_API_KEY=raw_key,
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "renewed successfully" in data["message"].lower()

    def test_suspend_license_success(self, api_client, db_license):
        """Test successful license suspension via API."""
        import hashlib
        import secrets

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
            "brand:suspend-license",
            kwargs={"license_id": db_license.id},
        )
        response = api_client.patch(
            url,
            HTTP_X_API_KEY=raw_key,
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "suspended successfully" in data["message"].lower()

    def test_list_licenses_by_email(self, api_client, db_license):
        """Test listing licenses by customer email."""
        import hashlib
        import secrets

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

        url = reverse("brand:list-licenses")
        response = api_client.get(
            url,
            {"email": "test@example.com"},
            HTTP_X_API_KEY=raw_key,
        )

        assert response.status_code == 200
        data = response.json()
        # Response is a list of licenses, not a dict with "licenses" key
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_resume_license_invalid_state(self, api_client, db_license):
        """Test resuming a license that is not suspended (should fail)."""
        import hashlib
        import secrets

        from licenses.infrastructure.models import License

        license_obj = License.objects.get(id=db_license.id)
        # License is VALID by default in test fixture

        brand = license_obj.license_key.brand
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        ApiKey.objects.create(
            brand=brand,
            key_prefix=raw_key[:8],
            key_hash=key_hash,
        )

        url = reverse("brand:resume-license", kwargs={"license_id": db_license.id})
        response = api_client.patch(
            url,
            HTTP_X_API_KEY=raw_key,
            format="json",
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Can only resume a suspended license" in data["error"]

    def test_renew_license_past_date(self, api_client, db_license):
        """Test renewing a license with a past date (should fail)."""
        import hashlib
        import secrets

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

        past_date = timezone.now() - timedelta(days=1)
        url = reverse("brand:renew-license", kwargs={"license_id": db_license.id})
        response = api_client.patch(
            url,
            {"expiration_date": past_date.isoformat()},
            HTTP_X_API_KEY=raw_key,
            format="json",
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Expiration date cannot be in the past" in data["error"]
