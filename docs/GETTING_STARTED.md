# Getting Started Guide

This guide will help you get started with the Centralized License Service.

## Getting API Keys

### Creating a Brand and API Key

API keys are generated when you create a brand. Here's how to do it:

#### Option 1: Using Django Admin

1. Start the application:
   ```bash
   docker-compose up
   ```

2. Access Django Admin:
   - URL: http://localhost:8000/admin
   - Create a superuser if needed:
     ```bash
     docker-compose exec app python manage.py createsuperuser
     ```

3. Create a Brand:
   - Go to "Brands" → "Add Brand"
   - Fill in:
     - Name: e.g., "RankMath"
     - Slug: e.g., "rankmath"
     - Prefix: e.g., "RM" (2-10 characters, alphanumeric)
   - Save

4. Generate API Key:
   - Go to "Api Keys" → "Add Api Key"
   - Select the brand
   - Choose scope: "Full Access" or "Read Only"
   - Save
   - **Important**: Copy the `_raw_key` value immediately - it's only shown once!

#### Option 2: Using Django Shell

```bash
docker-compose exec app python manage.py shell
```

```python
from brands.infrastructure.models import Brand, ApiKey

# Create a brand
brand = Brand.objects.create(
    name="RankMath",
    slug="rankmath",
    prefix="RM"
)

# Generate an API key
api_key = brand.generate_api_key(scope="full")
print(f"API Key: {api_key._raw_key}")
print(f"Key Prefix: {api_key.key_prefix}")
```

#### Option 3: Using Django Management Command

Create a management command (optional):

```python
# core/management/commands/create_api_key.py
from django.core.management.base import BaseCommand
from brands.infrastructure.models import Brand

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('brand_slug', type=str)
        parser.add_argument('--scope', default='full', choices=['full', 'read'])

    def handle(self, *args, **options):
        brand = Brand.objects.get(slug=options['brand_slug'])
        api_key = brand.generate_api_key(scope=options['scope'])
        self.stdout.write(
            self.style.SUCCESS(f'API Key created: {api_key._raw_key}')
        )
```

Usage:
```bash
docker-compose exec app python manage.py create_api_key rankmath --scope full
```

## Using API Keys

### Brand API (Requires API Key)

All brand API endpoints require authentication via API key:

```bash
# Set your API key
export API_KEY="your-api-key-here"

# Provision a license
curl -X POST http://localhost:8000/api/v1/brand/licenses/provision \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "customer@example.com",
    "product_slug": "rankmath-pro",
    "seat_limit": 5,
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

### Product API (Requires License Key)

Product API endpoints use license keys (not API keys):

```bash
# Activate a license
curl -X POST http://localhost:8000/api/v1/product/licenses/activate \
  -H "Authorization: Bearer LICENSE-KEY-HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_identifier": "https://example.com",
    "instance_type": "url"
  }'
```

## Sorting and Filtering

### List Licenses by Email

The list licenses endpoint supports sorting:

```bash
curl -X GET "http://localhost:8000/api/v1/brand/licenses?email=customer@example.com&sort=created_at&order=desc" \
  -H "X-API-Key: $API_KEY"
```

**Query Parameters:**
- `email` (required): Customer email address
- `sort` (optional): Field to sort by (default: `created_at`)
  - Available fields: `created_at`, `status`, `expires_at`
- `order` (optional): Sort order (default: `desc`)
  - Values: `asc` or `desc`

**Example Response:**
```json
{
  "licenses": [
    {
      "id": "uuid",
      "license_key": "RM-XXXX-XXXX-XXXX-XXXX",
      "product": {
        "id": "uuid",
        "name": "RankMath Pro",
        "slug": "rankmath-pro"
      },
      "status": "valid",
      "seat_limit": 5,
      "seats_used": 2,
      "expires_at": "2025-12-31T23:59:59Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Get License Status

```bash
curl -X GET "http://localhost:8000/api/v1/product/licenses/status?license_key=RM-XXXX-XXXX-XXXX-XXXX" \
  -H "Authorization: Bearer RM-XXXX-XXXX-XXXX-XXXX"
```

## Rate Limiting

Rate limits are configured per API key. Check response headers:

```bash
curl -I -X GET "http://localhost:8000/api/v1/brand/licenses?email=test@example.com" \
  -H "X-API-Key: $API_KEY"
```

**Response Headers:**
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Unix timestamp when limit resets
- `Retry-After`: Seconds to wait before retrying (if limited)

## Webhooks

### Configuring Webhooks

Webhooks are configured per brand via Django Admin or API:

```python
from brands.infrastructure.models import Brand, WebhookConfig

brand = Brand.objects.get(slug="rankmath")

webhook = WebhookConfig.objects.create(
    brand=brand,
    url="https://your-server.com/webhooks/license",
    secret="your-webhook-secret",
    events=["license.provisioned", "license.renewed", "license.suspended"],
    is_active=True,
    max_retries=3,
    timeout_seconds=10
)
```

### Webhook Signature Verification

Webhooks include an HMAC SHA-256 signature:

```python
import hmac
import hashlib

def verify_webhook(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Example Workflow

1. **Create Brand and API Key:**
   ```bash
   # Using Django shell
   docker-compose exec app python manage.py shell
   ```
   ```python
   from brands.infrastructure.models import Brand
   brand = Brand.objects.create(name="RankMath", slug="rankmath", prefix="RM")
   api_key = brand.generate_api_key()
   print(f"API Key: {api_key._raw_key}")
   ```

2. **Create Product:**
   ```python
   from products.infrastructure.models import Product
   product = Product.objects.create(
       brand=brand,
       name="RankMath Pro",
       slug="rankmath-pro"
   )
   ```

3. **Provision License:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/brand/licenses/provision \
     -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "customer_email": "customer@example.com",
       "product_slug": "rankmath-pro",
       "seat_limit": 5
     }'
   ```

4. **Activate License:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/product/licenses/activate \
     -H "Authorization: Bearer LICENSE-KEY-FROM-PROVISION" \
     -H "Content-Type: application/json" \
     -d '{
       "instance_identifier": "https://example.com",
       "instance_type": "url"
     }'
   ```

## Troubleshooting

### API Key Not Working

1. Check the key is correct (copy-paste, no extra spaces)
2. Verify the key hasn't expired
3. Check the key scope (full vs read-only)
4. Ensure you're using the correct header: `X-API-Key` or `Authorization: Bearer`

### Rate Limit Exceeded

- Check `X-RateLimit-Remaining` header
- Wait until `X-RateLimit-Reset` time
- Contact admin to increase rate limit for your API key

### Webhook Not Receiving Events

1. Check webhook is active (`is_active=True`)
2. Verify webhook subscribes to the event type
3. Check webhook URL is accessible
4. Review Celery worker logs for delivery errors

## Next Steps

- See [API.md](API.md) for complete API documentation
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system architecture
- See [OBSERVABILITY.md](OBSERVABILITY.md) for monitoring setup

