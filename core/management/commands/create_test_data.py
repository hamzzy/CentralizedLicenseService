"""
Django management command to create test data for development and testing.

Creates:
- A superuser (admin/admin)
- A test brand
- An API key for the brand
- A test product
- Optionally, a test license key and license
"""

import asyncio
import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from brands.domain.brand import Brand
from brands.domain.product import Product
from brands.infrastructure.models import ApiKey
from brands.infrastructure.models import Brand as BrandModel
from brands.infrastructure.repositories.django_brand_repository import DjangoBrandRepository
from brands.infrastructure.repositories.django_product_repository import DjangoProductRepository
from licenses.domain.license import License
from licenses.domain.license_key import LicenseKey
from licenses.infrastructure.repositories.django_license_key_repository import (  # noqa: E501
    DjangoLicenseKeyRepository,
)
from licenses.infrastructure.repositories.django_license_repository import DjangoLicenseRepository

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    """Command to create test data."""

    help = "Create test data (superuser, brand, API key, product, license)"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--skip-superuser",
            action="store_true",
            help="Skip creating superuser",
        )
        parser.add_argument(
            "--skip-license",
            action="store_true",
            help="Skip creating test license",
        )
        parser.add_argument(
            "--brand-name",
            type=str,
            default="Test Brand",
            help="Brand name (default: Test Brand)",
        )
        parser.add_argument(
            "--brand-slug",
            type=str,
            default=None,
            help="Brand slug (default: auto-generated)",
        )
        parser.add_argument(
            "--brand-prefix",
            type=str,
            default=None,
            help="Brand prefix for license keys (default: TEST)",
        )
        parser.add_argument(
            "--product-name",
            type=str,
            default="Test Product",
            help="Product name (default: Test Product)",
        )
        parser.add_argument(
            "--customer-email",
            type=str,
            default="test@example.com",
            help="Customer email for test license (default: test@example.com)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        with transaction.atomic():
            # Create superuser
            if not options["skip_superuser"]:
                self.create_superuser()

            # Run async operations
            brand, api_key, product, license_key = asyncio.run(self.create_async_data(options))

            # Print summary
            self.print_summary(brand, api_key, product, license_key)

    async def create_async_data(self, options):
        """Create async data (brand, API key, product, license)."""
        # Create brand
        brand = await self.create_brand(
            name=options["brand_name"],
            slug=options["brand_slug"],
            prefix=options["brand_prefix"],
        )

        # Create API key
        api_key = self.create_api_key(brand)

        # Create product
        product = await self.create_product(brand, options["product_name"])

        # Create license (optional)
        license_key = None
        if not options["skip_license"]:
            license_key = await self.create_test_license(brand, product, options["customer_email"])
            # pylint: disable=no-member
            self.stdout.write(self.style.SUCCESS(f"\n✅ Test License Key: {license_key.key}\n"))

        return brand, api_key, product, license_key

    def create_superuser(self):
        """Create a superuser if it doesn't exist."""
        username = "admin"
        email = "admin@example.com"
        password = "admin"

        if User.objects.filter(username=username).exists():
            # pylint: disable=no-member
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists"))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        # pylint: disable=no-member
        self.stdout.write(self.style.SUCCESS(f"✅ Created superuser: {username} / {password}"))

    async def create_brand(self, name: str, slug: str = None, prefix: str = None) -> Brand:
        """Create a test brand."""
        brand_repo = DjangoBrandRepository()

        # Generate slug if not provided
        if not slug:
            slug = name.lower().replace(" ", "-").replace("_", "-")

        # Generate prefix if not provided
        if not prefix:
            prefix = name.upper()[:4].replace(" ", "").replace("-", "")
            if len(prefix) < 2:
                prefix = "TEST"

        # Check if brand already exists
        # pylint: disable=no-member
        existing = BrandModel.objects.filter(slug=slug).first()
        if existing:
            # pylint: disable=no-member
            self.stdout.write(self.style.WARNING(f"Brand '{name}' already exists (slug: {slug})"))
            return await brand_repo.find_by_id(existing.id)

        # Create brand
        brand = Brand.create(name=name, slug=slug, prefix=prefix)
        brand = await brand_repo.save(brand)

        # pylint: disable=no-member
        self.stdout.write(
            self.style.SUCCESS(f"✅ Created brand: {brand.name} (slug: {slug}, prefix: {prefix})")
        )
        return brand

    def create_api_key(self, brand: Brand) -> ApiKey:
        """Create an API key for the brand."""
        # Check if API key already exists
        # pylint: disable=no-member
        existing = ApiKey.objects.filter(brand_id=brand.id).first()
        if existing:
            # pylint: disable=no-member
            self.stdout.write(
                self.style.WARNING(f"API key already exists for brand '{brand.name}'")
            )
            self.stdout.write(
                self.style.WARNING(
                    "Note: Existing API keys cannot be retrieved. "
                    "Create a new one via Django admin or delete "
                    "the existing one."
                )
            )
            return existing

        # Get BrandModel to use generate_api_key method
        # pylint: disable=no-member
        brand_model = BrandModel.objects.get(id=brand.id)
        api_key = brand_model.generate_api_key(scope="full")
        raw_key = api_key._raw_key  # pylint: disable=protected-access

        # pylint: disable=no-member
        self.stdout.write(self.style.SUCCESS(f"✅ Created API key: {raw_key}"))
        self.stdout.write(
            self.style.WARNING("⚠️  Save this API key - it cannot be retrieved later!")
        )
        return api_key

    async def create_product(self, brand: Brand, name: str) -> Product:
        """Create a test product."""
        product_repo = DjangoProductRepository()

        # Generate slug
        slug = name.lower().replace(" ", "-").replace("_", "-")

        # Check if product already exists
        existing_products = await product_repo.list_by_brand(brand.id)
        for existing in existing_products:
            if existing.slug.value == slug:
                # pylint: disable=no-member
                self.stdout.write(
                    self.style.WARNING(f"Product '{name}' already exists (slug: {slug})")
                )
                return existing

        # Create product
        product = Product.create(brand_id=brand.id, name=name, slug=slug)
        product = await product_repo.save(product)

        # pylint: disable=no-member
        self.stdout.write(self.style.SUCCESS(f"✅ Created product: {product.name} (slug: {slug})"))
        return product

    async def create_test_license(self, brand: Brand, product: Product, customer_email: str):
        """Create a test license key and license."""
        license_key_repo = DjangoLicenseKeyRepository()
        license_repo = DjangoLicenseRepository()

        # Create license key (generates key automatically)
        license_key = LicenseKey.create(
            brand_id=brand.id,
            brand_prefix=brand.prefix,
            customer_email=customer_email,
        )
        license_key = await license_key_repo.save(license_key)

        # Create license
        from datetime import datetime, timedelta, timezone

        license_entity = License.create(
            license_key_id=license_key.id,
            product_id=product.id,
            seat_limit=5,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )
        license_entity = await license_repo.save(license_entity)

        self.stdout.write(
            # pylint: disable=no-member
            self.style.SUCCESS(f"✅ Created license key and license for {customer_email}")
        )
        return license_key

    def print_summary(
        self,
        brand: Brand,
        api_key: ApiKey,
        product: Product,
        license_key: LicenseKey = None,
    ):
        """Print summary of created test data."""
        # pylint: disable=no-member
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("📋 Test Data Summary"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        self.stdout.write("\n🔐 Superuser:")
        self.stdout.write("   Username: admin")
        self.stdout.write("   Password: admin")
        self.stdout.write("   URL: http://localhost:8000/admin/")

        self.stdout.write("\n🏢 Brand:")
        self.stdout.write(f"   Name: {brand.name}")
        self.stdout.write(f"   Slug: {brand.slug.value}")
        self.stdout.write(f"   Prefix: {brand.prefix}")
        self.stdout.write(f"   ID: {brand.id}")

        raw_key = getattr(api_key, "_raw_key", None)
        if raw_key:
            self.stdout.write("\n🔑 API Key:")
            self.stdout.write(f"   {raw_key}")
            # pylint: disable=no-member
            self.stdout.write(self.style.WARNING("   ⚠️  Save this - it cannot be retrieved later!"))
        else:
            self.stdout.write("\n🔑 API Key:")
            self.stdout.write(
                # pylint: disable=no-member
                self.style.WARNING("   API key already exists. Create a new one via Django admin.")
            )

        self.stdout.write("\n📦 Product:")
        self.stdout.write(f"   Name: {product.name}")
        self.stdout.write(f"   Slug: {product.slug.value}")
        self.stdout.write(f"   ID: {product.id}")

        if license_key:
            self.stdout.write("\n🔑 License Key:")
            self.stdout.write(f"   Key: {license_key.key}")
            self.stdout.write(f"   Customer: {license_key.customer_email.value}")

        self.stdout.write("\n📝 Example API Request:")
        if raw_key:
            # pylint: disable=no-member
            self.stdout.write(
                "   curl -X POST http://localhost:8000/api/v1/brand/licenses/provision \\"
            )
            self.stdout.write(f'     -H "X-API-Key: {raw_key}" \\')
            self.stdout.write('     -H "Content-Type: application/json" \\')
            self.stdout.write(
                f'     -d \'{{"customer_email": "customer@example.com", '
                f'"products": ["{product.id}"]}}\''
            )

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60 + "\n"))
