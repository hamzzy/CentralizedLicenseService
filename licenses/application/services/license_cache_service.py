"""
License cache service.

Provides caching for license validation and status queries.
"""
import hashlib
import json
import logging
from typing import Optional

from core.infrastructure.cache_adapters import cache_adapter
from licenses.application.dto.license_dto import LicenseStatusDTO

logger = logging.getLogger(__name__)

# Cache TTLs (in seconds)
CACHE_TTL_LICENSE_STATUS = 300  # 5 minutes
CACHE_TTL_LICENSE_VALIDATION = 60  # 1 minute


class LicenseCacheService:
    """Service for caching license-related data."""

    @staticmethod
    def _license_status_key(license_key: str) -> str:
        """Generate cache key for license status."""
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()[:16]
        return f"license:status:{key_hash}"

    @staticmethod
    def _license_validation_key(
        license_key: str, product_id: str
    ) -> str:
        """Generate cache key for license validation."""
        combined = f"{license_key}:{product_id}"
        key_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return f"license:validation:{key_hash}"

    @staticmethod
    async def get_license_status(
        license_key: str,
    ) -> Optional[LicenseStatusDTO]:
        """
        Get cached license status.

        Args:
            license_key: License key

        Returns:
            Cached LicenseStatusDTO or None
        """
        cache_key = LicenseCacheService._license_status_key(license_key)
        cached = await cache_adapter.get(cache_key)
        if cached:
            try:
                # Deserialize from dict
                return LicenseStatusDTO(**cached)
            except Exception as e:
                logger.warning(f"Error deserializing cached status: {e}")
                return None
        return None

    @staticmethod
    async def set_license_status(
        license_key: str, status: LicenseStatusDTO, ttl: int = None
    ) -> None:
        """
        Cache license status.

        Args:
            license_key: License key
            status: LicenseStatusDTO to cache
            ttl: Time to live in seconds
        """
        cache_key = LicenseCacheService._license_status_key(license_key)
        # Serialize to dict
        status_dict = {
            "license_key": status.license_key,
            "status": status.status,
            "is_valid": status.is_valid,
            "licenses": [
                {
                    "id": str(license.id),
                    "product_id": str(license.product_id),
                    "product_name": license.product_name,
                    "status": license.status,
                    "seat_limit": license.seat_limit,
                    "seats_used": license.seats_used,
                    "seats_remaining": license.seats_remaining,
                    "expires_at": (
                        license.expires_at.isoformat()
                        if license.expires_at
                        else None
                    ),
                    "created_at": license.created_at.isoformat(),
                }
                for license in status.licenses
            ],
            "total_seats_used": status.total_seats_used,
            "total_seats_available": status.total_seats_available,
        }
        await cache_adapter.set(
            cache_key, status_dict, timeout=ttl or CACHE_TTL_LICENSE_STATUS
        )

    @staticmethod
    async def invalidate_license_status(license_key: str) -> None:
        """
        Invalidate cached license status.

        Args:
            license_key: License key
        """
        cache_key = LicenseCacheService._license_status_key(license_key)
        await cache_adapter.delete(cache_key)
        logger.info(f"Invalidated license status cache: {license_key[:8]}...")

    @staticmethod
    async def invalidate_license_key_cache(license_key_id: str) -> None:
        """
        Invalidate all cache entries for a license key.

        Args:
            license_key_id: License key ID
        """
        # In production with Redis, use pattern matching
        # For now, we'll invalidate on license updates
        logger.debug(f"Invalidating cache for license key: {license_key_id}")

