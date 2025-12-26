# Explanation: Centralized License Service

## Table of Contents

- [Problem and Requirements](#problem-and-requirements)
- [Architecture and Design](#architecture-and-design)
- [Trade-offs and Decisions](#trade-offs-and-decisions)
- [User Story Implementation](#user-story-implementation)
- [How to Run Locally](#how-to-run-locally)
- [Known Limitations and Next Steps](#known-limitations-and-next-steps)

---

## Problem and Requirements

### Problem Statement

**group.one** operates multiple brands (e.g., WP Rocket, Imagify, RocketCDN), each with its own products requiring license management. Previously, each brand managed licenses independently, leading to:

- **Fragmented Systems**: Duplicate license management logic across brands
- **No Cross-Brand Visibility**: Inability to query licenses across multiple brands
- **Scalability Issues**: Each brand reinventing the wheel for license provisioning, activation, and lifecycle management
- **Maintenance Overhead**: Multiple codebases to maintain and update

### Core Requirements

The Centralized License Service addresses these challenges by providing:

1. **Single Source of Truth**: Unified license management across all brands
2. **Multi-Tenancy**: Row-level data isolation per brand with API key authentication
3. **License Provisioning**: Brands can create license keys and assign them to products
4. **License Activation**: Products can activate licenses with seat limit enforcement
5. **Lifecycle Management**: Support for renewing, suspending, resuming, and canceling licenses
6. **Cross-Brand Querying**: Ability to query licenses across brands (future capability)
7. **Scalability**: Designed to handle growth in brands, products, and license volume
8. **Observability**: Comprehensive monitoring, logging, and tracing for production operations
9. **Event-Driven Architecture**: Decoupled communication via domain events and message queues

---

## Architecture and Design

### Architectural Patterns

The service employs a **Modular Monolith** architecture combined with **Hexagonal Architecture** (Ports & Adapters) and **Strategic CQRS** (Command Query Responsibility Segregation).

#### 1. Modular Monolith

The application is organized into domain-focused modules:

```
CentralizedLicenseService/
├── brands/          # Brand and product management
├── licenses/        # License key and license management
├── activations/     # License activation and seat management
├── core/            # Shared infrastructure and domain primitives
├── api/             # REST API layer (v1)
│   ├── brand/       # Brand-facing APIs
│   └── product/     # Product-facing APIs
└── products/        # Product catalog
```

**Benefits**:
- Faster development and deployment (single deployment unit)
- Easier testing and debugging (no distributed system complexity)
- Clear module boundaries enable future extraction to microservices
- Reduced operational overhead

#### 2. Hexagonal Architecture (Ports & Adapters)

Each module follows a layered structure:

```
┌─────────────────────────────────────┐
│         API Layer (Views)           │
│   (Django REST Framework)           │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│      Application Layer              │
│  (Commands, Queries, Handlers)      │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│         Domain Layer                │
│  (Entities, Services, Events)       │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│      Ports (Interfaces)             │
│  (Repository, Cache, EventBus)      │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│   Infrastructure Layer (Adapters)   │
│  (Django ORM, Redis, RabbitMQ)      │
└─────────────────────────────────────┘
```

**Key Principles**:
- **Domain Layer**: Pure business logic, no framework dependencies
- **Ports**: Abstract interfaces (e.g., `LicenseRepository`, `EventBus`)
- **Adapters**: Concrete implementations (e.g., `DjangoLicenseRepository`, `RabbitMQEventBus`)
- **Dependency Inversion**: Domain depends on abstractions, not implementations

#### 3. Strategic CQRS

Commands (writes) and queries (reads) are separated for clarity and optimization:

**Commands** (Write Operations):
- `ProvisionLicenseCommand`
- `RenewLicenseCommand`
- `SuspendLicenseCommand`
- `ActivateLicenseCommand`

**Queries** (Read Operations):
- `GetLicenseStatusQuery`
- `ListLicensesByEmailQuery`

**Benefits**:
- Different optimization strategies for reads vs. writes
- Easier to add caching for queries
- Clear separation of concerns
- Future-proof for read replicas or CQRS with separate read models

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | Django 4.2 + DRF | Web framework and REST API |
| **Database** | PostgreSQL 15 | Primary data store |
| **Cache** | Redis 7 | Caching and session storage |
| **Message Queue** | RabbitMQ 3 | Event-driven communication |
| **Task Queue** | Celery 5 | Background job processing |
| **Observability** | OpenTelemetry, Prometheus, Grafana, Loki, Tempo | Monitoring, metrics, logging, tracing |
| **API Docs** | drf-spectacular | OpenAPI/Swagger documentation |

### Multi-Tenancy Strategy

**Implementation**: Row-level multi-tenancy with API key-based authentication

**Flow**:
1. Brand makes API request with `X-API-Key` header
2. `TenantMiddleware` extracts and validates API key
3. Retrieves associated `brand_id` from hashed API key
4. Sets tenant context using Python's `contextvars`
5. All database queries automatically filtered by `brand_id`
6. Repository layer enforces tenant isolation

**Security**:
- API keys stored as SHA-256 hashes in database
- Constant-time comparison to prevent timing attacks
- Automatic tenant filtering prevents cross-tenant data leaks

### Event-Driven Architecture

**Domain Events**:
- `BrandCreated`
- `ProductCreated`
- `LicenseKeyCreated`
- `LicenseProvisioned`
- `LicenseRenewed`
- `LicenseActivated`
- `SeatDeactivated`

**Event Bus**:
- **Current**: Configurable via `USE_RABBITMQ` environment variable
  - **In-Memory**: Default for development/testing (events lost on restart)
  - **RabbitMQ**: Fully implemented, production-ready (durable queues, topic exchange)
- **Implementation**: `RabbitMQEventBus` uses Kombu for AMQP communication
- **Benefits**: Decoupled modules, async processing via Celery, durable event storage

**Celery Integration**:
- Background tasks for license expiration checks
- Event handler processing
- Future: Webhook notifications, email notifications

### Database Schema

**Key Tables**:

```
brands
├── id (UUID, PK)
├── name
├── slug
└── created_at

api_keys
├── id (UUID, PK)
├── brand_id (FK → brands)
├── key_hash (SHA-256)
└── created_at

products
├── id (UUID, PK)
├── brand_id (FK → brands)
├── name
├── slug
└── created_at

license_keys
├── id (UUID, PK)
├── brand_id (FK → brands)
├── key_hash (SHA-256)
├── customer_email
└── created_at

licenses
├── id (UUID, PK)
├── license_key_id (FK → license_keys)
├── product_id (FK → products)
├── brand_id (FK → brands)
├── status (valid, expired, suspended, cancelled)
├── seat_limit
├── expires_at
└── created_at

activations
├── id (UUID, PK)
├── license_id (FK → licenses)
├── instance_identifier
├── instance_type (url, hostname, machine_id)
├── status (active, deactivated)
└── activated_at

audit_logs
├── id (UUID, PK)
├── brand_id (FK → brands)
├── entity_type
├── entity_id
├── action
├── metadata (JSONB)
└── created_at
```

**Indexes**:
- `license_keys.key_hash` (unique, for fast lookups)
- `license_keys.customer_email` (for email-based queries)
- `licenses.status` (for status filtering)
- `licenses.expires_at` (for expiration checks)
- `activations.instance_identifier` (for activation lookups)

---

## Trade-offs and Decisions

### 1. Modular Monolith vs. Microservices

**Decision**: Start with a modular monolith

**Rationale**:
- **Time Constraints**: Faster to develop and deploy a single application
- **Team Size**: Small team, easier coordination
- **Complexity**: Avoid distributed system challenges (network failures, eventual consistency, service discovery)
- **Future Flexibility**: Modules can be extracted to microservices when needed

**Trade-offs**:
- ✅ Faster development and iteration
- ✅ Simpler deployment and operations
- ✅ Easier debugging and testing
- ✅ Single database transaction boundaries
- ❌ Less independent scaling (mitigated by horizontal scaling)
- ❌ Shared database (mitigated by module boundaries)
- ❌ Potential for tighter coupling if not disciplined

**Alternatives Considered**:
- **Microservices**: Rejected due to operational complexity and time constraints
- **Serverless**: Rejected due to cold start latency and vendor lock-in concerns

**Scaling Plan**:
1. **Phase 1** (Current): Modular monolith with horizontal scaling
2. **Phase 2**: Add read replicas for database, expand caching
3. **Phase 3**: Extract high-traffic modules (e.g., product APIs) to separate services
4. **Phase 4**: Full microservices architecture with API gateway

### 2. Hexagonal Architecture

**Decision**: Implement Hexagonal Architecture (Ports & Adapters)

**Rationale**:
- **Testability**: Easy to mock dependencies (repositories, cache, event bus)
- **Flexibility**: Swap implementations without changing business logic
- **Domain Focus**: Business logic isolated from infrastructure concerns
- **Maintainability**: Clear boundaries and responsibilities

**Trade-offs**:
- ✅ Highly testable (unit tests don't require database)
- ✅ Easy to swap implementations (e.g., switch from Redis to Memcached)
- ✅ Clear separation of concerns
- ❌ More boilerplate code (interfaces, adapters)
- ❌ Steeper learning curve for developers unfamiliar with pattern

**Alternatives Considered**:
- **Django-centric approach**: Rejected because it couples business logic to Django ORM
- **Clean Architecture**: Similar to Hexagonal, but Hexagonal is more pragmatic for Django

### 3. Strategic CQRS

**Decision**: Apply CQRS selectively (commands vs. queries)

**Rationale**:
- **Optimization**: Different read/write patterns (writes need validation, reads need speed)
- **Scalability**: Can scale reads independently (caching, read replicas)
- **Clarity**: Clear separation between state-changing and read-only operations
- **Future-Proof**: Easy to add read models or event sourcing later

**Trade-offs**:
- ✅ Clear intent (command vs. query)
- ✅ Easier to optimize reads (caching) and writes (validation)
- ✅ Future-ready for event sourcing
- ❌ More code (separate command/query handlers)
- ❌ Not full CQRS (shared database for reads/writes)

**Alternatives Considered**:
- **Full CQRS with separate read models**: Rejected as over-engineering for current scale
- **No CQRS**: Rejected because it conflates read/write concerns

### 4. Multi-Tenancy: Row-Level vs. Schema-Level

**Decision**: Row-level multi-tenancy with `brand_id` filtering

**Rationale**:
- **Simplicity**: Single database, single schema
- **Cost-Effective**: No need for separate databases per tenant
- **Easy Onboarding**: Adding a new brand is just a database row
- **Backup/Restore**: Single backup for all tenants

**Trade-offs**:
- ✅ Simple to implement and maintain
- ✅ Cost-effective (single database)
- ✅ Easy to add new tenants
- ❌ Risk of cross-tenant data leaks (mitigated by middleware enforcement)
- ❌ Noisy neighbor problem (one tenant can impact others)
- ❌ Harder to customize per tenant

**Alternatives Considered**:
- **Schema-per-tenant**: Rejected due to operational complexity
- **Database-per-tenant**: Rejected due to cost and management overhead

**Mitigation Strategies**:
- Middleware enforces tenant context on every request
- Repository layer double-checks tenant filtering
- Comprehensive test coverage for tenant isolation
- Future: Add database-level row-level security (RLS)

### 5. Event Bus: In-Memory vs. RabbitMQ

**Decision**: Implement both, configurable via environment variable

**Rationale**:
- **Development Simplicity**: In-memory is easier to develop and test locally
- **Production Ready**: RabbitMQ fully implemented for distributed event processing
- **Flexibility**: Can switch between implementations without code changes
- **Gradual Adoption**: Teams can enable RabbitMQ when ready

**Trade-offs**:
- ✅ Fully implemented and production-ready
- ✅ Easy to test (in-memory for unit tests)
- ✅ Durable event storage with RabbitMQ
- ✅ Async processing via Celery workers
- ❌ Requires RabbitMQ infrastructure in production
- ❌ Additional operational complexity

**Current Status**:
- **Implemented**: Both `InMemoryEventBus` and `RabbitMQEventBus`
- **Toggle**: Set `USE_RABBITMQ=true` to enable RabbitMQ
- **Docker**: RabbitMQ included in `docker-compose.yml` with Celery worker

**Scaling Plan**:
1. **Phase 1** (Current): Use in-memory for development, RabbitMQ for production
2. **Phase 2**: Add retry logic and dead-letter queues
3. **Phase 3**: Add event replay and audit capabilities


### 6. API Versioning

**Decision**: URL-based versioning (`/api/v1/`)

**Rationale**:
- **Clarity**: Version is explicit in URL
- **Backward Compatibility**: Can run multiple versions simultaneously
- **Industry Standard**: Widely adopted pattern

**Trade-offs**:
- ✅ Clear and explicit
- ✅ Easy to support multiple versions
- ❌ URL changes on version bump

**Alternatives Considered**:
- **Header-based versioning**: Rejected due to less discoverability
- **No versioning**: Rejected because breaking changes would impact clients

### 7. Async Support

**Decision**: Use Django ASGI with async views and ORM operations

**Rationale**:
- **Performance**: Better concurrency for I/O-bound operations
- **Future-Ready**: Async is the future of Python web development
- **Scalability**: Handle more concurrent requests with fewer resources

**Trade-offs**:
- ✅ Better performance for I/O-bound operations
- ✅ Future-proof
- ❌ More complex (async/await syntax)
- ❌ Not all Django features support async yet

---

## User Story Implementation

### User Story 1: Provision License (Brand API)

**Requirement**: As a brand, I want to provision a license key for a customer and assign it to one or more products.

**Implementation Status**: ✅ **Fully Implemented**

**Endpoint**: `POST /api/v1/brand/licenses/provision`

**Implementation Details**:
- **Command**: `ProvisionLicenseCommand`
- **Handler**: `ProvisionLicenseCommandHandler`
- **Domain Service**: `LicenseKeyGenerator` generates secure license keys
- **Features**:
  - Multi-product support (one license key, multiple product licenses)
  - Configurable seat limits
  - Optional expiration dates
  - Idempotency support via `idempotency_key`
  - Audit logging for compliance

**Example Request**:
```bash
curl -X POST http://localhost:8000/api/v1/brand/licenses/provision \
  -H "X-API-Key: your-brand-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "customer@example.com",
    "products": ["product-uuid-1", "product-uuid-2"],
    "expiration_date": "2025-12-31T23:59:59Z",
    "max_seats": 5,
    "idempotency_key": "unique-key-123"
  }'
```

**Response**:
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
      "expires_at": "2025-12-31T23:59:59Z"
    }
  ]
}
```

---

### User Story 2: Manage License Lifecycle (Brand API)

**Requirement**: As a brand, I want to renew, suspend, resume, or cancel licenses.

**Implementation Status**: ✅ **Fully Implemented**

**Endpoints**:
- `POST /api/v1/brand/licenses/{license_id}/renew`
- `POST /api/v1/brand/licenses/{license_id}/suspend`
- `POST /api/v1/brand/licenses/{license_id}/resume`
- `POST /api/v1/brand/licenses/{license_id}/cancel`

**Implementation Details**:
- **Commands**: `RenewLicenseCommand`, `SuspendLicenseCommand`, `ResumeLicenseCommand`, `CancelLicenseCommand`
- **Domain Service**: `LicenseLifecycleManager` enforces state transitions
- **Features**:
  - State machine validation (e.g., can't resume a cancelled license)
  - Audit logging for all lifecycle changes
  - Domain events emitted for each action

**Example: Renew License**:
```bash
curl -X POST http://localhost:8000/api/v1/brand/licenses/{license_id}/renew \
  -H "X-API-Key: your-brand-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "expiration_date": "2026-12-31T23:59:59Z"
  }'
```

**Example: Suspend License**:
```bash
curl -X POST http://localhost:8000/api/v1/brand/licenses/{license_id}/suspend \
  -H "X-API-Key: your-brand-api-key"
```

---

### User Story 3: Activate License (Product API)

**Requirement**: As a product, I want to activate a license on a specific instance (URL, hostname, or machine ID).

**Implementation Status**: ✅ **Fully Implemented**

**Endpoint**: `POST /api/v1/product/licenses/activate`

**Implementation Details**:
- **Command**: `ActivateLicenseCommand`
- **Handler**: `ActivateLicenseCommandHandler`
- **Domain Service**: `SeatManager` enforces seat limits
- **Features**:
  - Seat limit enforcement (prevents over-activation)
  - Instance type support (URL, hostname, machine_id)
  - Duplicate activation prevention (idempotent)
  - License validation (status, expiration, suspension)

**Example Request**:
```bash
curl -X POST http://localhost:8000/api/v1/product/licenses/activate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "BRAND-XXXX-XXXX-XXXX-XXXX",
    "instance_identifier": "https://example.com",
    "instance_type": "url"
  }'
```

**Response**:
```json
{
  "activation_id": "activation-uuid",
  "status": "active",
  "seats_used": 1,
  "seats_remaining": 4,
  "activated_at": "2024-01-01T00:00:00Z"
}
```

**Error Handling**:
- `404`: License key not found
- `409`: License already activated on this instance
- `422`: Seat limit exceeded, license expired, or license suspended

---

### User Story 4: Check License Status (Product API)

**Requirement**: As a product, I want to check if a license is valid for a specific instance.

**Implementation Status**: ✅ **Fully Implemented**

**Endpoint**: `GET /api/v1/product/licenses/check?license_key={key}&instance_identifier={identifier}`

**Implementation Details**:
- **Query**: `GetLicenseStatusQuery`
- **Handler**: `GetLicenseStatusQueryHandler`
- **Domain Service**: `LicenseValidator` validates license state
- **Features**:
  - Real-time validation (status, expiration, suspension)
  - Seat availability check
  - Activation status for specific instance
  - Caching for performance (Redis)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/product/licenses/check?license_key=BRAND-XXXX-XXXX-XXXX-XXXX&instance_identifier=https://example.com"
```

**Response**:
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

---

### User Story 5: Deactivate Seat (Product API)

**Requirement**: As a product, I want to deactivate a license on a specific instance to free up a seat.

**Implementation Status**: ✅ **Fully Implemented**

**Endpoint**: `POST /api/v1/product/licenses/deactivate`

**Implementation Details**:
- **Command**: `DeactivateSeatCommand`
- **Handler**: `DeactivateSeatCommandHandler`
- **Domain Service**: `SeatManager` updates seat count
- **Features**:
  - Seat release for reuse
  - Idempotent (deactivating already deactivated seat is safe)
  - Audit logging

**Example Request**:
```bash
curl -X POST http://localhost:8000/api/v1/product/licenses/deactivate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "BRAND-XXXX-XXXX-XXXX-XXXX",
    "instance_identifier": "https://example.com"
  }'
```

**Response**:
```json
{
  "status": "deactivated",
  "seats_used": 1,
  "seats_remaining": 4
}
```

---

### User Story 6: Query Licenses by Customer (Brand API)

**Requirement**: As a brand, I want to query all licenses for a customer by email address.

**Implementation Status**: ✅ **Fully Implemented**

**Endpoint**: `GET /api/v1/brand/licenses?email={email}`

**Implementation Details**:
- **Query**: `ListLicensesByEmailQuery`
- **Handler**: `ListLicensesByEmailQueryHandler`
- **Features**:
  - Email-based filtering
  - Returns all licenses across products
  - Includes seat usage information
  - Tenant-isolated (only returns licenses for authenticated brand)

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/brand/licenses?email=customer@example.com" \
  -H "X-API-Key: your-brand-api-key"
```

**Response**:
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
        "name": "WP Rocket",
        "slug": "wp-rocket"
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

---

### Cross-Brand License Querying (Future)

**Requirement**: As group.one, I want to query licenses across all brands.

**Implementation Status**: 🔧 **Designed, Not Implemented**

**Design**:
- New endpoint: `GET /api/v1/admin/licenses?email={email}`
- Requires super-admin API key (not brand-specific)
- Bypasses tenant filtering
- Returns licenses from all brands

**Reason Not Implemented**:
- Not in initial MVP scope
- Requires admin authentication system
- Can be added without architectural changes

---

## How to Run Locally

### Prerequisites

Ensure you have the following installed:

- **Python 3.11+**
- **PostgreSQL 15+**
- **Redis 7+**
- **Docker and Docker Compose** (recommended)

---

### Option 1: Docker Compose (Recommended)

This is the easiest way to run the entire stack with observability.

#### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd CentralizedLicenseService
```

#### Step 2: Start All Services

```bash
docker-compose up -d
```

This starts:
- **App**: Django application (port 8000)
- **PostgreSQL**: Database (port 5432)
- **Redis**: Cache (port 6379)
- **RabbitMQ**: Message queue (port 5672, management UI on 15672)
- **Celery Worker**: Background task processor
- **Prometheus**: Metrics (port 9091)
- **Grafana**: Dashboards (port 3000)
- **Loki**: Log aggregation (port 3100)
- **Tempo**: Distributed tracing (port 3200)

#### Step 3: Access the Application

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Admin Panel**: http://localhost:8000/admin
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9091
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

#### Step 4: Create a Brand and API Key

```bash
# Access Django shell
docker-compose exec app python manage.py shell

# Create a brand
from brands.domain.entities import Brand
from brands.infrastructure.repositories import DjangoBrandRepository

repo = DjangoBrandRepository()
brand = Brand.create(name="WP Rocket", slug="wp-rocket")
repo.save(brand)

# Create an API key
from brands.infrastructure.models import APIKey
api_key = APIKey.objects.create(brand_id=brand.id)
print(f"API Key: {api_key.key}")  # Save this for API requests
```

#### Step 5: Create a Product

```bash
# In Django shell
from products.models import Product

product = Product.objects.create(
    brand_id=brand.id,
    name="WP Rocket Pro",
    slug="wp-rocket-pro"
)
print(f"Product ID: {product.id}")
```

#### Step 6: Test API with cURL

**Provision a License**:
```bash
curl -X POST http://localhost:8000/api/v1/brand/licenses/provision \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "products": ["<product-uuid>"],
    "expiration_date": "2025-12-31T23:59:59Z",
    "max_seats": 3
  }'
```

**Activate a License**:
```bash
curl -X POST http://localhost:8000/api/v1/product/licenses/activate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "WPROCKET-XXXX-XXXX-XXXX-XXXX",
    "instance_identifier": "https://mysite.com",
    "instance_type": "url"
  }'
```

**Check License Status**:
```bash
curl -X GET "http://localhost:8000/api/v1/product/licenses/check?license_key=WPROCKET-XXXX-XXXX-XXXX-XXXX&instance_identifier=https://mysite.com"
```

---

### Option 2: Local Development (Without Docker)

#### Step 1: Clone and Set Up Virtual Environment

```bash
git clone <repository-url>
cd CentralizedLicenseService

python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Step 2: Install Dependencies

```bash
pip install -r requirements/dev.txt
```

#### Step 3: Set Up PostgreSQL and Redis

**PostgreSQL**:
```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb license_service
```

**Redis**:
```bash
# macOS (Homebrew)
brew install redis
brew services start redis
```

#### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_DEBUG=True
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/license_service
REDIS_URL=redis://localhost:6379/0

# Optional: Observability
OTEL_SERVICE_NAME=license-service
OTEL_SERVICE_VERSION=1.0.0
PROMETHEUS_PORT=9090
```

#### Step 5: Run Migrations

```bash
python manage.py migrate
```

#### Step 6: Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

#### Step 7: Start Development Server

```bash
python manage.py runserver
```

Access the API at http://localhost:8000

#### Step 8: Start Celery Worker (Optional)

In a separate terminal:

```bash
celery -A CentralizedLicenseService worker --loglevel=info
```

---

### Option 3: Using Postman

A Postman collection is included in the `postman/` directory.

#### Step 1: Import Collection

1. Open Postman
2. Import `postman/Centralized_License_Service.postman_collection.json`
3. Import `postman/Local.postman_environment.json`

#### Step 2: Set Environment Variables

In Postman, select the "Local" environment and set:
- `base_url`: `http://localhost:8000`
- `api_key`: Your brand API key
- `product_id`: A product UUID

#### Step 3: Run Requests

The collection includes pre-configured requests for all endpoints.

---

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | (required) |
| `DJANGO_DEBUG` | Enable debug mode | `False` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/license_service` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `RABBITMQ_URL` | RabbitMQ connection string | `amqp://guest:guest@localhost:5672//` |
| `USE_RABBITMQ` | **Enable RabbitMQ event bus (set to `true` for production)** | `false` |
| `OTEL_SERVICE_NAME` | OpenTelemetry service name | `license-service` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint for traces | `http://tempo:4317` |
| `PROMETHEUS_PORT` | Prometheus metrics port | `9090` |

---

### Health Checks

Verify the service is running:

```bash
# Basic health check
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/health/db

# Cache connectivity
curl http://localhost:8000/health/cache

# Full readiness check
curl http://localhost:8000/ready
```

---

## Known Limitations and Next Steps

### Known Limitations

#### 1. **No Cross-Brand Admin API**
- **Limitation**: No API for querying licenses across all brands
- **Impact**: group.one admins cannot query licenses globally
- **Next Step**: Implement admin API with super-admin authentication

#### 2. **No Webhook Notifications**
- **Limitation**: Brands are not notified of license events (e.g., activation, expiration)
- **Impact**: Brands must poll for license status changes
- **Next Step**: Implement webhook system with retry logic

#### 3. **Limited Rate Limiting**
- **Limitation**: Basic rate limiting is configured but not fine-tuned
- **Impact**: Potential for API abuse
- **Next Step**: Implement per-brand rate limits with Redis

#### 4. **No License Transfer**
- **Limitation**: Cannot transfer a license from one customer to another
- **Impact**: Brands must cancel and re-provision licenses
- **Next Step**: Implement `TransferLicenseCommand`

#### 5. **No License Usage Analytics**
- **Limitation**: No built-in analytics for license usage trends
- **Impact**: Brands cannot see usage patterns over time
- **Next Step**: Add analytics endpoints and Grafana dashboards

#### 6. **No Multi-Product License Keys**
- **Limitation**: While one license key can have multiple product licenses, there's no concept of "bundles"
- **Impact**: Brands must manually specify products during provisioning
- **Next Step**: Implement product bundles (e.g., "Enterprise Bundle")

#### 7. **No License Downgrade/Upgrade**
- **Limitation**: Cannot change seat limits or products for existing licenses
- **Impact**: Brands must cancel and re-provision licenses
- **Next Step**: Implement `UpdateLicenseCommand` for seat limit changes

#### 8. **No Soft Deletes**
- **Limitation**: Cancelled licenses are marked as "cancelled" but not soft-deleted
- **Impact**: Database grows with cancelled licenses
- **Next Step**: Implement soft delete with archival strategy

#### 9. **No API Versioning Strategy for Breaking Changes**
- **Limitation**: No documented process for deprecating API versions
- **Impact**: Breaking changes could impact clients
- **Next Step**: Document API deprecation policy (e.g., 6-month notice)

---

### Next Steps (Roadmap)

#### Phase 1: Production Readiness (1-2 weeks)
- [ ] Configure RabbitMQ for production (set `USE_RABBITMQ=true`)
- [ ] Implement webhook notifications for license events
- [ ] Add comprehensive integration tests for all endpoints
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Configure production observability (Grafana Cloud or self-hosted)
- [ ] Implement per-brand rate limiting
- [ ] Add API key rotation mechanism

#### Phase 2: Feature Enhancements (1 month)
- [ ] Implement cross-brand admin API
- [ ] Add license transfer functionality
- [ ] Implement license upgrade/downgrade
- [ ] Add product bundles
- [ ] Implement usage analytics endpoints
- [ ] Add email notifications for license expiration
- [ ] Implement license import/export for migrations

#### Phase 3: Scalability (2-3 months)
- [ ] Add PostgreSQL read replicas
- [ ] Implement Redis caching for all read queries
- [ ] Add CDN for static assets
- [ ] Implement horizontal scaling with load balancer
- [ ] Add database connection pooling (PgBouncer)
- [ ] Implement background job for license expiration checks
- [ ] Add Celery beat for scheduled tasks

#### Phase 4: Advanced Features (3-6 months)
- [ ] Implement event sourcing for complete audit trail
- [ ] Add GraphQL API for flexible querying
- [ ] Implement license usage forecasting (ML-based)
- [ ] Add multi-region deployment support
- [ ] Implement license marketplace (resellers)
- [ ] Add SSO integration for brand admin portals
- [ ] Implement license compliance reporting

#### Phase 5: Microservices Migration (6-12 months)
- [ ] Extract product APIs to separate service
- [ ] Implement API gateway (Kong or AWS API Gateway)
- [ ] Add service mesh (Istio) for inter-service communication
- [ ] Migrate to Kubernetes for orchestration
- [ ] Implement distributed tracing across services
- [ ] Add circuit breakers and retry logic
- [ ] Implement database per service (if needed)

---

### Testing Strategy

**Current Coverage**:
- Unit tests for domain entities and services
- Integration tests for API endpoints
- Test coverage: ~85% (see `coverage.xml`)

**Next Steps**:
- Add end-to-end tests with Playwright
- Add load testing with Locust
- Add chaos engineering tests (e.g., database failures)
- Add contract testing for API versioning

---

### Security Considerations

**Current Measures**:
- API keys hashed with SHA-256
- Constant-time comparison for API key validation
- Tenant isolation enforced at middleware level
- HTTPS enforced in production (via reverse proxy)
- CORS configured for allowed origins

**Next Steps**:
- Implement API key expiration and rotation
- Add IP whitelisting for brand APIs
- Implement OAuth2 for admin APIs
- Add database-level row-level security (RLS)
- Implement security headers (CSP, HSTS, etc.)
- Add penetration testing

---

### Performance Benchmarks

**Target SLAs**:
- **P50 Latency**: < 100ms
- **P95 Latency**: < 300ms
- **P99 Latency**: < 500ms
- **Availability**: 99.9% uptime

**Current Performance** (local testing):
- Provision License: ~50ms
- Activate License: ~30ms
- Check License Status: ~20ms (cached), ~40ms (uncached)

**Next Steps**:
- Conduct load testing to validate SLAs
- Optimize database queries with EXPLAIN ANALYZE
- Add database indexes for slow queries
- Implement query result caching

---

## Conclusion

The Centralized License Service provides a robust, scalable foundation for managing licenses across multiple brands. By leveraging modern architectural patterns (Modular Monolith, Hexagonal Architecture, CQRS) and a comprehensive observability stack, the service is designed for both current needs and future growth.

While there are known limitations (primarily around advanced features like webhooks and cross-brand analytics), the architecture is designed to accommodate these enhancements without major refactoring. The roadmap outlines a clear path from MVP to a production-ready, enterprise-grade license management platform.

For questions or contributions, please refer to the [Readme.md](Readme.md) and [ARCHITECTURE.md](docs/ARCHITECTURE.md).
