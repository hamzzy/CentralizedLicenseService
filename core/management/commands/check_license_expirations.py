"""
Django management command to check and mark expired licenses.

This command should be run periodically (e.g., via cron or scheduled task).
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from licenses.infrastructure.models import License as LicenseModel
from licenses.infrastructure.repositories.django_license_repository import DjangoLicenseRepository

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command to check and mark expired licenses."""

    help = "Check and mark expired licenses"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run mode - don't actually update licenses",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        dry_run = options["dry_run"]
        repository = DjangoLicenseRepository()

        # Find licenses that are expired but still marked as valid
        now = timezone.now()
        # pylint: disable=no-member
        expired_licenses_queryset = LicenseModel.objects.filter(status="valid", expires_at__lt=now)

        count = expired_licenses_queryset.count()
        self.stdout.write(f"Found {count} expired license(s)")

        if dry_run:
            # pylint: disable=no-member
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            for license in expired_licenses_queryset[:10]:  # Show first 10
                self.stdout.write(f"  - License {license.id} expired at {license.expires_at}")
            return

        # Convert queryset to list before entering async context
        # This avoids issues with Django ORM in async functions
        expired_licenses = list(expired_licenses_queryset)

        if not expired_licenses:
            # pylint: disable=no-member
            self.stdout.write(self.style.SUCCESS("No expired licenses to update"))
            return

        # Mark licenses as expired
        import asyncio

        async def mark_expired():
            updated = 0
            for license_model in expired_licenses:
                try:
                    # pylint: disable=protected-access
                    # Convert to domain entity (synchronous method)
                    license_entity = repository._to_domain(license_model)
                    # Mark as expired
                    expired_entity = license_entity.mark_expired()
                    # Save (async)
                    await repository.save(expired_entity)
                    updated += 1
                    logger.info("Marked license %s as expired", license_model.id)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(
                        "Error marking license %s as expired: %s",
                        license_model.id,
                        e,
                        exc_info=True,
                    )
            return updated

        updated = asyncio.run(mark_expired())

        self.stdout.write(
            # pylint: disable=no-member
            self.style.SUCCESS(f"Successfully marked {updated} license(s) as expired")
        )
