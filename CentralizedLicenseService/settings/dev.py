"""
Development settings for CentralizedLicenseService.
"""

from .base import *  # noqa: F403, F401

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Database - Use PostgreSQL in Docker, SQLite for local development
# Override with environment variable DB_ENGINE=sqlite for SQLite
import os

if os.environ.get("DB_ENGINE") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }
else:
    # Use PostgreSQL from docker-compose
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "license_service"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

# Add debug toolbar for development (if installed)
if DEBUG:
    try:
        import debug_toolbar  # noqa: F401

        INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
        MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405
        INTERNAL_IPS = ["127.0.0.1"]
    except ImportError:
        pass  # Debug toolbar not installed

# CORS settings for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
