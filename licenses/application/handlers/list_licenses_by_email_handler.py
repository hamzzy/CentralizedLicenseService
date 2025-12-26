"""
ListLicensesByEmailHandler - US6.

Handler for listing licenses by customer email.
"""

from typing import List

from activations.ports.activation_repository import ActivationRepository
from brands.ports.brand_repository import BrandRepository
from brands.ports.product_repository import ProductRepository
from licenses.application.dto.license_dto import LicenseListItemDTO
from licenses.application.queries.list_licenses_by_email import ListLicensesByEmailQuery
from licenses.ports.license_key_repository import LicenseKeyRepository
from licenses.ports.license_repository import LicenseRepository


class ListLicensesByEmailHandler:
    """Handler for ListLicensesByEmailQuery."""

    def __init__(
        self,
        license_key_repository: LicenseKeyRepository,
        license_repository: LicenseRepository,
        brand_repository: BrandRepository,
        product_repository: ProductRepository,
        activation_repository: ActivationRepository,
    ):
        """Initialize handler with repositories."""
        self.license_key_repository = license_key_repository
        self.license_repository = license_repository
        self.brand_repository = brand_repository
        self.product_repository = product_repository
        self.activation_repository = activation_repository

    async def handle(self, query: ListLicensesByEmailQuery) -> List[LicenseListItemDTO]:
        """
        Handle list licenses by email query.

        Args:
            query: ListLicensesByEmailQuery

        Returns:
            List of LicenseListItemDTO
        """
        # Find license keys by email and brand
        license_keys = await self.license_key_repository.find_by_customer_email(
            query.brand_id, query.customer_email
        )

        # Get brand
        brand = await self.brand_repository.find_by_id(query.brand_id)
        brand_name = brand.name if brand else "Unknown"

        # Build list of licenses
        license_list = []

        for license_key in license_keys:
            # Get all licenses for this key
            licenses = await self.license_repository.find_by_license_key(license_key.id)

            for license in licenses:
                # Get product
                product = await self.product_repository.find_by_id(license.product_id)
                product_name = product.name if product else "Unknown"

                # Count active seats
                active_activations = await self.activation_repository.find_active_by_license(
                    license.id
                )
                seats_used = len(active_activations)

                license_list.append(
                    LicenseListItemDTO(
                        license_key=license_key.key,
                        brand_name=brand_name,
                        product_name=product_name,
                        status=license.status.value,
                        expires_at=license.expires_at,
                        seats_used=seats_used,
                        seat_limit=license.seat_limit,
                    )
                )

        return license_list
