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

    @sync_to_async
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit: {key}")
            else:
                logger.debug(f"Cache miss: {key}")
            return value
        except Exception as e:
            logger.error(f"Error getting from cache: {e}", exc_info=True)
            return None

    @sync_to_async
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Timeout in seconds (None for no expiration)
        """
        try:
            cache.set(key, value, timeout=timeout)
            logger.debug(f"Cache set: {key} (timeout={timeout})")
        except Exception as e:
            logger.error(f"Error setting cache: {e}", exc_info=True)

    @sync_to_async
    def delete(self, key: str) -> None:
        """
        Delete a value from cache.

        Args:
            key: Cache key
        """
        try:
            cache.delete(key)
            logger.debug(f"Cache delete: {key}")
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}", exc_info=True)

    @sync_to_async
    def clear(self, pattern: Optional[str] = None) -> None:
        """
        Clear cache entries matching a pattern.

        Args:
            pattern: Pattern to match (None for all)
        """
        try:
            if pattern:
                # Django cache doesn't support pattern matching directly
                # In production, use Redis cache backend for pattern support
                logger.warning(
                    f"Pattern-based cache clear not fully supported: {pattern}"
                )
            else:
                cache.clear()
                logger.debug("Cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)


# Global cache instance
cache_adapter = DjangoCacheAdapter()

