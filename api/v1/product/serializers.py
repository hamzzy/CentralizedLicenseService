"""
Serializers for Product API endpoints.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional

from rest_framework import serializers


class ActivateLicenseRequestSerializer(serializers.Serializer):
    """Serializer for activate license request - US3."""

    product_slug = serializers.CharField(required=True, max_length=100)
    instance_identifier = serializers.CharField(required=True, max_length=500)
    instance_type = serializers.ChoiceField(
        choices=["url", "hostname", "machine_id"], required=True
    )
    instance_metadata = serializers.DictField(required=False, allow_empty=True, default=dict)


class DeactivateSeatRequestSerializer(serializers.Serializer):
    """Serializer for deactivate seat request - US5."""

    instance_identifier = serializers.CharField(required=True, max_length=500)


class LicenseDTOSerializer(serializers.Serializer):
    """Serializer for LicenseDTO (shared with brand API)."""

    id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    status = serializers.CharField()
    seat_limit = serializers.IntegerField()
    seats_used = serializers.IntegerField()
    seats_remaining = serializers.IntegerField()
    expires_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class LicenseStatusResponseSerializer(serializers.Serializer):
    """Serializer for license status response - US4."""

    license_key = serializers.CharField()
    status = serializers.CharField()
    is_valid = serializers.BooleanField()  # License is valid (not expired, not suspended)
    is_activated = serializers.BooleanField()  # License has active activations (in use)
    licenses = LicenseDTOSerializer(many=True)
    total_seats_used = serializers.IntegerField()
    total_seats_available = serializers.IntegerField()


class ActivateLicenseResponseSerializer(serializers.Serializer):
    """Serializer for activate license response - US3."""

    activation_id = serializers.UUIDField()
    license_id = serializers.UUIDField()
    seats_remaining = serializers.IntegerField()
    message = serializers.CharField()


class ActivationStatusSerializer(serializers.Serializer):
    """Serializer for activation status response."""

    is_activated = serializers.BooleanField()
    activation_id = serializers.UUIDField(allow_null=True)
    activated_at = serializers.DateTimeField(allow_null=True)
    instance_identifier = serializers.CharField()
