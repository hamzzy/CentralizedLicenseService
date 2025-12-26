"""
License, LicenseKey, Activation, AuditLog, and IdempotencyKey models.
"""
import hashlib
import secrets
import string
import uuid

from django.db import models
from django.utils import timezone


def generate_license_key(brand_prefix: str) -> str:
    """
    Generate a license key in format: PREFIX-XXXX-XXXX-XXXX-XXXX.

    Args:
        brand_prefix: Brand prefix (e.g., 'RM' for RankMath)

    Returns:
        Generated license key string
    """
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
    return f"{brand_prefix}-{'-'.join(parts)}"


class LicenseKey(models.Model):
    """
    A license key that can contain multiple licenses.
    Given to customers to activate products.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey("brands.Brand", on_delete=models.CASCADE, related_name="license_keys")
    key = models.CharField(max_length=100, unique=True, db_index=True)
    key_hash = models.CharField(max_length=64, db_index=True, help_text="Hashed version for secure lookup")
    customer_email = models.EmailField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "license_keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key"]),
            models.Index(fields=["key_hash"]),
            models.Index(fields=["customer_email", "brand"]),
        ]

    def __str__(self):
        return self.key

    def save(self, *args, **kwargs):
        """Generate license key and hash on first save."""
        if not self.key:
            self.key = generate_license_key(self.brand.prefix)
        if not self.key_hash:
            self.key_hash = hashlib.sha256(self.key.encode()).hexdigest()
        super().save(*args, **kwargs)

    def verify_key(self, raw_key: str) -> bool:
        """
        Verify a raw license key against the stored hash.

        Args:
            raw_key: The raw license key to verify

        Returns:
            True if key matches, False otherwise
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return secrets.compare_digest(self.key_hash, key_hash)


class License(models.Model):
    """
    A license grants access to a specific product.
    Multiple licenses can be associated with one license key.
    """

    STATUS_CHOICES = [
        ("valid", "Valid"),
        ("suspended", "Suspended"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license_key = models.ForeignKey(
        LicenseKey, on_delete=models.CASCADE, related_name="licenses"
    )
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="licenses")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="valid")
    seat_limit = models.IntegerField(default=1, help_text="Maximum number of activations")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "licenses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["license_key", "product"]),
            models.Index(fields=["license_key", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.license_key.key} - {self.product.name}"

    @property
    def is_valid(self) -> bool:
        """
        Check if license is currently valid.

        Returns:
            True if license is valid and not expired
        """
        if self.status != "valid":
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    @property
    def seats_used(self) -> int:
        """
        Count active activations.

        Returns:
            Number of active activations
        """
        return self.activations.count()

    @property
    def seats_remaining(self) -> int:
        """
        Calculate remaining seats.

        Returns:
            Number of remaining seats
        """
        return max(0, self.seat_limit - self.seats_used)

    def can_activate(self) -> bool:
        """
        Check if a new activation is allowed.

        Returns:
            True if activation is allowed
        """
        if not self.is_valid:
            return False
        return self.seats_remaining > 0

    def renew(self, new_expiration):
        """
        Renew the license with a new expiration date.

        Args:
            new_expiration: New expiration datetime
        """
        self.expires_at = new_expiration
        if self.status == "expired":
            self.status = "valid"
        self.save()

    def suspend(self):
        """Suspend the license."""
        self.status = "suspended"
        self.save()

    def resume(self):
        """Resume a suspended license."""
        if self.status == "suspended":
            self.status = "valid"
            self.save()

    def cancel(self):
        """Cancel the license."""
        self.status = "cancelled"
        self.save()


class Activation(models.Model):
    """
    Represents a specific instance where a license is activated.
    Consumes a seat from the license.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name="activations")
    instance_identifier = models.CharField(
        max_length=500, help_text="URL, hostname, or machine ID"
    )
    instance_metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional instance information"
    )
    activated_at = models.DateTimeField(auto_now_add=True)
    last_checked_at = models.DateTimeField(auto_now=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "activations"
        unique_together = [["license", "instance_identifier"]]
        ordering = ["-activated_at"]
        indexes = [
            models.Index(fields=["license", "instance_identifier"]),
            models.Index(fields=["license", "is_active"]),
        ]

    def __str__(self):
        return f"{self.license.license_key.key} @ {self.instance_identifier}"

    def deactivate(self):
        """Deactivate this activation, freeing a seat."""
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.save()


class AuditLog(models.Model):
    """
    Immutable audit trail of all license-related changes.
    """

    ACTION_CHOICES = [
        ("license_key_created", "License Key Created"),
        ("license_created", "License Created"),
        ("license_renewed", "License Renewed"),
        ("license_suspended", "License Suspended"),
        ("license_resumed", "License Resumed"),
        ("license_cancelled", "License Cancelled"),
        ("activation_created", "Activation Created"),
        ("activation_deleted", "Activation Deleted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey("brands.Brand", on_delete=models.CASCADE, related_name="audit_logs")
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    changes = models.JSONField(default=dict, help_text="Details of the change")
    actor = models.CharField(max_length=255, help_text="Who performed the action")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["brand", "entity_type", "entity_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity_type} {self.entity_id}"


class IdempotencyKey(models.Model):
    """
    Stores idempotency keys to prevent duplicate operations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, unique=True, db_index=True)
    brand = models.ForeignKey("brands.Brand", on_delete=models.CASCADE)
    response_data = models.JSONField(help_text="Cached response for idempotent replay")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "idempotency_keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key"]),
            models.Index(fields=["brand", "key"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return self.key

    def save(self, *args, **kwargs):
        """Set default expiration if not provided."""
        if not self.expires_at:
            # Default 24 hour expiration
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        """
        Check if idempotency key is expired.

        Returns:
            True if expired, False otherwise
        """
        return timezone.now() > self.expires_at
