"""
Webhook event handler.

Delivers webhooks when domain events occur.
"""

import logging
from typing import Dict

from core.domain.events import DomainEvent, EventHandler
from core.infrastructure.webhooks import WebhookDeliveryService
from licenses.domain.events import (
    LicenseCancelled,
    LicenseKeyCreated,
    LicenseProvisioned,
    LicenseRenewed,
    LicenseResumed,
    LicenseSuspended,
)

try:
    from activations.domain.events import LicenseActivated, SeatDeactivated
except ImportError:
    LicenseActivated = None
    SeatDeactivated = None

logger = logging.getLogger(__name__)


class WebhookEventHandler(EventHandler):
    """
    Event handler for webhook delivery.

    Delivers webhooks to brand systems when license events occur.
    """

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle domain event for webhook delivery.

        Args:
            event: Domain event to deliver via webhook
        """
        # Map event types to webhook event names
        event_type_map = {
            LicenseKeyCreated: "license_key.created",
            LicenseProvisioned: "license.provisioned",
            LicenseRenewed: "license.renewed",
            LicenseSuspended: "license.suspended",
            LicenseResumed: "license.resumed",
            LicenseCancelled: "license.cancelled",
        }

        if LicenseActivated:
            event_type_map[LicenseActivated] = "license.activated"
        if SeatDeactivated:
            event_type_map[SeatDeactivated] = "license.seat_deactivated"

        webhook_event_type = event_type_map.get(type(event))
        if not webhook_event_type:
            logger.debug(f"No webhook mapping for event type: {type(event)}")
            return

        # Extract brand_id from event
        brand_id = getattr(event, "brand_id", None)
        if not brand_id:
            logger.warning(f"Event {event.event_type} has no brand_id, skipping webhook")
            return

        # Prepare payload
        payload = {
            "event_id": str(event.event_id),
            "aggregate_id": str(event.aggregate_id),
            "occurred_at": event.occurred_at.isoformat(),
            "data": event.to_dict(),
        }

        # Deliver webhooks for this brand
        await WebhookDeliveryService.deliver_webhooks_for_event(
            brand_id=str(brand_id),
            event_type=webhook_event_type,
            payload=payload,
        )
