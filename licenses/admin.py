"""
Django admin configuration for licenses app.
"""
from django.contrib import admin
from django.utils.html import format_html

from licenses.infrastructure.models import (
    AuditLog,
    IdempotencyKey,
    License,
    LicenseKey,
)


@admin.register(LicenseKey)
class LicenseKeyAdmin(admin.ModelAdmin):
    """Admin interface for LicenseKey model."""

    list_display = [
        "key",
        "brand",
        "customer_email",
        "license_count",
        "created_at",
    ]
    list_filter = ["brand", "created_at", "updated_at"]
    search_fields = ["key", "customer_email", "brand__name"]
    readonly_fields = ["id", "key", "created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "brand", "key", "customer_email"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def license_count(self, obj):
        """Display number of licenses for this key."""
        return obj.licenses.count()

    license_count.short_description = "Licenses"

    def get_queryset(self, request):
        """Optimize queryset."""
        return (
            super()
            .get_queryset(request)
            .select_related("brand")
            .prefetch_related("licenses")
        )


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    """Admin interface for License model."""

    list_display = [
        "license_key",
        "product",
        "status_display",
        "seat_limit",
        "seats_used",
        "seats_remaining",
        "expires_at",
        "created_at",
    ]
    list_filter = ["status", "expires_at", "created_at", "product__brand"]
    search_fields = [
        "license_key__key",
        "license_key__customer_email",
        "product__name",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "seats_used",
        "seats_remaining",
    ]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "license_key", "product", "status"),
            },
        ),
        (
            "Seat Configuration",
            {
                "fields": (
                    "seat_limit",
                    "seats_used",
                    "seats_remaining",
                ),
            },
        ),
        (
            "Expiration",
            {
                "fields": ("expires_at",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            "valid": "green",
            "suspended": "orange",
            "cancelled": "red",
            "expired": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper(),
        )

    status_display.short_description = "Status"

    def seats_used(self, obj):
        """Display number of active activations."""
        return obj.activations.filter(is_active=True).count()

    seats_used.short_description = "Seats Used"

    def seats_remaining(self, obj):
        """Display remaining seats."""
        used = self.seats_used(obj)
        remaining = max(0, obj.seat_limit - used)
        if remaining == 0:
            return format_html(
                '<span style="color: red;">{}</span>',
                remaining,
            )
        return remaining

    seats_remaining.short_description = "Seats Remaining"

    def get_queryset(self, request):
        """Optimize queryset."""
        return (
            super()
            .get_queryset(request)
            .select_related("license_key__brand", "product")
            .prefetch_related("activations")
        )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""

    list_display = [
        "action",
        "brand",
        "entity_type",
        "entity_id",
        "actor",
        "created_at",
    ]
    list_filter = ["action", "entity_type", "created_at", "brand"]
    search_fields = ["actor", "entity_id", "brand__name"]
    readonly_fields = ["id", "created_at", "changes_display"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "brand", "entity_type", "entity_id", "action"),
            },
        ),
        (
            "Details",
            {
                "fields": ("actor", "changes_display", "created_at"),
            },
        ),
    )

    def changes_display(self, obj):
        """Display changes in a formatted way."""
        import json

        if obj.changes:
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; '
                'border-radius: 4px; overflow-x: auto;">{}</pre>',
                json.dumps(obj.changes, indent=2),
            )
        return "-"

    changes_display.short_description = "Changes"

    def has_add_permission(self, request):
        """Audit logs are read-only."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs are read-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deleted."""
        return False

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("brand")


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    """Admin interface for IdempotencyKey model."""

    list_display = [
        "key",
        "brand",
        "is_expired_display",
        "expires_at",
        "created_at",
    ]
    list_filter = ["expires_at", "created_at", "brand"]
    search_fields = ["key", "brand__name"]
    readonly_fields = [
        "id",
        "key",
        "response_data_display",
        "created_at",
        "expires_at",
    ]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "brand", "key"),
            },
        ),
        (
            "Response Data",
            {
                "fields": ("response_data_display",),
            },
        ),
        (
            "Expiration",
            {
                "fields": ("created_at", "expires_at"),
            },
        ),
    )

    def is_expired_display(self, obj):
        """Display expiration status."""
        if obj.is_expired:
            return format_html('<span style="color: red;">✗ Expired</span>')
        return format_html('<span style="color: green;">✓ Valid</span>')

    is_expired_display.short_description = "Status"

    def response_data_display(self, obj):
        """Display response data in a formatted way."""
        import json

        if obj.response_data:
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; '
                'border-radius: 4px; overflow-x: auto;">{}</pre>',
                json.dumps(obj.response_data, indent=2),
            )
        return "-"

    response_data_display.short_description = "Response Data"

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("brand")

