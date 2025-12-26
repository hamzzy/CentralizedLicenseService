"""
Celery tasks for background processing.

Tasks for event processing.
"""

import logging

from CentralizedLicenseService.celery import app

logger = logging.getLogger(__name__)


@app.task
def process_event_from_rabbitmq(event_data: dict):
    """
    Process event from RabbitMQ queue.

    Args:
        event_data: Event data from RabbitMQ
    """
    from core.infrastructure.event_handlers import (
        AuditLogEventHandler,
        LicenseCacheInvalidationHandler,
    )

    event_type = event_data.get("event_type")
    data = event_data.get("data", {})

    # Create appropriate handler instances
    handlers = [
        AuditLogEventHandler(),
        LicenseCacheInvalidationHandler(),
    ]

    # Process with handlers
    import asyncio

    loop = asyncio.get_event_loop()
    for handler in handlers:
        try:
            # Simplified - in production, reconstruct proper event object
            loop.run_until_complete(handler.handle(data))
        except Exception as e:
            logger.error(f"Handler {handler.__class__.__name__} failed: {e}")
