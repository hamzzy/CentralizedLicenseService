"""
Django admin configuration for products app.
"""

from django.contrib import admin

from products.infrastructure.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product model."""

    list_display = ["name", "slug", "brand", "license_count", "created_at"]
    list_filter = ["brand", "created_at", "updated_at"]
    search_fields = ["name", "slug", "brand__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "brand", "name", "slug"),
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
        """Display number of licenses for this product."""
        return obj.licenses.count()

    license_count.short_description = "Licenses"

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("brand").prefetch_related("licenses")
