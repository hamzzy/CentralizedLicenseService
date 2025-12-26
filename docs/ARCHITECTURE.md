# Architecture Documentation

## Overview

The Centralized License Service is built using a **Modular Monolith** architecture
pattern, combined with **Hexagonal Architecture** (Ports & Adapters) and
**Strategic CQRS** (Command Query Responsibility Segregation).

## Architectural Decisions

### Why Modular Monolith?

**Decision**: Use a modular monolith instead of microservices.

**Rationale**:
- **Time Constraints**: Faster development and deployment
- **Team Size**: Small team, easier to coordinate
- **Complexity**: Reduces operational overhead
- **Future Flexibility**: Modules can be extracted to services later

**Trade-offs**:
- ✅ Faster development
- ✅ Easier testing and debugging
- ✅ Single deployment unit
- ❌ Less independent scaling
- ❌ Shared database (can be mitigated with module boundaries)

### Why Hexagonal Architecture?

**Decision**: Implement Hexagonal Architecture (Ports & Adapters).

**Rationale**:
- **Testability**: Easy to mock dependencies
- **Flexibility**: Swap implementations (e.g., database, cache)
- **Domain Focus**: Business logic isolated from infrastructure
- **Maintainability**: Clear boundaries and responsibilities

**Structure**:
```
Domain Layer (Core Business Logic)
    ↑
Application Layer (Use Cases)
    ↑
Infrastructure Layer (Django ORM, Redis, etc.)
```

### Why Strategic CQRS?

**Decision**: Apply CQRS selectively (commands vs queries).

**Rationale**:
- **Optimization**: Different read/write patterns
- **Scalability**: Can scale reads independently
- **Clarity**: Clear separation of concerns
- **Future-Proof**: Easy to add read models/caching

**Implementation**:
- Commands: `ProvisionLicenseCommand`, `RenewLicenseCommand`
- Queries: `GetLicenseStatusQuery`, `ListLicensesByEmailQuery`
- Separate handlers for each

## Module Structure

### Brands Module

**Purpose**: Manage brands and products.

**Domain Entities**:
- `Brand`: Represents a tenant/brand
- `Product`: Represents a product within a brand

**Ports**:
- `BrandRepository`: Brand persistence interface
- `ProductRepository`: Product persistence interface

**Adapters**:
- `DjangoBrandRepository`: Django ORM implementation
- `DjangoProductRepository`: Django ORM implementation

### Licenses Module

**Purpose**: Manage license keys and licenses.

**Domain Entities**:
- `LicenseKey`: Customer-facing license key
- `License`: Product-specific license grant

**Domain Services**:
- `LicenseKeyGenerator`: Generates secure license keys
- `LicenseValidator`: Validates license state
- `LicenseLifecycleManager`: Manages license lifecycle

**Ports**:
- `LicenseKeyRepository`: License key persistence
- `LicenseRepository`: License persistence

**Application Layer**:
- Commands: Provision, Renew, Suspend, Resume, Cancel
- Queries: Get Status, List by Email
- Handlers: Command and query handlers

### Activations Module

**Purpose**: Manage license activations and seat limits.

**Domain Entities**:
- `Activation`: Represents an active license instance

**Domain Services**:
- `SeatManager`: Manages seat limits and availability

**Ports**:
- `ActivationRepository`: Activation persistence

### Core Module

**Purpose**: Shared infrastructure and domain primitives.

**Components**:
- Domain Events: `DomainEvent`, `EventBus`
- Value Objects: `Email`, `BrandSlug`, `LicenseStatus`
- Exceptions: Domain-specific exceptions
- Middleware: Tenant, Auth, Observability
- Infrastructure: Cache, Event Bus implementations

## Data Flow

### Write Flow (Command)

```
API Request
  ↓
Serializer (Validation)
  ↓
View (Async)
  ↓
Command Handler
  ↓
Domain Service / Entity
  ↓
Repository (Port)
  ↓
Django ORM (Adapter)
  ↓
PostgreSQL
```

### Read Flow (Query)

```
API Request
  ↓
View (Async)
  ↓
Query Handler
  ↓
Repository (Port)
  ↓
Django ORM (Adapter)
  ↓
PostgreSQL / Cache
  ↓
DTO (Response)
```

## Multi-Tenancy

### Implementation

**Strategy**: Row-level multi-tenancy with API key authentication.

**Mechanism**:
1. `TenantMiddleware` extracts `brand_id` from API key
2. Sets tenant context in `contextvars`
3. All queries automatically filtered by `brand_id`
4. Repository layer enforces tenant isolation

**Benefits**:
- Data isolation at application level
- No schema changes per tenant
- Easy to add new tenants

**Considerations**:
- Must ensure all queries include tenant filter
- API keys must be securely stored (SHA-256 hashing)

## Event-Driven Architecture

### Domain Events

Events represent significant business occurrences:

- `BrandCreated`
- `ProductCreated`
- `LicenseKeyCreated`
- `LicenseProvisioned`
- `LicenseRenewed`
- `LicenseActivated`
- `SeatDeactivated`

### Event Bus

**Current Implementation**: In-memory event bus (`InMemoryEventBus`)

**Future**: Can be replaced with message queue (RabbitMQ, Kafka)

**Benefits**:
- Decoupled modules
- Easy to add new event handlers
- Async processing

## Caching Strategy

### Cache Layer

**Purpose**: Improve read performance for license validation.

**Implementation**:
- Redis for cache backend
- Cache license status queries
- Invalidate on license updates

**Cache Keys**:
- `license:status:{license_id}`
- `license:key:{license_key_hash}`

## Security

### API Key Authentication

- **Brand APIs**: API key in `X-API-Key` header
- **Product APIs**: License key in request body
- **Storage**: SHA-256 hashed in database
- **Validation**: Constant-time comparison

### License Key Generation

- Format: `PREFIX-XXXX-XXXX-XXXX-XXXX`
- Cryptographically secure random generation
- Stored as hash in database

## Observability

### Logging

- Structured logging with correlation IDs
- Request/response logging
- Error tracking

### Metrics

- Request duration tracking
- Health check endpoints
- Database and cache connectivity

### Health Checks

- `/health`: Basic health
- `/health/db`: Database connectivity
- `/health/cache`: Cache connectivity
- `/ready`: Full readiness check

## Database Schema

### Key Tables

- `brands`: Brand information
- `api_keys`: API key authentication
- `products`: Product definitions
- `license_keys`: Customer license keys
- `licenses`: Product-specific licenses
- `activations`: Active license instances
- `audit_logs`: Audit trail
- `idempotency_keys`: Idempotency tracking

### Indexes

- License key lookups
- Customer email queries
- Status-based queries
- Expiration date queries

## Async Support

### ASGI

- Django ASGI application
- Async views and handlers
- Async ORM operations

### Background Tasks

- Django management commands
- Periodic license expiration checks
- Event handler processing

## Future Considerations

### Scalability

- **Read Replicas**: Add PostgreSQL read replicas
- **Caching**: Expand cache usage
- **CDN**: Static asset delivery
- **Load Balancing**: Multiple app instances

### Module Extraction

Modules can be extracted to microservices:
1. Extract to separate Django apps
2. Add API gateway
3. Use message queue for inter-service communication
4. Maintain database per service (or shared initially)

### Event Sourcing

Consider event sourcing for:
- Complete audit trail
- Time-travel debugging
- Event replay

## References

- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)
- [Modular Monolith](https://www.kamilgrzybek.com/blog/posts/modular-monolith-primer)

