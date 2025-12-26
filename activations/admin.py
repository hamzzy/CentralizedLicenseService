"""
Django admin configuration for activations app.
"""

from django.contrib import admin
from django.utils.html import format_html

from activations.infrastructure.models import Activation


@admin.register(Activation)
class ActivationAdmin(admin.ModelAdmin):
    """Admin interface for Activation model."""

    list_display = [
        "license",
        "instance_identifier_display",
        "is_active_display",
        "activated_at",
        "last_checked_at",
    ]
    list_filter = [
        "is_active",
        "activated_at",
        "last_checked_at",
        "license__product__brand",
    ]
    search_fields = [
        "instance_identifier",
        "license__license_key__key",
        "license__license_key__customer_email",
    ]
    readonly_fields = [
        "id",
        "activated_at",
        "last_checked_at",
    ]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "license", "is_active"),
            },
        ),
        (
            "Instance Information",
            {
                "fields": ("instance_identifier", "instance_metadata"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("activated_at", "last_checked_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def instance_identifier_display(self, obj):
        """Display instance identifier with truncation."""
        if len(obj.instance_identifier) > 50:
            return format_html(
                '<span title="{}">{}</span>',
                obj.instance_identifier,
                obj.instance_identifier[:47] + "...",
            )
        return obj.instance_identifier

    instance_identifier_display.short_description = "Instance"

    def is_active_display(self, obj):
        """Display active status with color."""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Inactive</span>')

    is_active_display.short_description = "Status"

    def get_queryset(self, request):
        """Optimize queryset."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "license__license_key__brand",
                "license__product",
            )
        )
