"""
RabbitMQ implementation of EventBus.

Replaces InMemoryEventBus with RabbitMQ for distributed event processing.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from kombu import Connection, Exchange, Queue
from kombu.pools import connections

from core.domain.events import DomainEvent, EventBus, EventHandler

logger = logging.getLogger(__name__)


class RabbitMQEventBus(EventBus):
    """
    RabbitMQ-based event bus implementation.

    Publishes events to RabbitMQ exchanges and queues.
    """

    def __init__(
        self,
        broker_url: str = "amqp://guest:guest@localhost:5672//",
        exchange_name: str = "license_events",
    ):
        """
        Initialize RabbitMQ event bus.

        Args:
            broker_url: RabbitMQ connection URL
            exchange_name: Exchange name for events
        """
        self.broker_url = broker_url
        self.exchange_name = exchange_name
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._exchange = Exchange(exchange_name, type="topic", durable=True)

    def _get_connection(self):
        """Get RabbitMQ connection from pool."""
        return connections[self.broker_url].acquire(block=True)

    def subscribe(self, event_type: str, handler: EventHandler):
        """
        Subscribe handler to event type.

        Args:
            event_type: Event type name
            handler: Event handler instance
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        logger.info("Subscribed handler %s to %s", handler.__class__.__name__, event_type)

    async def publish(self, event: DomainEvent):
        """
        Publish event to RabbitMQ.

        Args:
            event: Domain event to publish
        """
        try:
            with self._get_connection() as conn:
                # Create exchange
                self._exchange(conn).declare()

                # Serialize event
                event_data = {
                    "event_type": event.__class__.__name__,
                    "event_id": str(event.event_id),
                    "occurred_at": event.occurred_at.isoformat(),
                    "data": event.to_dict(),
                }

                # Publish to exchange with routing key
                routing_key = f"event.{event.__class__.__name__.lower()}"
                with conn.Producer(serializer="json") as producer:
                    producer.publish(
                        event_data,
                        exchange=self._exchange,
                        routing_key=routing_key,
                        declare=[self._exchange],
                    )

                logger.info(
                    "Published event %s to RabbitMQ (routing_key=%s)",
                    event.__class__.__name__,
                    routing_key,
                )

        except Exception as e:
            logger.error("Failed to publish event to RabbitMQ: %s", e, exc_info=True)
            raise

    def get_queue(self, queue_name: str) -> Queue:
        """
        Get or create queue for event consumption.

        Args:
            queue_name: Queue name

        Returns:
            Queue instance
        """
        return Queue(
            queue_name,
            exchange=self._exchange,
            routing_key="event.*",
            durable=True,
        )

    def consume_events(self, queue_name: str = "license_events_queue"):
        """
        Consume events from RabbitMQ queue.

        This should be run as a background task (Celery worker).

        Args:
            queue_name: Queue name to consume from
        """
        queue = self.get_queue(queue_name)

        conn = self._get_connection()
        try:
            with conn.Consumer(queue, callbacks=[self._handle_message]) as consumer:
                logger.info("Starting to consume events from queue: %s", queue_name)
                while True:
                    conn.drain_events(timeout=1)
        finally:
            conn.release()

    def _handle_message(self, body: Dict[str, Any], message):
        """
        Handle message from RabbitMQ.

        Dispatches to Celery task for async processing.

        Args:
            body: Message body
            message: Kombu message object
        """
        try:
            from CentralizedLicenseService.celery import app

            # Dispatch to Celery task for async processing using string name to avoid cyclic import
            app.send_task("core.tasks.process_event_from_rabbitmq", args=[body])

            message.ack()

        except Exception as e:
            logger.error("Failed to handle message: %s", e, exc_info=True)
            message.reject(requeue=True)
