"""
Django ORM models for Brand module.

This is a placeholder that will be implemented in Phase 2.
"""
from django.db import models


class Brand(models.Model):
    """Brand model - placeholder for Phase 2."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    api_key_hash = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brands"
        indexes = [
            models.Index(fields=["api_key_hash"]),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model - placeholder for Phase 2."""

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"
        unique_together = [["brand", "slug"]]
        indexes = [
            models.Index(fields=["brand", "slug"]),
        ]

    def __str__(self):
        return f"{self.brand.name} - {self.name}"

