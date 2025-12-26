"""
Cache adapter implementations.

Provides Redis and Django cache implementations of CachePort.
"""

import json
import logging
from typing import Any, Optional

from asgiref.sync import sync_to_async
from django.core.cache import cache

from core.infrastructure.cache import CachePort

logger = logging.getLogger(__name__)


class DjangoCacheAdapter(CachePort):
    """
    Django cache adapter implementing CachePort.

    Uses Django's cache framework (can be Redis, Memcached, etc.).
    """

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = await sync_to_async(cache.get)(key)
            if value is not None:
                logger.debug("Cache hit: %s", key)
            else:
                logger.debug("Cache miss: %s", key)
            return value
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error getting from cache: %s", e, exc_info=True)
            return None

    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Timeout in seconds (None for no expiration)
        """
        try:
            await sync_to_async(cache.set)(key, value, timeout=timeout)
            logger.debug("Cache set: %s (timeout=%s)", key, timeout)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error setting cache: %s", e, exc_info=True)

    async def delete(self, key: str) -> None:
        """
        Delete a value from cache.

        Args:
            key: Cache key
        """
        try:
            await sync_to_async(cache.delete)(key)
            logger.debug("Cache delete: %s", key)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error deleting from cache: %s", e, exc_info=True)

    async def clear(self, pattern: Optional[str] = None) -> None:
        """
        Clear cache entries matching a pattern.

        Args:
            pattern: Pattern to match (None for all)
        """
        try:
            if pattern:
                # Django cache doesn't support pattern matching directly
                # In production, use Redis cache backend for pattern support
                logger.warning("Pattern-based cache clear not fully supported: %s", pattern)
            else:
                await sync_to_async(cache.clear)()
                logger.debug("Cache cleared")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error clearing cache: %s", e, exc_info=True)


# Global cache instance
cache_adapter = DjangoCacheAdapter()
