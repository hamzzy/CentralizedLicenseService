"""
Celery tasks for background processing.

Tasks for webhook delivery and event processing.
"""
import logging

from CentralizedLicenseService.celery import app

from core.infrastructure.webhooks import WebhookDeliveryService

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3)
def deliver_webhook_task(
    self, webhook_config_id: str, event_type: str, payload: dict
):
    """
    Celery task for webhook delivery.

    Args:
        webhook_config_id: Webhook configuration UUID
        event_type: Event type
        payload: Webhook payload
    """
    import uuid

    from brands.infrastructure.models import WebhookConfig

    try:
        webhook_config = WebhookConfig.objects.get(id=uuid.UUID(webhook_config_id))

        # Use sync version for Celery task
        import asyncio

        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(
            WebhookDeliveryService.deliver_webhook(
                webhook_config, event_type, payload
            )
        )

        if not success:
            raise Exception("Webhook delivery failed")

    except Exception as exc:
        logger.error(f"Webhook delivery failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


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
        WebhookEventHandler,
    )

    event_type = event_data.get("event_type")
    data = event_data.get("data", {})

    # Create appropriate handler instances
    handlers = [
        AuditLogEventHandler(),
        LicenseCacheInvalidationHandler(),
    ]

    if WebhookEventHandler:
        handlers.append(WebhookEventHandler())

    # Process with handlers
    import asyncio

    loop = asyncio.get_event_loop()
    for handler in handlers:
        try:
            # Simplified - in production, reconstruct proper event object
            loop.run_until_complete(handler.handle(data))
        except Exception as e:
            logger.error(f"Handler {handler.__class__.__name__} failed: {e}")

