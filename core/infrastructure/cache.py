"""
Cache abstraction (port).

This module defines the cache interface that can be implemented
with different backends (Redis, Memcached, in-memory, etc.).
"""
from abc import ABC, abstractmethod
from typing import Any, Optional


class CachePort(ABC):
    """
    Abstract cache port.

    This defines the interface for caching operations.
    Implementations can use Redis, Memcached, or in-memory cache.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Timeout in seconds (None for no expiration)
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete a value from cache.

        Args:
            key: Cache key
        """
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> None:
        """
        Clear cache entries matching a pattern.

        Args:
            pattern: Pattern to match (None for all)
        """
        pass

