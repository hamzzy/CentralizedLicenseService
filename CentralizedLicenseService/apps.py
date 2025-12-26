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
        import os
        import sys

        # Skip for management commands
        if len(sys.argv) > 1 and sys.argv[1] in [
            "migrate",
            "makemigrations",
            "collectstatic",
            "shell",
            "test",
            "check",
            "createsuperuser",
        ]:
            return

        # Skip if running in a subprocess (Django's reloader runs code twice)
        # RUN_MAIN is set by Django's reloader in the main process
        # In Docker/development, if RUN_MAIN is not set, we still want to setup
        # The _initialized flag will prevent duplicate setup
        if os.environ.get("RUN_MAIN") == "false":
            return

        # Only setup once (avoid duplicate registration)
        if not hasattr(self, "_initialized"):
            try:
                import logging

                logger = logging.getLogger(__name__)
                logger.info("Setting up observability...")
                self.setup_observability()
                self.register_event_handlers()
                self._initialized = True
                logger.info("Observability setup complete")
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error in AppConfig.ready(): {e}", exc_info=True)
                # Don't raise - allow app to start even if setup fails

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
            from core.infrastructure.event_handlers import register_event_handlers as register

            register()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to register event handlers: {e}")
