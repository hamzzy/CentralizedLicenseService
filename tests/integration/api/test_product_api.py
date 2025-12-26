"""
Integration tests for Product API endpoints.
"""

import uuid

import pytest
from django.urls import reverse

from licenses.infrastructure.models import License, LicenseKey


@pytest.mark.django_db
@pytest.mark.integration
class TestProductAPI:
    """Integration tests for Product API."""

    def test_activate_license_success(self, api_client, db_license, db_product):
        """Test successful license activation via API."""
        # Get license key and product
        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)
        # Get product slug from db_product
        from products.infrastructure.models import Product

        product_obj = Product.objects.get(id=db_product.id)

        url = reverse("product:activate-license")
        response = api_client.post(
            url,
            {
                "product_slug": product_obj.slug,
                "instance_identifier": "https://example.com",
                "instance_type": "url",
            },
            HTTP_X_LICENSE_KEY=license_key_obj.key,
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert "activation_id" in data
        assert "activation_id" in data
        assert "activation_id" in data

    def test_activate_license_duplicate(self, api_client, db_license, db_product):
        """Test duplicate license activation returns 409/400 instead of 500."""
        # Get license key and product
        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)
        # Get product slug from db_product
        from products.infrastructure.models import Product

        product_obj = Product.objects.get(id=db_product.id)

        url = reverse("product:activate-license")
        payload = {
            "product_slug": product_obj.slug,
            "instance_identifier": "https://example.com",
            "instance_type": "url",
        }

        # First activation
        api_client.post(
            url,
            payload,
            HTTP_X_LICENSE_KEY=license_key_obj.key,
            format="json",
        )

        # Second activation (should fail with conflict)
        response = api_client.post(
            url,
            payload,
            HTTP_X_LICENSE_KEY=license_key_obj.key,
            format="json",
        )

        # Currently expecting 500, but goal is 409
        if response.status_code == 500:
            pytest.fail("Duplicate activation caused 500 Internal Server Error")

        # After fix, we expect 409 Conflict
        assert response.status_code in [409, 400]

    def test_activate_license_invalid_key(self, api_client):
        """Test activation with invalid license key."""
        url = reverse("product:activate-license")
        response = api_client.post(
            url,
            {
                "product_slug": "rankmath-pro",
                "instance_identifier": "https://example.com",
                "instance_type": "url",
            },
            HTTP_X_LICENSE_KEY="INVALID-KEY-1234",
            format="json",
        )

        assert response.status_code == 401

    def test_check_license_status_success(self, api_client, db_license):
        """Test checking license status via API."""
        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)

        url = reverse("product:get-license-status")
        response = api_client.get(
            url,
            {
                "instance_identifier": "https://example.com",
            },
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "licenses" in data

    def test_deactivate_seat_success(self, api_client, db_license):
        """Test successful seat deactivation via API."""
        from activations.infrastructure.models import Activation
        from core.domain.value_objects import InstanceType

        # Create activation first
        license_obj = License.objects.get(id=db_license.id)
        activation = Activation.objects.create(
            license=license_obj,
            instance_identifier="https://example.com",
            instance_metadata={"instance_type": InstanceType.URL.value},
        )

        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)

        url = reverse("product:deactivate-seat", kwargs={"activation_id": activation.id})
        response = api_client.delete(
            url,
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deactivated"

    def test_deactivate_seat_not_found(self, api_client, db_license):
        """Test deactivating non-existent seat."""
        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)

        # Use a non-existent activation ID
        import uuid

        fake_activation_id = uuid.uuid4()
        url = reverse("product:deactivate-seat", kwargs={"activation_id": fake_activation_id})
        response = api_client.delete(
            url,
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )

        assert response.status_code == 404

    def test_seat_count_logic(self, api_client, db_license, db_product):
        """Test that seat counts update correctly after activation/deactivation."""
        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)
        from products.infrastructure.models import Product

        product_obj = Product.objects.get(id=db_product.id)

        # 1. Check initial status (should be 0)
        url_status = reverse("product:get-license-status")
        response = api_client.get(
            url_status,
            {"instance_identifier": "https://example.com"},
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )
        data = response.json()
        assert data["total_seats_used"] == 0
        assert data["licenses"][0]["seats_used"] == 0

        # 2. Activate
        url_activate = reverse("product:activate-license")
        response = api_client.post(
            url_activate,
            {
                "product_slug": product_obj.slug,
                "instance_identifier": "https://example.com",
                "instance_type": "url",
            },
            HTTP_X_LICENSE_KEY=license_key_obj.key,
            format="json",
        )
        assert response.status_code == 201
        activation_id = response.json()["activation_id"]

        # 3. Check status (should be 1)
        response = api_client.get(
            url_status,
            {"instance_identifier": "https://example.com"},
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )
        data = response.json()
        assert data["total_seats_used"] == 1
        assert data["licenses"][0]["seats_used"] == 1

        # 4. Deactivate
        url_deactivate = reverse("product:deactivate-seat", kwargs={"activation_id": activation_id})
        response = api_client.delete(
            url_deactivate,
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )
        assert response.status_code == 200

        # 5. Check status (should be 0)
        response = api_client.get(
            url_status,
            {"instance_identifier": "https://example.com"},
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )
        data = response.json()
        assert data["total_seats_used"] == 0
        assert data["licenses"][0]["seats_used"] == 0

        # 6. Activate again (Check for the user reported issue)
        response = api_client.post(
            url_activate,
            {
                "product_slug": product_obj.slug,
                "instance_identifier": "https://example.com",
                "instance_type": "url",
            },
            HTTP_X_LICENSE_KEY=license_key_obj.key,
            format="json",
        )
        assert response.status_code == 201

        # 7. Check status (should be 1)
        response = api_client.get(
            url_status,
            {"instance_identifier": "https://example.com"},
            HTTP_X_LICENSE_KEY=license_key_obj.key,
        )
        data = response.json()
        # This is where we expect the failure based on user report
        if data["total_seats_used"] == 0:
            pytest.fail("Seat count did not increment after re-activation")

        assert data["total_seats_used"] == 1
        assert data["licenses"][0]["seats_used"] == 1
