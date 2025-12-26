# Centralized License Service

A multi-tenant, scalable license management service built with Django, following
Hexagonal Architecture, CQRS, and Modular Monolith patterns.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## Overview

The Centralized License Service provides a single source of truth for managing
licenses and entitlements across multiple brands and products. It supports:

- **Multi-tenancy**: Row-level data isolation per brand
- **License Provisioning**: Create and manage licenses for customers
- **License Activation**: Product-facing APIs for license activation
- **Seat Management**: Control concurrent activations per license
- **Lifecycle Management**: Renew, suspend, resume, and cancel licenses
- **Audit Trail**: Complete audit logging for all operations

## Architecture

This service follows a **Modular Monolith + Hexagonal Architecture + Strategic
CQRS** design:

### Modular Monolith

The application is organized into modules:
- `brands/`: Brand and product management
- `licenses/`: License key and license management
- `activations/`: License activation and seat management
- `core/`: Shared infrastructure and domain primitives
- `api/`: REST API layer

### Hexagonal Architecture (Ports & Adapters)

- **Domain Layer**: Pure business logic, no dependencies
- **Application Layer**: Use cases, commands, queries, handlers
- **Infrastructure Layer**: Django ORM, Redis, external services
- **Ports**: Repository interfaces, event bus, cache interfaces

### CQRS (Command Query Responsibility Segregation)

- **Commands**: Write operations (provision, renew, suspend, activate)
- **Queries**: Read operations (get status, list licenses)
- **Handlers**: Separate command and query handlers

### Key Design Principles

- **SOLID Principles**: Single Responsibility, Open/Closed, Liskov Substitution,
  Interface Segregation, Dependency Inversion
- **Domain-Driven Design**: Rich domain models with business logic
- **Event-Driven**: Domain events for decoupled communication
- **Async-First**: ASGI support, async views, async ORM operations

## Features

### Brand APIs

- **Provision License**: Create license keys and licenses for customers
- **Renew License**: Extend license expiration dates
- **Suspend/Resume License**: Temporarily disable licenses
- **Cancel License**: Permanently cancel licenses
- **List Licenses**: Query licenses by customer email

### Product APIs

- **Activate License**: Activate a license on a specific instance
- **Check License Status**: Verify license validity and seat availability
- **Deactivate Seat**: Release a seat for reuse

### Multi-Tenancy

- API key-based authentication per brand
- Automatic tenant context isolation
- Row-level security enforced at middleware level

### Observability

- Structured logging with correlation IDs
- Health check endpoints (`/health`, `/health/db`, `/health/cache`, `/ready`)
- Request duration tracking
- Audit logging for all license operations

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (optional)

### Installation

1. **Clone the repository**:

```bash
git clone <repository-url>
cd CentralizedLicenseService
```

2. **Create virtual environment**:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements/dev.txt
```

4. **Set up environment variables**:

Create a `.env` file:

```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/license_service
REDIS_URL=redis://localhost:6379/0
```

5. **Run migrations**:

```bash
python manage.py migrate
```

6. **Create superuser** (optional):

```bash
python manage.py createsuperuser
```

7. **Start development server**:

```bash
python manage.py runserver
```

### Docker Setup

1. **Start services**:

```bash
docker-compose up -d
```

2. **Run migrations**:

```bash
docker-compose exec app python manage.py migrate
```

3. **Access the service**:

- API: http://localhost:8000
- Admin: http://localhost:8000/admin
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## API Documentation

### Interactive API Documentation

The service provides interactive API documentation via Swagger UI and ReDoc:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema (JSON)**: http://localhost:8000/api/schema/

The OpenAPI schema is automatically generated from your Django REST Framework views
and serializers using `drf-spectacular`.

### Authentication

#### Brand APIs

Brand APIs require authentication via API key:

```http
X-API-Key: your-api-key-here
```

Or via Authorization header:

```http
Authorization: Bearer your-api-key-here
```

#### Product APIs

Product APIs authenticate using license keys in the request body.

### Brand API Endpoints

#### Provision License

Create a new license key and associated licenses.

```http
POST /api/v1/brand/licenses/provision
Content-Type: application/json
X-API-Key: your-api-key

{
  "customer_email": "customer@example.com",
  "products": ["product-uuid-1", "product-uuid-2"],
  "expiration_date": "2025-12-31T23:59:59Z",
  "max_seats": 5,
  "idempotency_key": "optional-idempotency-key"
}
```

**Response** (201 Created):

```json
{
  "license_key": {
    "id": "uuid",
    "key": "BRAND-XXXX-XXXX-XXXX-XXXX",
    "customer_email": "customer@example.com",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "licenses": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "status": "valid",
      "seat_limit": 5,
      "expires_at": "2025-12-31T23:59:59Z"
    }
  ]
}
```

#### Renew License

Extend a license's expiration date.

```http
POST /api/v1/brand/licenses/{license_id}/renew
Content-Type: application/json
X-API-Key: your-api-key

