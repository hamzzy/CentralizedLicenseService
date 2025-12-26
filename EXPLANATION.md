# Centralized License Service - Explanation Document

## Problem and Requirements

### Problem Statement

WP Media operates multiple brands (e.g., RankMath, WP Rocket) that each need to manage
licenses and entitlements for their products. Currently, each brand likely handles
licensing independently, leading to:

- **Inconsistent license management** across brands
- **Duplicated effort** in building and maintaining license systems
- **Difficulties in cross-brand analytics** and reporting
- **Lack of centralized control** over license policies

### Requirements

The solution must provide:

1. **Single Source of Truth**: Centralized license management for all brands
2. **Multi-Tenancy**: Complete data isolation between brands
3. **Brand Integration**: APIs for brand systems to provision and manage licenses
4. **Product Integration**: APIs for end-user products to activate and check licenses
5. **Scalability**: Handle high volumes of license checks and activations
6. **Observability**: Logging, metrics, and health checks for production monitoring
7. **Extensibility**: Easy to add new brands, products, and features

### User Stories

**US1: Provision License**
- As a brand system, I want to provision a license key and associated licenses for a
  customer, so that I can grant access to my products.

**US2: Manage License Lifecycle**
- As a brand system, I want to renew, suspend, resume, and cancel licenses, so that I
  can manage customer access over time.

**US3: Activate License**
- As an end-user product, I want to activate a license on my instance, so that I can
  enable premium features.

**US4: Check License Status**
- As an end-user product, I want to check if my license is valid and has available
  seats, so that I can verify access before enabling features.

**US5: Deactivate Seat**
- As an end-user product, I want to deactivate a seat when uninstalled, so that the
  seat becomes available for reuse.

**US6: List Licenses by Customer**
- As a brand system, I want to query all licenses for a customer by email, so that I
  can provide customer support and manage accounts.

## Architecture and Design

### Architectural Approach

The solution follows a **Modular Monolith + Hexagonal Architecture + Strategic CQRS**
pattern.

#### Modular Monolith

The application is organized into self-contained modules:

- **`brands/`**: Brand and product management
- **`licenses/`**: License key and license management
- **`activations/`**: License activation and seat management
- **`core/`**: Shared infrastructure (events, middleware, value objects)
- **`api/`**: REST API layer (brand-facing and product-facing)

Each module follows a consistent structure:
```
module/
├── domain/          # Domain entities, value objects, services
├── application/     # Use cases, commands, queries, handlers
├── infrastructure/ # Django models, repositories, adapters
└── ports/          # Repository interfaces (abstractions)
```

#### Hexagonal Architecture (Ports & Adapters)

The architecture separates concerns into three layers:

1. **Domain Layer** (Inner Core)
   - Pure business logic
   - No external dependencies
   - Immutable entities and value objects
   - Domain events

2. **Application Layer** (Use Cases)
   - Orchestrates domain logic
   - Commands and queries (CQRS)
   - Handlers for business workflows
   - DTOs for data transfer

3. **Infrastructure Layer** (Adapters)
   - Django ORM models
   - Repository implementations
   - Cache adapters
   - Event bus implementations
   - External service integrations

**Benefits**:
- Testability: Easy to mock dependencies
- Flexibility: Swap implementations without changing domain logic
- Maintainability: Clear boundaries and responsibilities

#### Strategic CQRS

Command Query Responsibility Segregation is applied selectively:

- **Commands** (Write Operations):
  - `ProvisionLicenseCommand`
  - `RenewLicenseCommand`
  - `SuspendLicenseCommand`
  - `ActivateLicenseCommand`
  - `DeactivateSeatCommand`

- **Queries** (Read Operations):
  - `GetLicenseStatusQuery`
  - `ListLicensesByEmailQuery`

**Benefits**:
- Optimized read/write paths
- Easy to add caching for queries
- Clear separation of concerns
- Future scalability (can add read replicas)

### Design Patterns

1. **Repository Pattern**: Abstracts data access behind interfaces
2. **Domain Events**: Decoupled communication between modules
3. **Value Objects**: Immutable, validated domain concepts (Email, BrandSlug, etc.)
4. **Factory Pattern**: Domain entity creation (`Brand.create()`, `License.create()`)
5. **Strategy Pattern**: Different validation strategies per license type

