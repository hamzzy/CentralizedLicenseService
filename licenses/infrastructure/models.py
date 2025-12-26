"""
Django ORM models for License module.

This is a placeholder that will be implemented in Phase 3.
"""
from django.db import models


class LicenseKey(models.Model):
    """LicenseKey model - placeholder for Phase 3."""

    key_hash = models.CharField(max_length=255, unique=True, db_index=True)
    brand = models.ForeignKey("brands.Brand", on_delete=models.CASCADE, related_name="license_keys")
    customer_email = models.EmailField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "license_keys"
        indexes = [
            models.Index(fields=["key_hash"]),
            models.Index(fields=["brand", "customer_email"]),
        ]

    def __str__(self):
        return f"LicenseKey for {self.customer_email}"


class License(models.Model):
    """License model - placeholder for Phase 3."""

    class Status(models.TextChoices):
        VALID = "valid", "Valid"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    license_key = models.ForeignKey(
        LicenseKey, on_delete=models.CASCADE, related_name="licenses"
    )
    product = models.ForeignKey("brands.Product", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALID)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_seats = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "licenses"
        indexes = [
            models.Index(fields=["license_key", "status"]),
            models.Index(fields=["license_key", "product"]),
        ]

    def __str__(self):
        return f"License {self.product.name} - {self.status}"

