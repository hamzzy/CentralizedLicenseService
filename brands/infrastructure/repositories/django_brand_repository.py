"""
Django implementation of BrandRepository port.

This adapter converts between domain entities and Django ORM models.
"""
import uuid
from typing import List, Optional

from asgiref.sync import sync_to_async

from brands.domain.brand import Brand
from brands.infrastructure.models import Brand as BrandModel
from brands.ports.brand_repository import BrandRepository


class DjangoBrandRepository(BrandRepository):
    """
    Django ORM implementation of BrandRepository.

    This adapter:
    1. Converts Django models to domain entities
    2. Converts domain entities to Django models
    3. Implements repository interface
    """

    def _to_domain(self, model: BrandModel) -> Brand:
        """
        Convert Django model to domain entity.

        Args:
            model: Django Brand model

        Returns:
            Brand domain entity
        """
        from core.domain.value_objects import BrandSlug

        return Brand(
            id=model.id,
            name=model.name,
            slug=BrandSlug(model.slug),
            prefix=model.prefix,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, brand: Brand) -> BrandModel:
        """
        Convert domain entity to Django model.

        Args:
            brand: Brand domain entity

        Returns:
            Django Brand model
        """
        model, _ = BrandModel.objects.get_or_create(
            id=brand.id,
            defaults={
                "name": brand.name,
                "slug": str(brand.slug),
                "prefix": brand.prefix,
                "created_at": brand.created_at,
                "updated_at": brand.updated_at,
            },
        )
        # Update if exists
        if not _:
            model.name = brand.name
            model.slug = str(brand.slug)
            model.prefix = brand.prefix
            model.updated_at = brand.updated_at
        return model

    @sync_to_async
    def save(self, brand: Brand) -> Brand:
        """
        Save a brand entity.

        Args:
            brand: Brand entity to save

        Returns:
            Saved brand entity
        """
        model = self._to_model(brand)
        model.save()
        return self._to_domain(model)

    @sync_to_async
    def find_by_id(self, brand_id: uuid.UUID) -> Optional[Brand]:
        """
        Find a brand by ID.

        Args:
            brand_id: Brand UUID

        Returns:
            Brand entity or None if not found
        """
        try:
            model = BrandModel.objects.get(id=brand_id)
            return self._to_domain(model)
        except BrandModel.DoesNotExist:
            return None

    @sync_to_async
    def find_by_slug(self, slug: str) -> Optional[Brand]:
        """
        Find a brand by slug.

        Args:
            slug: Brand slug

        Returns:
            Brand entity or None if not found
        """
        try:
            model = BrandModel.objects.get(slug=slug)
            return self._to_domain(model)
        except BrandModel.DoesNotExist:
            return None

    @sync_to_async
    def find_by_prefix(self, prefix: str) -> Optional[Brand]:
        """
        Find a brand by prefix.

        Args:
            prefix: Brand prefix

        Returns:
            Brand entity or None if not found
        """
        try:
            model = BrandModel.objects.get(prefix=prefix.upper())
            return self._to_domain(model)
        except BrandModel.DoesNotExist:
            return None

    @sync_to_async
    def exists(self, brand_id: uuid.UUID) -> bool:
        """
        Check if a brand exists.

        Args:
            brand_id: Brand UUID

        Returns:
            True if brand exists, False otherwise
        """
        return BrandModel.objects.filter(id=brand_id).exists()

    @sync_to_async
    def list_all(self) -> List[Brand]:
        """
        List all brands.

        Returns:
            List of Brand entities
        """
        models = BrandModel.objects.all()
        return [self._to_domain(model) for model in models]

