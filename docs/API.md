# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

### Brand APIs

Brand APIs require authentication via API key. Include the API key in the request
header:

```http
X-API-Key: your-api-key-here
```

Or via Authorization header:

```http
Authorization: Bearer your-api-key-here
```

### Product APIs

Product APIs authenticate using license keys provided in the request body.

## Brand API

### Provision License

Create a new license key and associated licenses for a customer.

**Endpoint**: `POST /brand/licenses/provision`

**Headers**:
- `X-API-Key`: Your brand API key
- `Content-Type`: application/json

**Request Body**:

```json
{
  "customer_email": "customer@example.com",
  "products": ["product-uuid-1", "product-uuid-2"],
  "expiration_date": "2025-12-31T23:59:59Z",
  "max_seats": 5,
  "idempotency_key": "optional-idempotency-key"
}
```

**Fields**:
- `customer_email` (required): Customer email address
- `products` (required): Array of product UUIDs
- `expiration_date` (optional): ISO 8601 expiration date
- `max_seats` (optional): Maximum concurrent activations (default: 1)
- `idempotency_key` (optional): Idempotency key for duplicate prevention

**Response** (201 Created):

```json
{
  "license_key": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "key": "BRAND-XXXX-XXXX-XXXX-XXXX",
    "customer_email": "customer@example.com",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "licenses": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "product_id": "product-uuid-1",
      "status": "valid",
      "seat_limit": 5,
      "expires_at": "2025-12-31T23:59:59Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: Brand or product not found
- `409 Conflict`: Duplicate idempotency key

### Renew License

Extend a license's expiration date.

**Endpoint**: `POST /brand/licenses/{license_id}/renew`

**Headers**:
- `X-API-Key`: Your brand API key
- `Content-Type`: application/json

**Request Body**:

```json
{
  "expiration_date": "2026-12-31T23:59:59Z"
}
```

**Response** (200 OK):

```json
{
  "id": "license-uuid",
  "status": "valid",
  "expires_at": "2026-12-31T23:59:59Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid expiration date
- `401 Unauthorized`: Invalid API key
- `404 Not Found`: License not found

### Suspend License

Temporarily disable a license. Suspended licenses cannot be activated.

**Endpoint**: `POST /brand/licenses/{license_id}/suspend`

**Headers**:
- `X-API-Key`: Your brand API key

**Response** (200 OK):

```json
{
  "id": "license-uuid",
  "status": "suspended",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Resume License

Re-enable a suspended license.

**Endpoint**: `POST /brand/licenses/{license_id}/resume`

**Headers**:
- `X-API-Key`: Your brand API key

**Response** (200 OK):

```json
{
  "id": "license-uuid",
  "status": "valid",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Cancel License

Permanently cancel a license. Cancelled licenses cannot be reactivated.

**Endpoint**: `POST /brand/licenses/{license_id}/cancel`

**Headers**:
- `X-API-Key`: Your brand API key

**Response** (200 OK):

```json
{
  "id": "license-uuid",
  "status": "cancelled",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### List Licenses by Email

Query all licenses for a customer by email address.

**Endpoint**: `GET /brand/licenses?email={email}`

**Headers**:
- `X-API-Key`: Your brand API key

**Query Parameters**:
- `email` (required): Customer email address

**Response** (200 OK):

```json
{
  "licenses": [
    {
      "id": "license-uuid",
      "license_key": {
        "id": "key-uuid",
        "key": "BRAND-XXXX-XXXX-XXXX-XXXX",
        "customer_email": "customer@example.com"
      },
      "product": {
        "id": "product-uuid",
        "name": "Product Name",
        "slug": "product-slug"
      },
      "status": "valid",
      "seat_limit": 5,
      "seats_used": 2,
      "seats_remaining": 3,
      "expires_at": "2025-12-31T23:59:59Z"
    }
  ]
}
```

## Product API

### Activate License

Activate a license on a specific instance (URL, hostname, or machine ID).

**Endpoint**: `POST /product/licenses/activate`

**Headers**:
- `Content-Type`: application/json

**Request Body**:

```json
{
  "license_key": "BRAND-XXXX-XXXX-XXXX-XXXX",
  "instance_identifier": "https://example.com",
  "instance_type": "url"
}
```

**Fields**:
- `license_key` (required): License key string
- `instance_identifier` (required): Instance identifier (URL, hostname, or machine ID)
- `instance_type` (required): One of `url`, `hostname`, `machine_id`

**Response** (201 Created):

```json
{
  "activation_id": "activation-uuid",
  "status": "active",
  "seats_used": 1,
  "seats_remaining": 4,
  "activated_at": "2024-01-01T00:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request data
- `404 Not Found`: License key not found or invalid
- `409 Conflict`: License already activated on this instance
- `422 Unprocessable Entity`: License invalid, expired, suspended, or seat limit exceeded

### Check License Status

Verify license validity and seat availability for a specific instance.

**Endpoint**: `GET /product/licenses/check?license_key={key}&instance_identifier={identifier}`

**Query Parameters**:
- `license_key` (required): License key string
- `instance_identifier` (required): Instance identifier

**Response** (200 OK):

```json
{
  "is_valid": true,
  "license": {
    "id": "license-uuid",
    "status": "valid",
    "seat_limit": 5,
    "seats_used": 2,
    "seats_remaining": 3,
    "expires_at": "2025-12-31T23:59:59Z"
  },
  "is_activated": true,
  "activation": {
    "id": "activation-uuid",
    "activated_at": "2024-01-01T00:00:00Z",
    "last_checked_at": "2024-01-01T12:00:00Z"
  }
}
```

**Error Responses**:
- `404 Not Found`: License key not found
- `422 Unprocessable Entity`: License invalid, expired, or suspended

### Deactivate Seat

Release a seat for reuse. This deactivates the license on a specific instance.

**Endpoint**: `POST /product/licenses/deactivate`

**Headers**:
- `Content-Type`: application/json

**Request Body**:

```json
{
  "license_key": "BRAND-XXXX-XXXX-XXXX-XXXX",
  "instance_identifier": "https://example.com"
}
```

**Response** (200 OK):

```json
{
  "status": "deactivated",
  "seats_used": 0,
  "seats_remaining": 5
}
```

**Error Responses**:
- `404 Not Found`: License key or activation not found

## Health Check Endpoints

### Basic Health Check

**Endpoint**: `GET /health`

**Response** (200 OK):

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Database Health Check

**Endpoint**: `GET /health/db`

**Response** (200 OK):

```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Cache Health Check

**Endpoint**: `GET /health/cache`

**Response** (200 OK):

```json
{
  "status": "healthy",
  "cache": "connected"
}
```

### Readiness Check

**Endpoint**: `GET /ready`

**Response** (200 OK):

```json
{
  "status": "ready",
  "database": "connected",
  "cache": "connected"
}
```

## Error Responses

All error responses follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `AUTHENTICATION_ERROR`: Authentication failed
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `CONFLICT`: Resource conflict (e.g., duplicate)
- `UNPROCESSABLE_ENTITY`: Business rule violation

## Rate Limiting

Rate limiting may be applied to prevent abuse. Check response headers:

- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time (Unix timestamp)

## Idempotency

Brand API write operations support idempotency keys. Include
`idempotency_key` in the request to ensure idempotent behavior:

- Same key within 24 hours returns cached response
- Prevents duplicate operations
- Useful for retries

## Pagination

List endpoints may support pagination in the future. Check response for:

- `page`: Current page number
- `page_size`: Items per page
- `total`: Total number of items
- `next`: URL for next page
- `previous`: URL for previous page

