"""
Brand and API Key models.
"""
import hashlib
import secrets
import uuid

from django.db import models
from django.utils import timezone


class Brand(models.Model):
    """
    Represents a brand/tenant in the system (e.g., RankMath, WP Rocket).
    Each brand has isolated data access.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Brand display name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-safe identifier")
    prefix = models.CharField(
        max_length=10,
        unique=True,
        help_text="License key prefix (e.g., 'RM' for RankMath)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["prefix"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(prefix__length__gte=2) & models.Q(prefix__length__lte=10),
                name="prefix_length_valid",
            ),
        ]

    def clean(self):
        """Validate brand fields."""
        from django.core.exceptions import ValidationError

        if not self.prefix:
            raise ValidationError("Prefix is required")
        if len(self.prefix) < 2 or len(self.prefix) > 10:
            raise ValidationError(
                "Prefix must be between 2 and 10 characters"
            )
        if not self.prefix.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                "Prefix must contain only alphanumeric characters, "
                "hyphens, or underscores"
            )

    def save(self, *args, **kwargs):
        """Save brand with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def generate_api_key(self, scope="full"):
        """
        Generate a new API key for this brand.

        Args:
            scope: API key scope ('full' or 'read')

        Returns:
            ApiKey instance with _raw_key attribute set
        """
        return ApiKey.objects.create(
            brand=self, scope=scope
        )


class ApiKey(models.Model):
    """
    API keys for brand authentication.
    """

    SCOPE_CHOICES = [
        ("full", "Full Access"),
        ("read", "Read Only"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="api_keys")
    key_prefix = models.CharField(max_length=8, editable=False)
    key_hash = models.CharField(
        max_length=64, editable=False, db_index=True
    )
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="full")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key_hash"]),
            models.Index(fields=["brand", "scope"]),
        ]

    def __str__(self):
        return f"{self.brand.name} - {self.key_prefix}..."

    def clean(self):
        """Validate API key fields."""
        from django.core.exceptions import ValidationError

        if not self.brand_id:
            raise ValidationError("Brand is required")

    def save(self, *args, **kwargs):
        """Generate API key on first save."""
        if not self.key_hash:
            # Generate a secure random key
            raw_key = secrets.token_urlsafe(32)
            self.key_prefix = raw_key[:8]
            self.key_hash = hashlib.sha256(
                raw_key.encode()
            ).hexdigest()
            # Store the raw key temporarily for retrieval
            self._raw_key = raw_key
        self.full_clean()
        super().save(*args, **kwargs)

    def verify_key(self, raw_key: str) -> bool:
        """
        Verify a raw API key against the stored hash.

        Args:
            raw_key: The raw API key to verify

        Returns:
            True if key matches, False otherwise
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return secrets.compare_digest(
            self.key_hash, key_hash
        )

    def is_valid(self) -> bool:
        """
        Check if the API key is still valid.

        Returns:
            True if key is valid, False if expired
        """
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def mark_used(self):
        """Update last_used_at timestamp."""
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])