{
  "expiration_date": "2026-12-31T23:59:59Z"
}
```

#### Suspend License

Temporarily disable a license.

```http
POST /api/v1/brand/licenses/{license_id}/suspend
X-API-Key: your-api-key
```

#### Resume License

Re-enable a suspended license.

```http
POST /api/v1/brand/licenses/{license_id}/resume
X-API-Key: your-api-key
```

#### Cancel License

Permanently cancel a license.

```http
POST /api/v1/brand/licenses/{license_id}/cancel
X-API-Key: your-api-key
```

#### List Licenses by Email

Query all licenses for a customer.

```http
GET /api/v1/brand/licenses?email=customer@example.com
X-API-Key: your-api-key
```

### Product API Endpoints

#### Activate License

Activate a license on a specific instance.

```http
POST /api/v1/product/licenses/activate
Content-Type: application/json

{
  "license_key": "BRAND-XXXX-XXXX-XXXX-XXXX",
  "instance_identifier": "https://example.com",
  "instance_type": "url"
}
```

**Response** (201 Created):

```json
{
  "activation_id": "uuid",
  "status": "active",
  "seats_used": 1,
  "seats_remaining": 4
}
```

#### Check License Status

Verify license validity and seat availability.

```http
GET /api/v1/product/licenses/check?license_key=BRAND-XXXX-XXXX-XXXX-XXXX&instance_identifier=https://example.com
```

**Response** (200 OK):

```json
{
  "is_valid": true,
  "license": {
    "id": "uuid",
    "status": "valid",
    "seat_limit": 5,
    "seats_used": 1,
    "seats_remaining": 4,
    "expires_at": "2025-12-31T23:59:59Z"
  }
}
```

#### Deactivate Seat

Release a seat for reuse.

```http
POST /api/v1/product/licenses/deactivate
Content-Type: application/json

{
  "license_key": "BRAND-XXXX-XXXX-XXXX-XXXX",
  "instance_identifier": "https://example.com"
}
```

### Health Check Endpoints

- `GET /health`: Basic health check
- `GET /health/db`: Database connectivity check
- `GET /health/cache`: Cache connectivity check
- `GET /ready`: Readiness check (all dependencies)

## Development

### Code Style

This project follows WP Media's Python engineering best practices:

- **Black**: Code formatting (100 char line length)
- **isort**: Import sorting
- **Pylint**: Linting
- **MyPy**: Type checking
- **Pytest**: Testing framework

### Running Linters

```bash
# Format code
black .

# Sort imports
isort .

# Lint
pylint .

# Type check
mypy .
```

### Project Structure

```
CentralizedLicenseService/
├── api/                    # API layer
│   └── v1/
│       ├── brand/         # Brand-facing APIs
│       └── product/       # Product-facing APIs
├── brands/                # Brands module
│   ├── domain/            # Domain entities and services
│   ├── application/       # Use cases and handlers
│   ├── infrastructure/    # Django models and repositories
│   └── ports/            # Repository interfaces
├── licenses/             # Licenses module
├── activations/          # Activations module
├── core/                 # Shared infrastructure
│   ├── domain/           # Domain primitives
│   ├── infrastructure/    # Infrastructure adapters
│   └── middleware/       # Django middleware
├── products/            # Products module
├── tests/               # Test suite
└── requirements/        # Python dependencies
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration

# Run specific test file
pytest tests/unit/brands/test_brand_entity.py
```

### Test Structure

- `tests/unit/`: Unit tests for domain logic
- `tests/integration/`: Integration tests for APIs and repositories

## Deployment

### Production Settings

Set the following environment variables:

```bash
DJANGO_SECRET_KEY=your-production-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
```

### Docker Production Build

```bash
docker build -f docker/app/Dockerfile -t license-service:latest .
```

### uWSGI Configuration

The project includes `uwsgi.ini` for production deployment. Run:

```bash
uwsgi --ini uwsgi.ini
```

### Background Tasks

Register event handlers and run expiration checks:

```bash
python manage.py register_event_handlers
python manage.py check_license_expirations
```

Set up a cron job or scheduler for periodic expiration checks.

## Contributing

1. Create a feature branch
2. Make your changes following the code style guidelines
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Your License Here]

