"""
Django implementation of LicenseKeyRepository port.

This adapter converts between domain entities and Django ORM models.
"""
import hashlib
import uuid
from typing import List, Optional

from asgiref.sync import sync_to_async

from core.domain.value_objects import Email
from licenses.domain.license_key import LicenseKey
from licenses.infrastructure.models import (
    LicenseKey as LicenseKeyModel,
)
from licenses.ports.license_key_repository import LicenseKeyRepository


class DjangoLicenseKeyRepository(LicenseKeyRepository):
    """
    Django ORM implementation of LicenseKeyRepository.

    This adapter:
    1. Converts Django models to domain entities
    2. Converts domain entities to Django models
    3. Implements repository interface
    """

    def _to_domain(self, model: LicenseKeyModel) -> LicenseKey:
        """
        Convert Django model to domain entity.

        Args:
            model: Django LicenseKey model

        Returns:
            LicenseKey domain entity
        """
        return LicenseKey(
            id=model.id,
            brand_id=model.brand_id,
            key=model.key,
            key_hash=model.key_hash,
            customer_email=Email(model.customer_email),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, license_key: LicenseKey) -> LicenseKeyModel:
        """
        Convert domain entity to Django model.

        Args:
            license_key: LicenseKey domain entity

        Returns:
            Django LicenseKey model
        """
        model, created = LicenseKeyModel.objects.get_or_create(
            id=license_key.id,
            defaults={
                "brand_id": license_key.brand_id,
                "key": license_key.key,
                "key_hash": license_key.key_hash,
                "customer_email": str(license_key.customer_email),
                "created_at": license_key.created_at,
                "updated_at": license_key.updated_at,
            },
        )
        # Update if exists
        if not created:
            model.key = license_key.key
            model.key_hash = license_key.key_hash
            model.customer_email = str(license_key.customer_email)
            model.updated_at = license_key.updated_at
        return model

    @sync_to_async
    def save(self, license_key: LicenseKey) -> LicenseKey:
        """
        Save a license key entity.

        Args:
            license_key: LicenseKey entity to save

        Returns:
            Saved license key entity
        """
        model = self._to_model(license_key)
        model.save()
        return self._to_domain(model)

    @sync_to_async
    def find_by_id(
        self, license_key_id: uuid.UUID
    ) -> Optional[LicenseKey]:
        """
        Find a license key by ID.

        Args:
            license_key_id: License key UUID

        Returns:
            LicenseKey entity or None if not found
        """
        try:
            model = LicenseKeyModel.objects.get(id=license_key_id)
            return self._to_domain(model)
        except LicenseKeyModel.DoesNotExist:
            return None

    @sync_to_async
    def find_by_key(self, key: str) -> Optional[LicenseKey]:
        """
        Find a license key by key string.

        Args:
            key: License key string

        Returns:
            LicenseKey entity or None if not found
        """
        try:
            model = LicenseKeyModel.objects.get(key=key)
            return self._to_domain(model)
        except LicenseKeyModel.DoesNotExist:
            return None

    @sync_to_async
    def find_by_key_hash(
        self, key_hash: str
    ) -> Optional[LicenseKey]:
        """
        Find a license key by key hash.

        Args:
            key_hash: License key hash

        Returns:
            LicenseKey entity or None if not found
        """
        try:
            model = LicenseKeyModel.objects.get(key_hash=key_hash)
            return self._to_domain(model)
        except LicenseKeyModel.DoesNotExist:
            return None

    @sync_to_async
    def find_by_customer_email(
        self, brand_id: uuid.UUID, email: str
    ) -> List[LicenseKey]:
        """
        Find license keys by customer email and brand.

        Args:
            brand_id: Brand UUID
            email: Customer email

        Returns:
            List of LicenseKey entities
        """
        models = LicenseKeyModel.objects.filter(
            brand_id=brand_id, customer_email=email
        )
        return [self._to_domain(model) for model in models]

    @sync_to_async
    def exists(self, license_key_id: uuid.UUID) -> bool:
        """
        Check if a license key exists.

        Args:
            license_key_id: License key UUID

        Returns:
            True if license key exists, False otherwise
        """
        return LicenseKeyModel.objects.filter(id=license_key_id).exists()

