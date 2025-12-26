"""
Django admin configuration for brands app.
"""

from django.contrib import admin
from django.utils.html import format_html

from brands.infrastructure.models import ApiKey, Brand


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Admin interface for Brand model."""

    list_display = ["name", "slug", "prefix", "created_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["name", "slug", "prefix"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "name", "slug", "prefix"),
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

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).prefetch_related("api_keys")


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    """Admin interface for ApiKey model."""

    list_display = [
        "brand",
        "key_prefix_display",
        "scope",
        "is_valid_display",
        "expires_at",
        "last_used_at",
        "created_at",
    ]
    list_filter = ["scope", "expires_at", "created_at", "brand"]
    search_fields = ["key_prefix", "brand__name", "brand__slug"]
    readonly_fields = [
        "id",
        "key_prefix",
        "key_hash",
        "created_at",
        "last_used_at",
        "raw_key_display",
        "is_valid_display",
    ]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "brand", "scope"),
            },
        ),
        (
            "Key Information",
            {
                "fields": ("key_prefix", "key_hash", "raw_key_display"),
                "description": "The raw key is only shown once when created.",
            },
        ),
        (
            "Validity",
            {
                "fields": ("expires_at", "is_valid_display"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "last_used_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def key_prefix_display(self, obj):
        """Display key prefix with ellipsis."""
        return f"{obj.key_prefix}..."

    key_prefix_display.short_description = "Key Prefix"

    def is_valid_display(self, obj):
        """Display validity status with color."""
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')

    is_valid_display.short_description = "Status"

    def raw_key_display(self, obj):
        """Display raw key if available."""
        if hasattr(obj, "_raw_key"):
            return format_html(
                '<code style="background: #f0f0f0; padding: 4px 8px; '
                'border-radius: 3px;">{}</code>',
                obj._raw_key,
            )
        return format_html(
            '<span style="color: #999;">Raw key not available '
            "(only shown once at creation)</span>"
        )

    raw_key_display.short_description = "Raw Key"

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("brand")

    def save_model(self, request, obj, form, change):
        """Save model and show raw key if new."""
        super().save_model(request, obj, form, change)
        if not change and hasattr(obj, "_raw_key"):
            self.message_user(
                request,
                f"API Key created! Raw key: {obj._raw_key} "
                "(Save this - it won't be shown again)",
                level="WARNING",
            )
