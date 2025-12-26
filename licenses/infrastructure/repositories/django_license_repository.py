"""
Django implementation of LicenseRepository port.

This adapter converts between domain entities and Django ORM models.
"""
import uuid
from typing import List, Optional

from asgiref.sync import sync_to_async

from core.domain.value_objects import LicenseStatus
from licenses.domain.license import License
from licenses.infrastructure.models import License as LicenseModel
from licenses.ports.license_repository import LicenseRepository


class DjangoLicenseRepository(LicenseRepository):
    """
    Django ORM implementation of LicenseRepository.

    This adapter:
    1. Converts Django models to domain entities
    2. Converts domain entities to Django models
    3. Implements repository interface
    """

    def _to_domain(self, model: LicenseModel) -> License:
        """
        Convert Django model to domain entity.

        Args:
            model: Django License model

        Returns:
            License domain entity
        """
        # Map Django status string to LicenseStatus enum
        status_map = {
            "valid": LicenseStatus.VALID,
            "suspended": LicenseStatus.SUSPENDED,
            "cancelled": LicenseStatus.CANCELLED,
            "expired": LicenseStatus.EXPIRED,
        }
        status = status_map.get(model.status, LicenseStatus.VALID)

        return License(
            id=model.id,
            license_key_id=model.license_key_id,
            product_id=model.product_id,
            status=status,
            seat_limit=model.seat_limit,
            expires_at=model.expires_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, license: License) -> LicenseModel:
        """
        Convert domain entity to Django model.

        Args:
            license: License domain entity

        Returns:
            Django License model
        """
        model, created = LicenseModel.objects.get_or_create(
            id=license.id,
            defaults={
                "license_key_id": license.license_key_id,
                "product_id": license.product_id,
                "status": license.status.value,
                "seat_limit": license.seat_limit,
                "expires_at": license.expires_at,
                "created_at": license.created_at,
                "updated_at": license.updated_at,
            },
        )
        # Update if exists
        if not created:
            model.status = license.status.value
            model.seat_limit = license.seat_limit
            model.expires_at = license.expires_at
            model.updated_at = license.updated_at
        return model

    @sync_to_async
    def save(self, license: License) -> License:
        """
        Save a license entity.

        Args:
            license: License entity to save

        Returns:
            Saved license entity
        """
        model = self._to_model(license)
        model.save()
        return self._to_domain(model)

    @sync_to_async
    def find_by_id(self, license_id: uuid.UUID) -> Optional[License]:
        """
        Find a license by ID.

        Args:
            license_id: License UUID

        Returns:
            License entity or None if not found
        """
        try:
            model = LicenseModel.objects.get(id=license_id)
            return self._to_domain(model)
        except LicenseModel.DoesNotExist:
            return None

    @sync_to_async
    def find_by_license_key(
        self, license_key_id: uuid.UUID
    ) -> List[License]:
        """
        Find all licenses for a license key.

        Args:
            license_key_id: License key UUID

        Returns:
            List of License entities
        """
        models = LicenseModel.objects.filter(
            license_key_id=license_key_id
        )
        return [self._to_domain(model) for model in models]

    @sync_to_async
    def find_by_license_key_and_product(
        self, license_key_id: uuid.UUID, product_id: uuid.UUID
    ) -> Optional[License]:
        """
        Find a license by license key and product.

        Args:
            license_key_id: License key UUID
            product_id: Product UUID

        Returns:
            License entity or None if not found
        """
        try:
            model = LicenseModel.objects.get(
                license_key_id=license_key_id, product_id=product_id
            )
            return self._to_domain(model)
        except LicenseModel.DoesNotExist:
            return None

    @sync_to_async
    def exists(self, license_id: uuid.UUID) -> bool:
        """
        Check if a license exists.

        Args:
            license_id: License UUID

        Returns:
            True if license exists, False otherwise
        """
        return LicenseModel.objects.filter(id=license_id).exists()

