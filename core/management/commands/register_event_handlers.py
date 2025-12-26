"""
Django management command to register event handlers.

This should be called at application startup.
"""
import logging

from django.core.management.base import BaseCommand

from core.infrastructure.event_handlers import register_event_handlers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command to register event handlers."""

    help = "Register event handlers with the event bus"

    def handle(self, *args, **options):
        """Execute the command."""
        register_event_handlers()
        self.stdout.write(
            self.style.SUCCESS("Event handlers registered successfully")
        )

