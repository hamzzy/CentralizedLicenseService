"""
Serializers for Brand API endpoints.
"""

from rest_framework import serializers


class ProvisionLicenseRequestSerializer(serializers.Serializer):
    """Serializer for provision license request - US1."""

    customer_email = serializers.EmailField(required=True)
    products = serializers.ListField(child=serializers.UUIDField(), required=True, min_length=1)
    expiration_date = serializers.DateTimeField(required=False, allow_null=True)
    max_seats = serializers.IntegerField(required=False, default=1, min_value=1)

    def validate_products(self, value):
        """Validate products list."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one product is required")
        return value


class RenewLicenseRequestSerializer(serializers.Serializer):
    """Serializer for renew license request - US2."""

    expiration_date = serializers.DateTimeField(required=True)


class SuspendLicenseRequestSerializer(serializers.Serializer):
    """Serializer for suspend license request - US2."""

    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ResumeLicenseRequestSerializer(serializers.Serializer):
    """Serializer for resume license request - US2."""


class CancelLicenseRequestSerializer(serializers.Serializer):
    """Serializer for cancel license request - US2."""

    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class LicenseDTOSerializer(serializers.Serializer):
    """Serializer for LicenseDTO."""

    id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    status = serializers.CharField()
    seat_limit = serializers.IntegerField()
    seats_used = serializers.IntegerField()
    seats_remaining = serializers.IntegerField()
    expires_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class LicenseKeyDTOSerializer(serializers.Serializer):
    """Serializer for LicenseKeyDTO."""

    id = serializers.UUIDField()
    key = serializers.CharField()
    brand_id = serializers.UUIDField()
    customer_email = serializers.EmailField()
    created_at = serializers.DateTimeField()


class ProvisionLicenseResponseSerializer(serializers.Serializer):
    """Serializer for provision license response - US1."""

    license_key = LicenseKeyDTOSerializer()
    licenses = LicenseDTOSerializer(many=True)


class LicenseListItemSerializer(serializers.Serializer):
    """Serializer for license list item - US6."""

    license_key = serializers.CharField()
    brand_name = serializers.CharField()
    product_name = serializers.CharField()
    status = serializers.CharField()
    expires_at = serializers.DateTimeField(allow_null=True)
    seats_used = serializers.IntegerField()
    seat_limit = serializers.IntegerField()
