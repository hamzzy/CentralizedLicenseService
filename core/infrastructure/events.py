"""
In-memory event bus implementation.

This is a simple in-memory implementation suitable for modular monolith.
For production scale, this could be replaced with Redis, RabbitMQ, etc.
"""

import asyncio
import logging
from typing import Dict, List, Type

from core.domain.events import DomainEvent, EventBus, EventHandler

logger = logging.getLogger(__name__)


class InMemoryEventBus(EventBus):
    """
    In-memory event bus implementation.

    This implementation stores handlers in memory and processes
    events synchronously. For async processing, events are handled
    in a background task.
    """

    def __init__(self):
        """Initialize the event bus."""
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}
        self._loop = None

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Subscribe to a domain event type.

        Args:
            event_type: The type of event to subscribe to
            handler: The handler to call when event is published
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__class__.__name__} to {event_type.__name__}")

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event.

        Args:
            event: The domain event to publish
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers registered for {event_type.__name__}")
            return

        logger.info(f"Publishing {event_type.__name__} to {len(handlers)} handler(s)")

        # Process handlers concurrently
        tasks = [self._handle_event(handler, event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_event(self, handler: EventHandler, event: DomainEvent) -> None:
        """
        Handle an event with a specific handler.

        Args:
            handler: The handler to use
            event: The event to handle
        """
        try:
            await handler.handle(event)
            logger.debug(
                f"Successfully handled {event.event_type} with {handler.__class__.__name__}"
            )
        except Exception as e:
            logger.error(
                f"Error handling {event.event_type} with {handler.__class__.__name__}: {e}",
                exc_info=True,
            )
            # In production, you might want to retry or send to dead letter queue
            raise


# Global event bus instance
# Use RabbitMQ in production, InMemoryEventBus for development/testing
import os

if os.environ.get("USE_RABBITMQ", "false").lower() == "true":
    from core.infrastructure.rabbitmq_event_bus import RabbitMQEventBus

    broker_url = os.environ.get(
        "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"
    )
    event_bus = RabbitMQEventBus(broker_url=broker_url)
else:
    event_bus = InMemoryEventBus()
