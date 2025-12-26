"""
Test settings for CentralizedLicenseService.
"""

import os

from .base import *  # noqa: F403, F401

DEBUG = False

# Use PostgreSQL in CI (from DATABASE_URL), SQLite in-memory for local tests
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    # Parse DATABASE_URL: postgresql://user:password@host:port/dbname
    import urllib.parse

    parsed = urllib.parse.urlparse(DATABASE_URL)
    # Override DATABASES from base.py
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path[1:] if parsed.path.startswith("/") else parsed.path,  # Remove leading '/'
            "USER": parsed.username or "postgres",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or 5432,
            "TEST": {
                "NAME": (parsed.path[1:] if parsed.path.startswith("/") else parsed.path) + "_test",
            },
        }
    }
    # Enable migrations in CI
    MIGRATION_MODULES = {}
else:
    # Use in-memory SQLite for faster local tests
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    # Enable migrations for local tests (pytest-django will handle this)
    # Migrations are needed to create tables even in in-memory SQLite
    MIGRATION_MODULES = {}

# Use in-memory cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Password hashers for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable logging during tests
LOGGING_CONFIG = None
