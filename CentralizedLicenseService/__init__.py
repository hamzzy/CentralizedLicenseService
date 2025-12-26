"""
Centralized License Service Django project.
"""
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

# Register event handlers after Django apps are loaded
import django
from django.apps import AppConfig


def setup_observability():
    """Setup observability and event handlers after apps are ready."""
    try:
        from core.instrumentation import setup_opentelemetry

        setup_opentelemetry()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to setup OpenTelemetry: {e}")


def register_event_handlers():
    """Register event handlers after apps are ready."""
    try:
        from core.infrastructure.event_handlers import (
            register_event_handlers as register,
        )

        register()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to register event handlers: {e}")


# Use Django's ready() signal to setup after apps are loaded
class CentralizedLicenseServiceConfig(AppConfig):
    """App configuration for CentralizedLicenseService."""

    name = "CentralizedLicenseService"
    verbose_name = "Centralized License Service"

    def ready(self):
        """Called when Django starts."""
        # Only run in main process (not in management commands that don't need it)
        import sys

        if "migrate" not in sys.argv and "makemigrations" not in sys.argv:
            setup_observability()
            register_event_handlers()


# Register the app config
default_app_config = "CentralizedLicenseService.apps.CentralizedLicenseServiceConfig"

__all__ = ("celery_app",)

