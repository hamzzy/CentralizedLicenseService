"""
License lifecycle handlers - US2.

Handlers for renew, suspend, resume, and cancel license commands.
"""
import uuid

from core.domain.exceptions import LicenseNotFoundError
from core.infrastructure.events import event_bus
from licenses.application.commands.cancel_license import CancelLicenseCommand
from licenses.application.commands.renew_license import RenewLicenseCommand
from licenses.application.commands.resume_license import ResumeLicenseCommand
from licenses.application.commands.suspend_license import SuspendLicenseCommand
from licenses.application.services.license_cache_service import (
    LicenseCacheService,
)
from licenses.domain.events import (
    LicenseCancelled,
    LicenseRenewed,
    LicenseResumed,
    LicenseSuspended,
)
from licenses.domain.services import LicenseLifecycleManager
from licenses.ports.license_key_repository import LicenseKeyRepository
from licenses.ports.license_repository import LicenseRepository


class RenewLicenseHandler:
    """Handler for RenewLicenseCommand."""

    def __init__(
        self,
        license_repository: LicenseRepository,
        license_key_repository: LicenseKeyRepository = None,
    ):
        """Initialize handler with repositories."""
        self.license_repository = license_repository
        self.license_key_repository = license_key_repository

    async def handle(self, command: RenewLicenseCommand):
        """
        Handle renew license command.

        Args:
            command: RenewLicenseCommand

        Returns:
            Renewed License entity

        Raises:
            LicenseNotFoundError: If license not found
        """
        license = await self.license_repository.find_by_id(command.license_id)
        if not license:
            raise LicenseNotFoundError(
                f"License {command.license_id} not found"
            )

        renewed = await LicenseLifecycleManager.renew_license(
            license, command.expiration_date, self.license_repository
        )

        # Invalidate cache
        if self.license_key_repository:
            license_key = await self.license_key_repository.find_by_id(
                renewed.license_key_id
            )
            if license_key:
                await LicenseCacheService.invalidate_license_status(
                    license_key.key
                )

        # Publish event
        await event_bus.publish(
            LicenseRenewed(
                license_id=renewed.id,
                new_expiration=command.expiration_date,
            )
        )

        return renewed


class SuspendLicenseHandler:
    """Handler for SuspendLicenseCommand."""

    def __init__(
        self,
        license_repository: LicenseRepository,
        license_key_repository: LicenseKeyRepository = None,
    ):
        """Initialize handler with repositories."""
        self.license_repository = license_repository
        self.license_key_repository = license_key_repository

    async def handle(self, command: SuspendLicenseCommand):
        """
        Handle suspend license command.

        Args:
            command: SuspendLicenseCommand

        Returns:
            Suspended License entity

        Raises:
            LicenseNotFoundError: If license not found
        """
        license = await self.license_repository.find_by_id(command.license_id)
        if not license:
            raise LicenseNotFoundError(
                f"License {command.license_id} not found"
            )

        suspended = await LicenseLifecycleManager.suspend_license(
            license, self.license_repository
        )

        # Invalidate cache
        if self.license_key_repository:
            license_key = await self.license_key_repository.find_by_id(
                suspended.license_key_id
            )
            if license_key:
                await LicenseCacheService.invalidate_license_status(
                    license_key.key
                )

        # Publish event
        await event_bus.publish(LicenseSuspended(license_id=suspended.id))

        return suspended


class ResumeLicenseHandler:
    """Handler for ResumeLicenseCommand."""

    def __init__(
        self,
        license_repository: LicenseRepository,
        license_key_repository: LicenseKeyRepository = None,
    ):
        """Initialize handler with repositories."""
        self.license_repository = license_repository
        self.license_key_repository = license_key_repository

    async def handle(self, command: ResumeLicenseCommand):
        """
        Handle resume license command.

        Args:
            command: ResumeLicenseCommand

        Returns:
            Resumed License entity

        Raises:
            LicenseNotFoundError: If license not found
        """
        license = await self.license_repository.find_by_id(command.license_id)
        if not license:
            raise LicenseNotFoundError(
                f"License {command.license_id} not found"
            )

        resumed = await LicenseLifecycleManager.resume_license(
            license, self.license_repository
        )

        # Invalidate cache
        if self.license_key_repository:
            license_key = await self.license_key_repository.find_by_id(
                resumed.license_key_id
            )
            if license_key:
                await LicenseCacheService.invalidate_license_status(
                    license_key.key
                )

        # Publish event
        await event_bus.publish(LicenseResumed(license_id=resumed.id))

        return resumed


class CancelLicenseHandler:
    """Handler for CancelLicenseCommand."""

    def __init__(
        self,
        license_repository: LicenseRepository,
        license_key_repository: LicenseKeyRepository = None,
    ):
        """Initialize handler with repositories."""
        self.license_repository = license_repository
        self.license_key_repository = license_key_repository

    async def handle(self, command: CancelLicenseCommand):
        """
        Handle cancel license command.

        Args:
            command: CancelLicenseCommand

        Returns:
            Cancelled License entity

        Raises:
            LicenseNotFoundError: If license not found
        """
        license = await self.license_repository.find_by_id(command.license_id)
        if not license:
            raise LicenseNotFoundError(
                f"License {command.license_id} not found"
            )

        cancelled = await LicenseLifecycleManager.cancel_license(
            license, self.license_repository
        )

        # Invalidate cache
        if self.license_key_repository:
            license_key = await self.license_key_repository.find_by_id(
                cancelled.license_key_id
            )
            if license_key:
                await LicenseCacheService.invalidate_license_status(
                    license_key.key
                )

        # Publish event
        await event_bus.publish(LicenseCancelled(license_id=cancelled.id))

        return cancelled

