"""
Product model.
"""
import uuid

from django.db import models


class Product(models.Model):
    """
    Represents a product that can be licensed (e.g., RankMath Pro, Content AI).
    Products belong to a brand.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey("brands.Brand", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255, help_text="Product display name")
    slug = models.SlugField(max_length=100, help_text="URL-safe identifier")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        unique_together = [["brand", "slug"]]
        ordering = ["brand", "name"]
        indexes = [
            models.Index(fields=["brand", "slug"]),
        ]

    def clean(self):
        """Validate product fields."""
        from django.core.exceptions import ValidationError

        if not self.brand_id:
            raise ValidationError("Brand is required")
        if not self.slug:
            raise ValidationError("Slug is required")
        if not self.name:
            raise ValidationError("Name is required")

    def save(self, *args, **kwargs):
        """Save product with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand.name} - {self.name}"

