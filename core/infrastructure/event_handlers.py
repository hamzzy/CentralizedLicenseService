"""
Event handlers for domain events.

These handlers process domain events asynchronously for side effects
like audit logging, notifications, cache invalidation, etc.
"""

import logging

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
            "Audit log: %s - %s",
            event.event_type,
            event.aggregate_id,
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
        from licenses.application.services.license_cache_service import LicenseCacheService
        from licenses.infrastructure.repositories.django_license_key_repository import (  # noqa: E501
            DjangoLicenseKeyRepository,
        )
        from licenses.infrastructure.repositories.django_license_repository import (  # noqa: E501
            DjangoLicenseRepository,
        )

        license_repo = DjangoLicenseRepository()
        license_key_repo = DjangoLicenseKeyRepository()

        try:
            license_key_str = None

            # Handle events with license_key_id directly
            if isinstance(event, LicenseKeyCreated):
                license_key_obj = await license_key_repo.find_by_id(event.license_key_id)
                if license_key_obj:
                    license_key_str = license_key_obj.key

            # Handle events with license_key_id via license_id
            elif isinstance(event, LicenseProvisioned):
                license_key_obj = await license_key_repo.find_by_id(event.license_key_id)
                if license_key_obj:
                    license_key_str = license_key_obj.key

            # Handle events with only license_id (need to fetch license first)
            elif isinstance(
                event,
                (LicenseRenewed, LicenseSuspended, LicenseResumed, LicenseCancelled),
            ):
                license_obj = await license_repo.find_by_id(event.license_id)
                if license_obj:
                    license_key_obj = await license_key_repo.find_by_id(license_obj.license_key_id)
                    if license_key_obj:
                        license_key_str = license_key_obj.key

            # Handle activation events
            elif LicenseActivated and isinstance(event, LicenseActivated):
                license_obj = await license_repo.find_by_id(event.license_id)
                if license_obj:
                    license_key_obj = await license_key_repo.find_by_id(license_obj.license_key_id)
                    if license_key_obj:
                        license_key_str = license_key_obj.key

            elif SeatDeactivated and isinstance(event, SeatDeactivated):
                license_obj = await license_repo.find_by_id(event.license_id)
                if license_obj:
                    license_key_obj = await license_key_repo.find_by_id(license_obj.license_key_id)
                    if license_key_obj:
                        license_key_str = license_key_obj.key

            # Invalidate cache if we have the license key
            if license_key_str:
                await LicenseCacheService.invalidate_license_status(license_key_str)
                logger.info(
                    "Cache invalidated for license key (event: %s)",
                    event.event_type,
                )
            else:
                logger.warning(
                    "Could not find license key for cache invalidation "
                    "(event: %s, aggregate_id: %s)",
                    event.event_type,
                    event.aggregate_id,
                )

        except Exception as e:
            logger.error(
                "Error invalidating cache for event %s: %s",
                event.event_type,
                e,
                exc_info=True,
            )


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
        logger.debug("Expiration check triggered by: %s", event.event_type)


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
