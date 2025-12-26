"""
Activation Django ORM model.

This is the infrastructure layer model for activations.
Domain entities are in activations.domain.activation.
"""
import uuid

from django.db import models


class Activation(models.Model):
    """
    Represents a specific instance where a license is activated.
    Consumes a seat from the license.
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    license = models.ForeignKey(
        "licenses.License",
        on_delete=models.CASCADE,
        related_name="activations",
    )
    instance_identifier = models.CharField(
        max_length=500, help_text="URL, hostname, or machine ID"
    )
    instance_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional instance information",
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
            models.Index(
                fields=["license", "is_active", "activated_at"]
            ),
        ]

    def clean(self):
        """Validate activation fields."""
        from django.core.exceptions import ValidationError

        if not self.instance_identifier or len(
            self.instance_identifier.strip()
        ) == 0:
            raise ValidationError("Instance identifier cannot be empty")
        if len(self.instance_identifier) > 500:
            raise ValidationError("Instance identifier too long")

    def save(self, *args, **kwargs):
        """Save activation with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def deactivate(self):
        """Deactivate this activation, freeing a seat."""
        if not self.is_active:
            return  # Already deactivated
        self.is_active = False
        from django.utils import timezone

        self.deactivated_at = timezone.now()
        self.save()

    def __str__(self):
        return (
            f"{self.license.license_key.key} @ "
            f"{self.instance_identifier}"
        )

