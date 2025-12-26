"""
Webhook delivery service.

Handles webhook delivery with retry logic and signature verification.
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests
from django.utils import timezone

from brands.infrastructure.models import WebhookConfig

logger = logging.getLogger(__name__)


class WebhookDeliveryService:
    """Service for delivering webhooks to brand systems."""

    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """
        Generate HMAC signature for webhook payload.

        Args:
            payload: JSON string payload
            secret: Webhook secret

        Returns:
            HMAC SHA-256 signature (hex)
        """
        return hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: JSON string payload
            signature: Expected signature
            secret: Webhook secret

        Returns:
            True if signature is valid
        """
        expected_signature = WebhookDeliveryService.generate_signature(
            payload, secret
        )
        return hmac.compare_digest(expected_signature, signature)

    @staticmethod
    async def deliver_webhook(
        webhook_config: WebhookConfig,
        event_type: str,
        payload: Dict[str, Any],
        retry_count: int = 0,
    ) -> bool:
        """
        Deliver webhook with retry logic.

        Args:
            webhook_config: Webhook configuration
            event_type: Event type (e.g., 'license.provisioned')
            payload: Webhook payload
            retry_count: Current retry attempt

        Returns:
            True if delivery succeeded, False otherwise
        """
        if not webhook_config.is_active:
            logger.debug(
                f"Webhook {webhook_config.id} is inactive, skipping"
            )
            return False

        # Check if webhook subscribes to this event
        if event_type not in webhook_config.events:
            logger.debug(
                f"Webhook {webhook_config.id} does not subscribe to {event_type}"
            )
            return False

        # Prepare payload
        webhook_payload = {
            "event_type": event_type,
            "timestamp": timezone.now().isoformat(),
            "data": payload,
        }
        payload_json = json.dumps(webhook_payload, sort_keys=True)

        # Generate signature
        signature = WebhookDeliveryService.generate_signature(
            payload_json, webhook_config.secret
        )

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type,
            "User-Agent": "License-Service-Webhook/1.0",
        }

        # Deliver webhook
        try:
            response = requests.post(
                webhook_config.url,
                data=payload_json,
                headers=headers,
                timeout=webhook_config.timeout_seconds,
            )
            response.raise_for_status()

            logger.info(
                f"Webhook delivered successfully: {webhook_config.id} - {event_type}"
            )
            return True

        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Webhook delivery failed: {webhook_config.id} - {event_type} - {e}"
            )

            # Retry logic
            if retry_count < webhook_config.max_retries:
                # Exponential backoff
                delay = 2 ** retry_count
                logger.info(
                    f"Retrying webhook {webhook_config.id} in {delay}s "
                    f"(attempt {retry_count + 1}/{webhook_config.max_retries})"
                )
                time.sleep(delay)

                return await WebhookDeliveryService.deliver_webhook(
                    webhook_config, event_type, payload, retry_count + 1
                )

            logger.error(
                f"Webhook delivery failed after {webhook_config.max_retries} "
                f"retries: {webhook_config.id} - {event_type}"
            )
            return False

    @staticmethod
    async def deliver_webhooks_for_event(
        brand_id: str, event_type: str, payload: Dict[str, Any]
    ):
        """
        Deliver webhooks to all active webhook configs for a brand.

        Uses Celery tasks for async delivery.

        Args:
            brand_id: Brand UUID
            event_type: Event type
            payload: Event payload
        """
        import uuid

        from core.tasks import deliver_webhook_task

        webhook_configs = WebhookConfig.objects.filter(
            brand_id=uuid.UUID(brand_id), is_active=True
        )

        # Dispatch webhook delivery tasks
        for webhook_config in webhook_configs:
            deliver_webhook_task.delay(
                str(webhook_config.id), event_type, payload
            )

