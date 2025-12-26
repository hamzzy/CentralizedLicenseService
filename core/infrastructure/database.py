"""
Database utilities and transaction management.
"""

import contextlib
from typing import AsyncGenerator

from django.db import transaction


@contextlib.asynccontextmanager
async def async_transaction() -> AsyncGenerator[None, None]:
    """
    Async context manager for database transactions.

    Usage:
        async with async_transaction():
            # Database operations
            pass
    """
    with transaction.atomic():
        yield
