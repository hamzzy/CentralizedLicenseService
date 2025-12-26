"""
GetLicenseStatusHandler - US4.

Handler for getting license status query.
"""

import hashlib

from activations.ports.activation_repository import ActivationRepository
from brands.ports.product_repository import ProductRepository
from core.domain.exceptions import InvalidLicenseKeyError
from licenses.application.dto.license_dto import LicenseDTO, LicenseStatusDTO
from licenses.application.queries.get_license_status import GetLicenseStatusQuery
from licenses.application.services.license_cache_service import LicenseCacheService
from licenses.ports.license_key_repository import LicenseKeyRepository
from licenses.ports.license_repository import LicenseRepository


class GetLicenseStatusHandler:
    """Handler for GetLicenseStatusQuery."""

    def __init__(
        self,
        license_key_repository: LicenseKeyRepository,
        license_repository: LicenseRepository,
        product_repository: ProductRepository,
        activation_repository: ActivationRepository,
    ):
        """Initialize handler with repositories."""
        self.license_key_repository = license_key_repository
        self.license_repository = license_repository
        self.product_repository = product_repository
        self.activation_repository = activation_repository

    async def handle(self, query: GetLicenseStatusQuery) -> LicenseStatusDTO:
        """
        Handle get license status query.

        Args:
            query: GetLicenseStatusQuery

        Returns:
            LicenseStatusDTO with license status and entitlements

        Raises:
            InvalidLicenseKeyError: If license key not found
        """
        # Try cache first
        cached_status = await LicenseCacheService.get_license_status(query.license_key)
        if cached_status:
            with open("debug_cache.log", "a") as f:
                f.write("DEBUG: Cache HIT\n")
            return cached_status
        with open("debug_cache.log", "a") as f:
            f.write("DEBUG: Cache MISS\n")

        # Find license key by key hash
        key_hash = hashlib.sha256(query.license_key.encode()).hexdigest()
        license_key = await self.license_key_repository.find_by_key_hash(key_hash)

        if not license_key:
            raise InvalidLicenseKeyError("Invalid license key")

        # Get all licenses for this key
        licenses = await self.license_repository.find_by_license_key(license_key.id)

        # Build license DTOs with seat information
        license_dtos = []
        total_seats_used = 0
        total_seats_available = 0
        overall_valid = False

        for license in licenses:
            # Count active seats
            active_activations = await self.activation_repository.find_active_by_license(license.id)
            seats_used = len(active_activations)
            seats_remaining = max(0, license.seat_limit - seats_used)

            # Get product name
            product = await self.product_repository.find_by_id(license.product_id)
            product_name = product.name if product else "Unknown"

            # Check if license is valid
            is_valid = license.is_valid()
            if is_valid:
                overall_valid = True

            license_dtos.append(
                LicenseDTO(
                    id=license.id,
                    product_id=license.product_id,
                    product_name=product_name,
                    status=license.status.value,
                    seat_limit=license.seat_limit,
                    seats_used=seats_used,
                    seats_remaining=seats_remaining,
                    expires_at=license.expires_at,
                    created_at=license.created_at,
                )
            )

            total_seats_used += seats_used
            total_seats_available += seats_remaining

        result = LicenseStatusDTO(
            license_key=query.license_key,
            status="valid" if overall_valid else "invalid",
            is_valid=overall_valid,
            licenses=license_dtos,
            total_seats_used=total_seats_used,
            total_seats_available=total_seats_available,
        )

        # Cache the result
        await LicenseCacheService.set_license_status(query.license_key, result)

        return result
