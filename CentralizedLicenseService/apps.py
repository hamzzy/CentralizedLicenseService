"""
App configuration for Centralized License Service.
"""
from django.apps import AppConfig


class CentralizedLicenseServiceConfig(AppConfig):
    """App configuration for CentralizedLicenseService."""

    name = "CentralizedLicenseService"
    verbose_name = "Centralized License Service"

    def ready(self):
        """Called when Django starts."""
        # Only run in main process (not in management commands that don't need it)
        import sys

        if "migrate" not in sys.argv and "makemigrations" not in sys.argv:
            self.setup_observability()
            self.register_event_handlers()

    def setup_observability(self):
        """Setup observability after apps are ready."""
        try:
            from core.instrumentation import setup_opentelemetry

            setup_opentelemetry()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to setup OpenTelemetry: {e}")

    def register_event_handlers(self):
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

