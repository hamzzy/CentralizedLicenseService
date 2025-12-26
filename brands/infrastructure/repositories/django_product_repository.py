"""
Django implementation of ProductRepository port.

This adapter converts between domain entities and Django ORM models.
"""

import uuid
from typing import List, Optional

from asgiref.sync import sync_to_async

from brands.domain.product import Product
from brands.ports.product_repository import ProductRepository
from products.infrastructure.models import Product as ProductModel


class DjangoProductRepository(ProductRepository):
    """
    Django ORM implementation of ProductRepository.

    This adapter:
    1. Converts Django models to domain entities
    2. Converts domain entities to Django models
    3. Implements repository interface
    """

    def _to_domain(self, model: ProductModel) -> Product:
        """
        Convert Django model to domain entity.

        Args:
            model: Django Product model

        Returns:
            Product domain entity
        """
        from core.domain.value_objects import ProductSlug

        return Product(
            id=model.id,
            brand_id=model.brand_id,
            name=model.name,
            slug=ProductSlug(model.slug),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, product: Product) -> ProductModel:
        """
        Convert domain entity to Django model.

        Args:
            product: Product domain entity

        Returns:
            Django Product model
        """
        model, created = ProductModel.objects.get_or_create(
            id=product.id,
            defaults={
                "brand_id": product.brand_id,
                "name": product.name,
                "slug": str(product.slug),
                "created_at": product.created_at,
                "updated_at": product.updated_at,
            },
        )
        # Update if exists
        if not created:
            model.name = product.name
            model.slug = str(product.slug)
            model.updated_at = product.updated_at
        return model

    @sync_to_async
    def save(self, product: Product) -> Product:
        """
        Save a product entity.

        Args:
            product: Product entity to save

        Returns:
            Saved product entity
        """
        model = self._to_model(product)
        model.save()
        return self._to_domain(model)

    @sync_to_async
    def find_by_id(self, product_id: uuid.UUID) -> Optional[Product]:
        """
        Find a product by ID.

        Args:
            product_id: Product UUID

        Returns:
            Product entity or None if not found
        """
        try:
            model = ProductModel.objects.get(id=product_id)
            return self._to_domain(model)
        except ProductModel.DoesNotExist:
            return None

    @sync_to_async
    def find_by_slug(self, brand_id: uuid.UUID, slug: str) -> Optional[Product]:
        """
        Find a product by brand and slug.

        Args:
            brand_id: Brand UUID
            slug: Product slug

        Returns:
            Product entity or None if not found
        """
        try:
            model = ProductModel.objects.get(brand_id=brand_id, slug=slug)
            return self._to_domain(model)
        except ProductModel.DoesNotExist:
            return None

    @sync_to_async
    def list_by_brand(self, brand_id: uuid.UUID) -> List[Product]:
        """
        List all products for a brand.

        Args:
            brand_id: Brand UUID

        Returns:
            List of Product entities
        """
        models = ProductModel.objects.filter(brand_id=brand_id)
        return [self._to_domain(model) for model in models]

    @sync_to_async
    def exists(self, product_id: uuid.UUID) -> bool:
        """
        Check if a product exists.

        Args:
            product_id: Product UUID

        Returns:
            True if product exists, False otherwise
        """
        return ProductModel.objects.filter(id=product_id).exists()