### Multi-Tenancy Implementation

**Strategy**: Row-level multi-tenancy with API key authentication

**Mechanism**:
1. `TenantMiddleware` extracts `brand_id` from API key header
2. Sets tenant context in `contextvars` (thread-local storage)
3. All repository queries automatically filter by `brand_id`
4. Data isolation enforced at application level

**Benefits**:
- No schema changes per tenant
- Easy to add new brands
- Efficient data storage
- Simple to understand and maintain

### Security

- **API Key Authentication**: SHA-256 hashed keys for brand APIs
- **License Key Validation**: Secure key generation and verification
- **Idempotency Keys**: Prevent duplicate operations
- **Input Validation**: Comprehensive validation at domain and API layers

## Trade-offs and Decisions

### Alternatives Considered

#### 1. Microservices vs Modular Monolith

**Alternative**: Build separate microservices for each module

**Why Not Chosen**:
- **Time Constraints**: Microservices require more infrastructure setup
- **Operational Complexity**: More services to deploy, monitor, and maintain
- **Team Size**: Small team benefits from simpler architecture
- **Network Overhead**: Inter-service communication adds latency

**Chosen Approach**: Modular Monolith
- Faster development and deployment
- Easier debugging (single codebase)
- Can extract modules to services later if needed
- Single deployment unit reduces complexity

**Trade-off**: Less independent scaling, but acceptable for current scale

#### 2. Event Sourcing vs Traditional CRUD

**Alternative**: Use event sourcing for complete audit trail

**Why Not Chosen**:
- **Complexity**: Event sourcing adds significant complexity
- **Time Constraints**: More time to implement and test
- **Current Needs**: Traditional audit log sufficient for now

**Chosen Approach**: Traditional CRUD with audit logging
- Simpler to implement and understand
- Faster to develop
- Audit log table provides sufficient history

**Trade-off**: Less powerful than event sourcing, but meets current requirements

#### 3. Synchronous vs Asynchronous Processing

**Alternative**: Fully synchronous request/response

**Why Not Chosen**:
- **Scalability**: Async allows handling more concurrent requests
- **Performance**: Non-blocking I/O improves throughput
- **Future-Proof**: Ready for background tasks and event processing

**Chosen Approach**: Async-first with ASGI
- Better scalability
- Non-blocking database and cache operations
- Foundation for future async features

**Trade-off**: Slightly more complex, but better performance

#### 4. In-Memory Event Bus vs Message Queue

**Alternative**: Use RabbitMQ or Kafka for event bus

**Why Not Chosen**:
- **Operational Overhead**: Additional infrastructure to manage
- **Complexity**: More moving parts
- **Current Scale**: In-memory bus sufficient for modular monolith

**Chosen Approach**: In-memory event bus
- Simpler to operate
- No additional infrastructure
- Easy to replace with message queue later

**Trade-off**: Not distributed, but fine for current architecture

### Scaling Plan

#### Phase 1: Current (Modular Monolith)
- Single Django application
- PostgreSQL database
- Redis cache
- Horizontal scaling: Multiple app instances behind load balancer

#### Phase 2: Database Optimization
- **Read Replicas**: Add PostgreSQL read replicas for query scaling
- **Connection Pooling**: PgBouncer for connection management
- **Query Optimization**: Add indexes, optimize slow queries

#### Phase 3: Caching Expansion
- **Cache More**: Expand Redis caching for license status queries
- **CDN**: Add CDN for static assets
- **Cache Warming**: Pre-populate cache for common queries

#### Phase 4: Module Extraction (If Needed)
- Extract high-traffic modules to separate services:
  1. Extract `activations` module (most frequent operations)
  2. Add API gateway for routing
  3. Use message queue for inter-service communication
  4. Maintain shared database initially, then split

#### Phase 5: Advanced Scaling
- **Event Sourcing**: Migrate to event sourcing for audit trail
- **Read Models**: Separate read models for complex queries
- **Sharding**: Database sharding by brand if needed
- **CQRS Full**: Full CQRS with separate read/write databases

