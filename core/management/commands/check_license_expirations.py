"""
Django management command to check and mark expired licenses.

This command should be run periodically (e.g., via cron or scheduled task).
"""
import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from licenses.infrastructure.repositories.django_license_repository import (
    DjangoLicenseRepository,
)
from licenses.infrastructure.models import License as LicenseModel

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
        expired_licenses = LicenseModel.objects.filter(
            status="valid", expires_at__lt=now
        )

        count = expired_licenses.count()
        self.stdout.write(f"Found {count} expired license(s)")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No changes will be made")
            )
            for license in expired_licenses[:10]:  # Show first 10
                self.stdout.write(
                    f"  - License {license.id} expired at {license.expires_at}"
                )
            return

        # Mark licenses as expired
        updated = 0
        for license_model in expired_licenses:
            try:
                # Convert to domain entity
                license_entity = repository._to_domain(license_model)
                # Mark as expired
                expired_entity = license_entity.mark_expired()
                # Save
                repository.save(expired_entity)
                updated += 1
                logger.info(f"Marked license {license_model.id} as expired")
            except Exception as e:
                logger.error(
                    f"Error marking license {license_model.id} as expired: {e}",
                    exc_info=True,
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully marked {updated} license(s) as expired")
        )

