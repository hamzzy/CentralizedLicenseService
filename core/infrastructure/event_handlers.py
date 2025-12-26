"""
Event handlers for domain events.

These handlers process domain events asynchronously for side effects
like audit logging, notifications, cache invalidation, etc.
"""
import logging
from typing import Dict

from core.domain.events import DomainEvent, EventHandler
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


class AuditLogEventHandler(EventHandler):
    """
    Event handler for audit logging.

    Logs all domain events to audit log (to be implemented).
    """

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle domain event for audit logging.

        Args:
            event: Domain event to log
        """
        logger.info(
            f"Audit log: {event.event_type} - {event.aggregate_id}",
            extra={
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "occurred_at": event.occurred_at.isoformat(),
            },
        )
        # TODO: Write to AuditLog model in production


class LicenseCacheInvalidationHandler(EventHandler):
    """
    Event handler for cache invalidation.

    Invalidates cache when license-related events occur.
    """

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle domain event for cache invalidation.

        Args:
            event: Domain event
        """
        from licenses.application.services.license_cache_service import (
            LicenseCacheService,
        )

        # Invalidate cache for license lifecycle events
        event_types = [
            LicenseRenewed,
            LicenseSuspended,
            LicenseResumed,
            LicenseCancelled,
        ]
        if LicenseActivated:
            event_types.append(LicenseActivated)
        if SeatDeactivated:
            event_types.append(SeatDeactivated)

        if isinstance(event, tuple(event_types)):
            # Get license key from event
            # For now, log - full implementation would fetch license_key
            logger.debug(
                f"Cache invalidation needed for event: {event.event_type}"
            )
            # TODO: Implement full cache invalidation based on event


class LicenseExpirationCheckHandler(EventHandler):
    """
    Event handler for license expiration checks.

    Checks and marks expired licenses (to be run as background task).
    """

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle domain event for expiration checks.

        Args:
            event: Domain event
        """
        # This would be called periodically, not on every event
        logger.debug(f"Expiration check triggered by: {event.event_type}")


# Register event handlers
def register_event_handlers():
    """Register all event handlers with the event bus."""
    from core.infrastructure.events import event_bus

    audit_handler = AuditLogEventHandler()
    cache_handler = LicenseCacheInvalidationHandler()

    # Register handlers for all license events
    event_bus.subscribe(LicenseKeyCreated, audit_handler)
    event_bus.subscribe(LicenseProvisioned, audit_handler)
    event_bus.subscribe(LicenseRenewed, audit_handler)
    event_bus.subscribe(LicenseSuspended, audit_handler)
    event_bus.subscribe(LicenseResumed, audit_handler)
    event_bus.subscribe(LicenseCancelled, audit_handler)

    # Register activation event handlers if available
    if LicenseActivated:
        event_bus.subscribe(LicenseActivated, audit_handler)
    if SeatDeactivated:
        event_bus.subscribe(SeatDeactivated, audit_handler)

    # Register cache invalidation handlers
    event_bus.subscribe(LicenseRenewed, cache_handler)
    event_bus.subscribe(LicenseSuspended, cache_handler)
    event_bus.subscribe(LicenseResumed, cache_handler)
    event_bus.subscribe(LicenseCancelled, cache_handler)

    if LicenseActivated:
        event_bus.subscribe(LicenseActivated, cache_handler)
    if SeatDeactivated:
        event_bus.subscribe(SeatDeactivated, cache_handler)

    logger.info("Event handlers registered")