**Evolution Path**:
The modular monolith design allows gradual evolution:
1. Start simple (current state)
2. Optimize bottlenecks (caching, read replicas)
3. Extract modules only when needed
4. Scale infrastructure independently

## User Story Implementation

### US1: Provision License ✅ **IMPLEMENTED**

**Status**: Fully implemented

**Implementation**:
- **Endpoint**: `POST /api/v1/brand/licenses/provision`
- **Handler**: `ProvisionLicenseHandler`
- **Command**: `ProvisionLicenseCommand`
- **Features**:
  - Creates `LicenseKey` entity
  - Creates `License` entities for each product
  - Generates secure license key (format: `PREFIX-XXXX-XXXX-XXXX-XXXX`)
  - Supports idempotency keys
  - Validates brand and products exist
  - Publishes `LicenseKeyCreated` and `LicenseProvisioned` events

**Code Locations**:
- `licenses/application/handlers/provision_license_handler.py`
- `licenses/application/commands/provision_license.py`
- `api/v1/brand/views.py::provision_license`

### US2: Manage License Lifecycle ✅ **IMPLEMENTED**

**Status**: Fully implemented

**Implementation**:
- **Endpoints**:
  - `POST /api/v1/brand/licenses/{id}/renew`
  - `POST /api/v1/brand/licenses/{id}/suspend`
  - `POST /api/v1/brand/licenses/{id}/resume`
  - `POST /api/v1/brand/licenses/{id}/cancel`
