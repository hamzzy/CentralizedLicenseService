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

    def test_activate_license_success(self, api_client, db_license):
        """Test successful license activation via API."""
        # Get license key
        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)

        url = reverse("product:activate-license")
        response = api_client.post(
            url,
            {
                "license_key": license_key_obj.key,
                "instance_identifier": "https://example.com",
                "instance_type": "url",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "activation_id" in data
        assert data["status"] == "active"

    def test_activate_license_invalid_key(self, api_client):
        """Test activation with invalid license key."""
        url = reverse("product:activate-license")
        response = api_client.post(
            url,
            {
                "license_key": "INVALID-KEY-1234",
                "instance_identifier": "https://example.com",
                "instance_type": "url",
            },
        )

        assert response.status_code == 404

    def test_check_license_status_success(self, api_client, db_license):
        """Test checking license status via API."""
        license_obj = License.objects.get(id=db_license.id)
        license_key_obj = LicenseKey.objects.get(id=license_obj.license_key_id)

        url = reverse("product:get-license-status")
        response = api_client.get(
            url,
            {
                "license_key": license_key_obj.key,
                "instance_identifier": "https://example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "license" in data

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
