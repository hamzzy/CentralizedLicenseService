# Architecture & Design Documentation

## Table of Contents

1. [Overview](#overview)
2. [Multi-Tenancy Architecture](#multi-tenancy-architecture)
3. [Integration Points](#integration-points)
4. [Technical Architecture](#technical-architecture)
5. [Data Model](#data-model)
6. [Observability & Operability](#observability--operability)
7. [Error Handling & Resilience](#error-handling--resilience)

---

## Overview

The Centralized License Service is a multi-tenant SaaS platform that provides centralized license management for multiple brands and their products. It enables brands to provision and manage licenses while allowing end-user products to activate and validate licenses.

### Key Design Principles

- **Multi-Tenancy**: Complete data isolation per brand using row-level security
- **Hexagonal Architecture**: Clean separation between domain, application, and infrastructure
- **CQRS**: Separate command and query models for optimal performance
- **Event-Driven**: Domain events for decoupled module communication
- **Observable**: Comprehensive logging, metrics, and tracing
- **Resilient**: Graceful error handling and circuit breakers

---

## Multi-Tenancy Architecture

### Design Model

The system implements **row-level multi-tenancy** where all data is logically partitioned by brand (tenant). Each brand has complete data isolation while sharing the same database schema.

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Brand A    │  │   Brand B    │  │   Brand C    │ │
│  │  (Tenant 1)  │  │  (Tenant 2)  │  │  (Tenant 3)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Shared Database (PostgreSQL)                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  All tables include brand_id for isolation       │  │
│  │  - brands (tenant metadata)                       │  │
│  │  - products (brand_id FK)                        │  │
│  │  - license_keys (brand_id FK)                     │  │
│  │  - licenses (brand_id via license_key)           │  │
│  │  - activations (brand_id via license)            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Implementation Strategy

#### 1. Tenant Identification

**API Key Authentication**:
- Each brand has one or more API keys
- API keys are SHA-256 hashed and stored securely
- Tenant context is extracted from API key in middleware

```python
# TenantMiddleware extracts brand_id from API key
api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
api_key_obj = ApiKey.objects.filter(key_hash=api_key_hash).first()
tenant_id = api_key_obj.brand.id  # Sets tenant context
```

#### 2. Context Propagation

**Context Variables** (Python `contextvars`):
- Tenant ID is stored in thread-local context
- Automatically available throughout request lifecycle
- Cleared after request completion

```python
tenant_context: ContextVar[Optional[UUID]] = contextvars.ContextVar("tenant_id")
tenant_context.set(brand_id)  # Set at request start
tenant_id = tenant_context.get()  # Access anywhere in request
```

#### 3. Data Isolation

**Repository Pattern**:
- All repository methods automatically filter by tenant
- Enforced at application layer, not database level
- Prevents accidental cross-tenant data access

```python
class DjangoLicenseRepository:
    def find_by_id(self, license_id: UUID) -> Optional[License]:
        tenant_id = get_current_tenant_id()
        # Automatically filters by tenant_id
        return self._to_domain(
            LicenseModel.objects.filter(id=license_id, brand_id=tenant_id).first()
        )
```

#### 4. Product Isolation

**Brand-Product Relationship**:
- Products belong to a specific brand
- Product slugs are unique within a brand (not globally)
- License keys are brand-specific with unique prefixes

```
Brand: RankMath
  ├── Product: RankMath Pro
  ├── Product: Content AI
  └── Product: SEO Analyzer

Brand: WP Rocket
  ├── Product: WP Rocket Pro
  └── Product: Imagify
```

### Security Considerations

1. **API Key Security**:
   - Keys are never stored in plain text
   - SHA-256 hashing with constant-time comparison
   - Keys can be revoked or expired
   - Rate limiting per API key

2. **Data Leakage Prevention**:
   - All queries must include tenant filter
   - Repository pattern enforces isolation
   - Middleware validates tenant context
   - No cross-tenant queries possible

3. **License Key Security**:
   - License keys are brand-prefixed (e.g., `RM-XXXX-XXXX-XXXX-XXXX`)
   - Keys are hashed in database
   - Validation includes brand verification

---

## Integration Points

### Brand System Integration

Brand systems (e.g., RankMath, WP Rocket) integrate via **Brand APIs** to manage licenses for their customers.

#### Authentication

```http
X-API-Key: <brand-api-key>
```

Or:

```http
Authorization: Bearer <brand-api-key>
```

#### API Endpoints

**Base URL**: `https://license-service.example.com/api/v1/brand`

##### 1. Provision License

Create a new license key and licenses for a customer.

```http
POST /licenses/provision
Content-Type: application/json
X-API-Key: <brand-api-key>

{
  "customer_email": "customer@example.com",
  "products": ["product-uuid-1", "product-uuid-2"],
  "expiration_date": "2025-12-31T23:59:59Z",
  "max_seats": 5,
  "idempotency_key": "unique-idempotency-key"
}
```

**Response**:
```json
{
  "license_key": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "key": "RM-XXXX-XXXX-XXXX-XXXX",
    "customer_email": "customer@example.com",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "licenses": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "product_id": "product-uuid-1",
      "product_name": "RankMath Pro",
      "status": "valid",
      "seat_limit": 5,
      "seats_used": 0,
      "seats_remaining": 5,
      "expires_at": "2025-12-31T23:59:59Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Use Cases**:
- New customer purchase
- License upgrade
- License renewal with new products

##### 2. License Lifecycle Management

```http
# Renew License
POST /licenses/{license_id}/renew
{
  "expiration_date": "2026-12-31T23:59:59Z"
}

# Suspend License
POST /licenses/{license_id}/suspend

# Resume License
POST /licenses/{license_id}/resume

# Cancel License
POST /licenses/{license_id}/cancel
```

##### 3. Query Licenses

```http
GET /licenses?email=customer@example.com
```

Returns all licenses for a customer across all products.

#### Integration Flow

```
Brand System (e.g., WooCommerce)
    ↓
1. Customer purchases product
    ↓
2. Brand system calls POST /licenses/provision
    ↓
3. License Service creates license key + licenses
    ↓
4. Brand system receives license key
    ↓
5. Brand system sends license key to customer
    ↓
6. Customer enters license key in product
    ↓
7. Product activates license (see Product Integration)
```

### End-User Product Integration

End-user products (WordPress plugins, SaaS apps) integrate via **Product APIs** to activate and validate licenses.

#### Authentication

Product APIs authenticate using **license keys** provided in the request body. No API key required.

#### API Endpoints

**Base URL**: `https://license-service.example.com/api/v1/product`

##### 1. Activate License

Activate a license on a specific instance (e.g., WordPress site URL).

```http
POST /licenses/activate
Content-Type: application/json

{
  "license_key": "RM-XXXX-XXXX-XXXX-XXXX",
  "instance_identifier": "https://example.com",
  "instance_type": "url"
}
```

**Response**:
```json
{
  "activation_id": "770e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "seats_used": 1,
  "seats_remaining": 4
}
```

**Error Responses**:
- `400 Bad Request`: Invalid license key or already activated
- `403 Forbidden`: License expired, suspended, or cancelled
- `409 Conflict`: Seat limit exceeded

##### 2. Check License Status

Verify license validity and seat availability.

```http
GET /licenses/check?license_key=RM-XXXX-XXXX-XXXX-XXXX&instance_identifier=https://example.com
```

**Response**:
```json
{
  "license_key": "RM-XXXX-XXXX-XXXX-XXXX",
  "status": "valid",
  "is_valid": true,
  "is_activated": true,
  "licenses": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "product_id": "product-uuid-1",
      "product_name": "RankMath Pro",
      "status": "valid",
      "seat_limit": 5,
      "seats_used": 1,
      "seats_remaining": 4,
      "expires_at": "2025-12-31T23:59:59Z"
    }
  ],
  "total_seats_used": 1,
  "total_seats_available": 4
}
```

##### 3. Deactivate Seat

Release a seat when product is deactivated or uninstalled.

```http
POST /licenses/deactivate
Content-Type: application/json

{
  "license_key": "RM-XXXX-XXXX-XXXX-XXXX",
  "instance_identifier": "https://example.com"
}
```

#### Integration Flow

```
End-User Product (WordPress Plugin)
    ↓
1. User enters license key in plugin settings
    ↓
2. Plugin calls POST /licenses/activate
    ↓
3. License Service validates and activates
    ↓
4. Plugin receives activation confirmation
    ↓
5. Plugin enables premium features
    ↓
6. Plugin periodically calls GET /licenses/check
    ↓
7. On deactivation, plugin calls POST /licenses/deactivate
```

#### Best Practices for Product Integration

1. **Activation on First Use**: Activate license when user first enables premium features
2. **Periodic Validation**: Check license status daily or weekly
3. **Graceful Degradation**: Handle license expiration gracefully
4. **Seat Management**: Deactivate when plugin is deactivated
5. **Error Handling**: Show user-friendly error messages

---

## Technical Architecture

### Architecture Pattern

The system follows a **Modular Monolith** with **Hexagonal Architecture** and **Strategic CQRS**.

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (REST)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Brand APIs   │  │ Product APIs │  │ Health APIs  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer (CQRS)                   │
│  ┌──────────────┐              ┌──────────────┐            │
│  │  Commands    │              │   Queries   │            │
│  │  - Provision │              │  - GetStatus│            │
│  │  - Renew     │              │  - List     │            │
│  │  - Activate  │              │             │            │
│  └──────────────┘              └──────────────┘            │
│         ↓                              ↓                    │
│  ┌──────────────┐              ┌──────────────┐            │
│  │   Handlers   │              │   Handlers   │            │
│  └──────────────┘              └──────────────┘            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer (Pure Logic)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Entities   │  │   Services   │  │    Events    │     │
│  │  - License   │  │  - Validator │  │ - Provisioned│    │
│  │  - Brand     │  │  - Generator │  │ - Activated  │     │
│  │  - Product   │  │  - Manager   │  │ - Renewed    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer (Adapters)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Repositories│  │    Cache     │  │  Event Bus   │     │
│  │  - Django ORM│  │  - Redis     │  │  - RabbitMQ  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    External Services                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PostgreSQL  │  │    Redis     │  │  Observability│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Module Structure

#### Brands Module

**Purpose**: Manage brands and products (tenant metadata)

**Domain**:
- `Brand`: Tenant entity with name, slug, prefix
- `Product`: Product entity belonging to a brand

**Application**:
- Brand and product management (CRUD operations)

**Infrastructure**:
- `DjangoBrandRepository`: Brand persistence
- `DjangoProductRepository`: Product persistence

#### Licenses Module

**Purpose**: Manage license keys and licenses

**Domain**:
- `LicenseKey`: Customer-facing license key (e.g., `RM-XXXX-XXXX-XXXX-XXXX`)
- `License`: Product-specific license grant with status, seats, expiration

**Domain Services**:
- `LicenseKeyGenerator`: Generates secure, brand-prefixed keys
- `LicenseValidator`: Validates license state and expiration
- `LicenseLifecycleManager`: Manages state transitions

**Application**:
- **Commands**: Provision, Renew, Suspend, Resume, Cancel
- **Queries**: GetStatus, ListByEmail
- **Handlers**: Command and query handlers

**Infrastructure**:
- `DjangoLicenseKeyRepository`: License key persistence
- `DjangoLicenseRepository`: License persistence

#### Activations Module

**Purpose**: Manage license activations and seat limits

**Domain**:
- `Activation`: Represents an active license instance
  - Links license to instance identifier (URL, domain, etc.)
  - Tracks activation timestamp

**Domain Services**:
- `SeatManager`: Manages seat limits and availability
  - Checks seat availability
  - Enforces seat limits
  - Handles seat deactivation

**Application**:
- **Commands**: ActivateLicense, DeactivateSeat
- **Queries**: GetActivationStatus
- **Handlers**: Activation handlers

**Infrastructure**:
- `DjangoActivationRepository`: Activation persistence

#### Core Module

**Purpose**: Shared infrastructure and domain primitives

**Components**:
- **Domain Events**: `DomainEvent`, `EventBus`
- **Value Objects**: `Email`, `LicenseStatus`, `InstanceType`
- **Exceptions**: Domain-specific exceptions
- **Middleware**: Tenant, Auth, Observability, Tracing, Metrics
- **Infrastructure**: Cache adapters, Event bus implementations

### Data Flow

#### Write Flow (Command)

```
1. API Request (REST)
   ↓
2. Middleware Stack
   - TenantMiddleware (extract brand_id)
   - AuthMiddleware (validate API key)
   - TracingMiddleware (create span)
   - MetricsMiddleware (track metrics)
   ↓
3. View (Async)
   - Validate request
   - Create command object
   ↓
4. Command Handler
   - Load domain entities
   - Execute business logic
   - Persist changes
   ↓
5. Domain Layer
   - Entity methods
   - Domain services
   - Domain events
   ↓
6. Repository (Port)
   - Convert domain to ORM
   - Save to database
   ↓
7. Event Bus
   - Publish domain events
   - Trigger event handlers
   ↓
8. Response
   - Return DTO
   - Set status code
```

#### Read Flow (Query)

```
1. API Request (REST)
   ↓
2. Middleware Stack
   ↓
3. View (Async)
   - Create query object
   ↓
4. Query Handler
   - Check cache first
   - Load from repository
   - Convert to DTO
   ↓
5. Repository (Port)
   - Query database
   - Filter by tenant
   - Convert to domain
   ↓
6. Cache (Optional)
   - Store result
   - Set TTL
   ↓
7. Response
   - Return DTO
```

### Event-Driven Architecture

#### Domain Events

Events represent significant business occurrences:

- `BrandCreated`
- `ProductCreated`
- `LicenseKeyCreated`
- `LicenseProvisioned`
- `LicenseRenewed`
- `LicenseSuspended`
- `LicenseResumed`
- `LicenseCancelled`
- `LicenseActivated`
- `SeatDeactivated`

#### Event Bus

**Current Implementation**: In-memory event bus (`InMemoryEventBus`)

**Future**: RabbitMQ for distributed event processing

**Event Handlers**:
- `AuditLogEventHandler`: Logs all license operations
- `LicenseCacheInvalidationHandler`: Invalidates cache on license changes
- `MetricsEventHandler`: Updates Prometheus metrics

---

## Data Model

### Entity Relationship Diagram

```
┌─────────────┐
│   Brand     │
│─────────────│
│ id (PK)     │
│ name        │
│ slug        │
│ prefix      │
└─────────────┘
      │
      │ 1:N
      │
      ├─────────────────┐
      │                 │
┌─────────────┐  ┌─────────────┐
│  Product    │  │  ApiKey     │
│─────────────│  │─────────────│
│ id (PK)     │  │ id (PK)     │
│ brand_id(FK)│  │ brand_id(FK)│
│ name        │  │ key_hash    │
│ slug        │  │ expires_at  │
└─────────────┘  └─────────────┘
      │
      │ 1:N
      │
┌─────────────┐
│ LicenseKey  │
│─────────────│
│ id (PK)     │
│ brand_id(FK)│
│ key_hash    │
│ key (plain) │
│ customer_email│
└─────────────┘
      │
      │ 1:N
      │
┌─────────────┐
│  License    │
│─────────────│
│ id (PK)     │
│ license_key_id(FK)│
│ product_id(FK)│
│ status      │
│ seat_limit  │
│ expires_at  │
└─────────────┘
      │
      │ 1:N
      │
┌─────────────┐
│ Activation  │
│─────────────│
│ id (PK)     │
│ license_id(FK)│
│ instance_identifier│
│ instance_type│
│ activated_at│
└─────────────┘
```

### Database Schema

#### brands

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Brand identifier |
| name | VARCHAR(255) | Brand display name |
| slug | VARCHAR(100) | URL-safe identifier (unique) |
| prefix | VARCHAR(10) | License key prefix (unique) |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Indexes**: `slug`, `prefix`

#### products

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Product identifier |
| brand_id | UUID (FK) | Brand reference |
| name | VARCHAR(255) | Product display name |
| slug | VARCHAR(100) | URL-safe identifier |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Indexes**: `(brand_id, slug)` (unique), `brand_id`

#### api_keys

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | API key identifier |
| brand_id | UUID (FK) | Brand reference |
| key_hash | VARCHAR(64) | SHA-256 hash of API key |
| scope | VARCHAR(50) | Key scope (full, read-only) |
| expires_at | TIMESTAMP | Expiration date (nullable) |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `key_hash` (unique), `brand_id`

#### license_keys

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | License key identifier |
| brand_id | UUID (FK) | Brand reference |
| key | VARCHAR(255) | Plain license key |
| key_hash | VARCHAR(64) | SHA-256 hash of key |
| customer_email | VARCHAR(255) | Customer email |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `key_hash` (unique), `brand_id`, `customer_email`

#### licenses

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | License identifier |
| license_key_id | UUID (FK) | License key reference |
| product_id | UUID (FK) | Product reference |
| status | VARCHAR(20) | Status (valid, expired, suspended, cancelled) |
| seat_limit | INTEGER | Maximum concurrent activations |
| expires_at | TIMESTAMP | Expiration date (nullable) |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Indexes**: `license_key_id`, `product_id`, `status`, `expires_at`

#### activations

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Activation identifier |
| license_id | UUID (FK) | License reference |
| instance_identifier | VARCHAR(500) | Instance identifier (URL, domain, etc.) |
| instance_type | VARCHAR(50) | Instance type (url, domain, etc.) |
| activated_at | TIMESTAMP | Activation timestamp |

**Indexes**: `license_id`, `(license_id, instance_identifier)` (unique)

#### audit_logs

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Audit log identifier |
| brand_id | UUID (FK) | Brand reference |
| action | VARCHAR(50) | Action type |
| entity_type | VARCHAR(50) | Entity type |
| entity_id | UUID | Entity identifier |
| user_id | UUID | User identifier (nullable) |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `brand_id`, `action`, `entity_type`, `created_at`

#### idempotency_keys

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Idempotency key identifier |
| brand_id | UUID (FK) | Brand reference |
| key | VARCHAR(255) | Idempotency key value |
| response | JSONB | Cached response |
| expires_at | TIMESTAMP | Expiration timestamp |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes**: `(brand_id, key)` (unique), `expires_at`

### Data Isolation Strategy

All tables include `brand_id` either directly or via foreign key relationships:

- **Direct**: `brands`, `api_keys`, `license_keys`
- **Via FK**: `products.brand_id`, `licenses` (via `license_key.brand_id`), `activations` (via `license.license_key.brand_id`)

All repository queries automatically filter by `brand_id` from tenant context.

---

## Observability & Operability

### Observability Stack

```
┌─────────────────────────────────────────────────────────┐
│                  Application (Django)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Logging    │  │   Metrics    │  │   Tracing    │ │
│  │  (Structured)│  │ (Prometheus) │  │ (OpenTelemetry)││
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│     Loki     │  │  Prometheus  │  │    Tempo     │
│  (Log Agg)   │  │  (Metrics)   │  │  (Traces)    │
└──────────────┘  └──────────────┘  └──────────────┘
         ↓                    ↓                    ↓
┌─────────────────────────────────────────────────────────┐
│                    Grafana                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Log Panels  │  │ Metric Panels│  │ Trace Panels │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Logging

#### Structured Logging

All logs are structured JSON with the following fields:

```json
{
  "asctime": "2024-01-01T00:00:00Z",
  "name": "core.middleware.observability",
  "levelname": "INFO",
  "message": "Request completed successfully",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "request_status": "success",
  "method": "POST",
  "path": "/api/v1/brand/licenses/provision",
  "status_code": 201,
  "duration_ms": 45.2,
  "brand_id": "brand-uuid",
  "response_size": 1024
}
```

#### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages (requests, responses)
- **WARNING**: Warning messages (deprecated features, recoverable errors)
- **ERROR**: Error messages (exceptions, failures)
- **CRITICAL**: Critical errors (system failures)

#### Log Aggregation

- **Loki**: Collects logs from application via Promtail
- **LogQL**: Query language for log analysis
- **Grafana**: Visualization and alerting

### Metrics

#### Prometheus Metrics

**HTTP Metrics**:
- `http_requests_total`: Total HTTP requests by method, endpoint, status_code
- `http_request_duration_seconds`: Request duration histogram

**Business Metrics**:
- `licenses_provisioned_total`: Total licenses provisioned by brand, product
- `licenses_activated_total`: Total licenses activated
- `licenses_renewed_total`: Total licenses renewed
- `licenses_suspended_total`: Total licenses suspended
- `licenses_cancelled_total`: Total licenses cancelled
- `active_licenses`: Current active licenses by brand, status
- `active_activations`: Current active activations by brand

**Infrastructure Metrics**:
- `db_query_duration_seconds`: Database query duration
- `cache_hits_total`: Cache hits
- `cache_misses_total`: Cache misses
- `errors_total`: Total errors by type, endpoint

**Metrics Endpoint**: `http://localhost:9090/metrics`

### Distributed Tracing

#### OpenTelemetry Integration

- **Auto-instrumentation**: Django, PostgreSQL, Redis
- **Manual spans**: Custom business operations
- **Trace context**: Propagated via headers
- **Span attributes**: Request/response details, errors, status

#### Trace Attributes

Each span includes:
- HTTP method, URL, status code
- Request/response body (sanitized)
- Error details (code, message, stack trace)
- Request status (success, client_error, server_error, exception)
- Correlation ID
- Tenant context (brand_id)
- Duration

#### Trace Backend

- **Tempo**: Distributed tracing backend
- **OTLP**: OpenTelemetry Protocol for trace export
- **Grafana**: Trace visualization and correlation with logs

### Health Checks

#### Endpoints

- `GET /health`: Basic health check
- `GET /health/db`: Database connectivity check
- `GET /health/cache`: Cache connectivity check
- `GET /ready`: Full readiness check (all dependencies)

#### Response Format

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "checks": {
    "database": "ok",
    "cache": "ok"
  }
}
```

### Monitoring Dashboards

#### Grafana Dashboards

**License Service Overview**:
- Request rate and latency
- License operations (provision, activate, renew)
- Error rates
- Active licenses and activations

**HTTP Performance**:
- Request duration percentiles (p50, p95, p99)
- Status code distribution
- Endpoint performance

**License Operations**:
- Provision rate
- Activation rate
- Renewal rate
- Suspension/cancellation rate

**Error Analysis**:
- Error rate by type
- Error rate by endpoint
- Error trends

**Traces**:
- Recent traces
- Error traces
- Trace duration by operation

**Logs**:
- Application logs (all)
- Error logs (filtered)

---

## Error Handling & Resilience

### Error Handling Strategy

#### Error Classification

1. **Domain Errors**: Business rule violations
   - `InvalidLicenseStatusError`: Invalid license operation
   - `LicenseNotFoundError`: License not found
   - `SeatLimitExceededError`: Seat limit exceeded
   - `LicenseExpiredError`: License expired

2. **Infrastructure Errors**: System failures
   - Database connection errors
   - Cache connection errors
   - External service failures

3. **Validation Errors**: Input validation failures
   - Invalid request format
   - Missing required fields
   - Invalid data types

#### Error Response Format

```json
{
  "error": {
    "code": "InvalidLicenseStatusError",
    "message": "Cannot suspend a cancelled license",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### HTTP Status Code Mapping

| Error Type | Status Code |
|------------|-------------|
| Domain validation errors | 400 Bad Request |
| Not found errors | 404 Not Found |
| Authentication errors | 401 Unauthorized |
| Authorization errors | 403 Forbidden |
| Conflict errors | 409 Conflict |
| Server errors | 500 Internal Server Error |

### Resilience Patterns

#### 1. Retry Logic

**Database Operations**:
- Automatic retry on connection errors
- Exponential backoff
- Maximum retry attempts

**External Services**:
- Retry on transient failures
- Circuit breaker pattern

#### 2. Circuit Breaker

**Implementation**: Prevents cascading failures

- **Closed**: Normal operation
- **Open**: Failing, reject requests immediately
- **Half-Open**: Testing if service recovered

#### 3. Timeout Handling

**Request Timeouts**:
- API request timeout: 30 seconds
- Database query timeout: 10 seconds
- Cache operation timeout: 5 seconds

#### 4. Graceful Degradation

**Cache Failures**:
- Continue without cache
- Log warning
- Fall back to database

**Metrics Collection Failures**:
- Continue without metrics
- Log warning
- Don't block request processing

#### 5. Idempotency

**Idempotency Keys**:
- Prevent duplicate operations
- Cache responses for idempotent requests
- TTL: 24 hours

**Implementation**:
```python
# Check idempotency key
if idempotency_key:
    cached_response = get_cached_response(idempotency_key)
    if cached_response:
        return cached_response

# Process request
response = process_request()

# Cache response
if idempotency_key:
    cache_response(idempotency_key, response)
```

### Error Monitoring

#### Alerting Rules

**Prometheus Alerts**:
- High error rate (> 5% of requests)
- High latency (p95 > 1 second)
- Database connection failures
- Cache connection failures
- License activation failures

#### Error Tracking

- **Structured Logging**: All errors logged with full context
- **Distributed Tracing**: Errors included in trace spans
- **Metrics**: Error counts by type and endpoint
- **Grafana**: Error visualization and alerting

### Recovery Procedures

#### Database Failures

1. **Connection Pool**: Automatic reconnection
2. **Read Replicas**: Failover to read replicas (future)
3. **Graceful Shutdown**: Complete in-flight requests

#### Cache Failures

1. **Fallback**: Continue without cache
2. **Reconnection**: Automatic reconnection attempts
3. **Monitoring**: Alert on cache failures

#### Service Failures

1. **Health Checks**: Kubernetes/Docker health checks
2. **Auto-restart**: Container auto-restart on failure
3. **Rolling Updates**: Zero-downtime deployments

---

## References

- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)
- [Modular Monolith](https://www.kamilgrzybek.com/blog/posts/modular-monolith-primer)
- [OpenTelemetry](https://opentelemetry.io/)
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
- [Loki](https://grafana.com/docs/loki/latest/)