- **Handlers**: `RenewLicenseHandler`, `SuspendLicenseHandler`, `ResumeLicenseHandler`, `CancelLicenseHandler`
- **Domain Service**: `LicenseLifecycleManager`
- **Features**:
  - State transitions with validation
  - Prevents invalid transitions (e.g., can't suspend cancelled license)
  - Publishes domain events for each state change
  - Updates expiration dates on renewal
  - Invalidates cache on state changes

**Code Locations**:
- `licenses/application/handlers/license_lifecycle_handlers.py`
- `licenses/domain/services.py::LicenseLifecycleManager`
- `licenses/domain/license.py` (domain entity methods)

### US3: Activate License ✅ **IMPLEMENTED**

**Status**: Fully implemented

**Implementation**:
- **Endpoint**: `POST /api/v1/product/licenses/activate`
- **Handler**: `ActivateLicenseHandler`
- **Command**: `ActivateLicenseCommand`
- **Domain Service**: `SeatManager`
- **Features**:
  - Validates license key and license status
  - Checks seat availability
  - Prevents duplicate activations on same instance
  - Creates `Activation` entity
  - Supports instance types: URL, hostname, machine_id
  - Publishes `LicenseActivated` event

**Code Locations**:
- `activations/application/handlers/activate_license_handler.py`
- `activations/domain/services.py::SeatManager`
- `api/v1/product/views.py::activate_license`

### US4: Check License Status ✅ **IMPLEMENTED**

**Status**: Fully implemented

**Implementation**:
- **Endpoint**: `GET /api/v1/product/licenses/check`
- **Handler**: `GetLicenseStatusHandler`
- **Query**: `GetLicenseStatusQuery`
- **Features**:
  - Validates license key
  - Checks license validity (status, expiration)
  - Returns seat usage information
  - Checks if instance is already activated
  - Cached for performance

**Code Locations**:
- `licenses/application/handlers/get_license_status_handler.py`
- `licenses/application/queries/get_license_status.py`
- `api/v1/product/views.py::get_license_status`

### US5: Deactivate Seat ✅ **IMPLEMENTED**

**Status**: Fully implemented

**Implementation**:
- **Endpoint**: `POST /api/v1/product/licenses/deactivate`
- **Handler**: `DeactivateSeatHandler`
- **Command**: `DeactivateSeatCommand`
- **Features**:
  - Finds activation by license key and instance identifier
  - Marks activation as inactive
  - Frees seat for reuse
  - Publishes `SeatDeactivated` event
  - Invalidates cache

**Code Locations**:
- `activations/application/handlers/deactivate_seat_handler.py`
- `activations/application/commands/deactivate_seat.py`
- `api/v1/product/views.py::deactivate_seat`

### US6: List Licenses by Customer ✅ **IMPLEMENTED**

**Status**: Fully implemented

**Implementation**:
- **Endpoint**: `GET /api/v1/brand/licenses?email={email}`
- **Handler**: `ListLicensesByEmailHandler`
- **Query**: `ListLicensesByEmailQuery`
- **Features**:
  - Finds all license keys for customer email
  - Returns all licenses associated with those keys
  - Includes seat usage information
  - Filters by brand (multi-tenancy)

**Code Locations**:
- `licenses/application/handlers/list_licenses_by_email_handler.py`
- `licenses/application/queries/list_licenses_by_email.py`
- `api/v1/brand/views.py::list_licenses_by_email`

### Summary

**All 6 user stories are fully implemented** with:
- Complete domain logic
- Application layer handlers
- API endpoints
- Error handling
- Domain events
- Tests (unit and integration)

## How to Run Locally

### Prerequisites

- Python 3.11+ (or 3.8+ for compatibility)
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (recommended)

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
```bash
git clone <repository-url>
cd CentralizedLicenseService
```

2. **Start services**:
```bash
docker-compose up -d
```

This starts:
- Django app (port 8000)
- PostgreSQL (port 5432)
- Redis (port 6379)

3. **Run migrations**:
```bash
docker-compose exec app python manage.py migrate
```

4. **Create a superuser** (optional):
```bash
docker-compose exec app python manage.py createsuperuser
```

5. **Access the service**:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- Admin: http://localhost:8000/admin

### Option 2: Local Development

1. **Create virtual environment**:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements/dev.txt
```

3. **Set up PostgreSQL and Redis**:
   - Start PostgreSQL locally or use Docker:
     ```bash
     docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine
     ```
   - Start Redis locally or use Docker:
     ```bash
     docker run -d --name redis -p 6379:6379 redis:7-alpine
     ```

4. **Set environment variables**:
Create a `.env` file:
```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DB_HOST=localhost
DB_NAME=license_service
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

5. **Run migrations**:
```bash
python manage.py migrate
```

6. **Create test data** (optional):
```bash
python manage.py shell
```

```python
from brands.infrastructure.models import Brand, ApiKey
from products.infrastructure.models import Product

# Create brand
brand = Brand.objects.create(name="RankMath", slug="rankmath", prefix="RM")

# Create API key
api_key = ApiKey.objects.create(brand=brand)
print(f"API Key: {api_key._raw_key}")  # Save this!

# Create product
product = Product.objects.create(brand=brand, name="RankMath Pro", slug="rankmath-pro")
```

7. **Start development server**:
```bash
python manage.py runserver
```

### Sample API Requests

#### 1. Provision License (Brand API)

```bash
curl -X POST http://localhost:8000/api/v1/brand/licenses/provision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{
    "customer_email": "customer@example.com",
    "products": ["PRODUCT_UUID_HERE"],
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
    "key": "RM-XXXX-XXXX-XXXX-XXXX",
    "customer_email": "customer@example.com",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "licenses": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "product_id": "PRODUCT_UUID",
      "status": "valid",
      "seat_limit": 5,
      "expires_at": "2025-12-31T23:59:59Z"
    }
  ]
}
```

#### 2. Activate License (Product API)

```bash
curl -X POST http://localhost:8000/api/v1/product/licenses/activate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "RM-XXXX-XXXX-XXXX-XXXX",
    "instance_identifier": "https://example.com",
    "instance_type": "url"
  }'
```

**Response**:
```json
{
  "activation_id": "770e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "seats_used": 1,
  "seats_remaining": 4,
  "activated_at": "2024-01-01T00:00:00Z"
}
```

#### 3. Check License Status (Product API)

```bash
curl "http://localhost:8000/api/v1/product/licenses/check?license_key=RM-XXXX-XXXX-XXXX-XXXX&instance_identifier=https://example.com"
```

**Response**:
```json
{
  "is_valid": true,
  "license": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "status": "valid",
    "seat_limit": 5,
    "seats_used": 1,
    "seats_remaining": 4,
    "expires_at": "2025-12-31T23:59:59Z"
  },
  "is_activated": true,
  "activation": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "activated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### 4. Renew License (Brand API)

```bash
curl -X POST http://localhost:8000/api/v1/brand/licenses/LICENSE_UUID/renew \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{
    "expiration_date": "2026-12-31T23:59:59Z"
  }'
```

#### 5. List Licenses by Email (Brand API)

```bash
curl "http://localhost:8000/api/v1/brand/licenses?email=customer@example.com" \
  -H "X-API-Key: YOUR_API_KEY_HERE"
```

### Postman Collection

Import the OpenAPI schema into Postman:
1. Go to http://localhost:8000/api/schema/
2. Download the OpenAPI JSON
3. Import into Postman
4. Set `X-API-Key` header in collection variables

## Known Limitations and Next Steps

### Known Limitations

1. **In-Memory Event Bus**
   - **Limitation**: Events are not persisted and lost on restart
   - **Impact**: Low - events are for decoupling, not critical data
   - **Mitigation**: Can replace with message queue (RabbitMQ/Kafka) later

2. **Single Database**
   - **Limitation**: All modules share same database
   - **Impact**: Medium - potential bottleneck at scale
   - **Mitigation**: Can add read replicas, then split databases per module

3. **Synchronous Audit Logging**
   - **Limitation**: Audit logs written synchronously (adds latency)
   - **Impact**: Low - minimal performance impact
   - **Mitigation**: Can move to async background task

4. **No Rate Limiting**
   - **Limitation**: API endpoints don't have rate limiting
   - **Impact**: Medium - vulnerable to abuse
   - **Mitigation**: Add rate limiting middleware (Django Ratelimit)

5. **Limited Caching**
   - **Limitation**: Only license status queries are cached
   - **Impact**: Low - can expand caching as needed
   - **Mitigation**: Add caching to more read operations

6. **No Webhook Support**
   - **Limitation**: No webhooks for license events
   - **Impact**: Low - brands can poll or use events
   - **Mitigation**: Add webhook system for external integrations

### Next Steps

#### Short Term (1-3 months)

1. **Add Rate Limiting**
   - Implement rate limiting middleware
   - Configure limits per API key
   - Add rate limit headers to responses

2. **Expand Caching**
   - Cache license key lookups
   - Cache product information
   - Implement cache warming

3. **Improve Monitoring**
   - Add Prometheus metrics
   - Set up Grafana dashboards
   - Configure alerting

4. **Add Webhooks**
   - Webhook configuration per brand
   - Retry logic for failed webhooks
   - Webhook signature verification

#### Medium Term (3-6 months)

1. **Database Optimization**
   - Add read replicas
   - Optimize slow queries
   - Add connection pooling

2. **Event Bus Migration**
   - Replace in-memory bus with RabbitMQ
   - Add event persistence
   - Implement event replay

3. **Enhanced Security**
   - Add API key rotation
   - Implement OAuth2 for product APIs
   - Add request signing

4. **Performance Testing**
   - Load testing
   - Identify bottlenecks
   - Optimize hot paths

#### Long Term (6+ months)

1. **Module Extraction**
   - Extract activations module to separate service
   - Add API gateway
   - Implement service mesh

2. **Event Sourcing**
   - Migrate to event sourcing
   - Add event store
   - Implement CQRS read models

3. **Multi-Region Support**
   - Database replication across regions
   - CDN for static assets
   - Regional API endpoints

4. **Advanced Features**
   - License usage analytics
   - Predictive expiration alerts
   - Automated license renewal

### Migration Path

The architecture is designed for gradual evolution:

1. **Current**: Modular monolith with shared database
2. **Phase 1**: Add read replicas and caching
3. **Phase 2**: Extract high-traffic modules
4. **Phase 3**: Full microservices with event sourcing

Each phase can be implemented incrementally without major rewrites.

## Conclusion

The Centralized License Service provides a robust, scalable foundation for managing
licenses across multiple brands. The modular monolith architecture balances development
speed with future scalability, while the hexagonal architecture ensures maintainability
and testability.

All user stories are fully implemented, and the system is production-ready with
comprehensive error handling, logging, and observability. The design allows for
gradual evolution as requirements grow and scale increases.

