# Centralized License Service

A multi-tenant, scalable license management service built with Django, following
Hexagonal Architecture, CQRS, and Modular Monolith patterns.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (optional)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd CentralizedLicenseService

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements/dev.txt

# Create .env file (optional - for custom configuration)
# See Environment Variables section below
cp .env.example .env  # if .env.example exists

# Run migrations
python manage.py migrate

# Create test data (superuser, brand, API key, product)
python manage.py create_test_data

# Start development server
python manage.py runserver
```

### Environment Variables

The application supports loading environment variables from a `.env` file in the project root. Create a `.env` file with the following variables (all optional):

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DB_ENGINE=postgresql  # or 'sqlite' for SQLite
DB_NAME=license_service
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DOCKER_ENV=false  # Set to 'true' when running in Docker

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# RabbitMQ (optional)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
USE_RABBITMQ=false

# OpenTelemetry
OTEL_SERVICE_NAME=license-service
OTEL_SERVICE_VERSION=1.0.0
ENVIRONMENT=development
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
PROMETHEUS_PORT=9090

# Rate Limiting
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT=100
RATE_LIMIT_WINDOW=60
```

**Note**: If no `.env` file exists, the application will use default values from settings files.

### Docker Setup

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec app python manage.py migrate

# Create test data (superuser, brand, API key, product)
docker-compose exec app python manage.py create_test_data

# Access services
# - API: http://localhost:8000
# - Admin: http://localhost:8000/admin
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9091
```

## Documentation

- **[Architecture & Design](docs/ARCHITECTURE.md)**: Complete architecture documentation including multi-tenancy, integration points, data model, and observability
- **[API Documentation](docs/API.md)**: Detailed API reference
- **[Observability Guide](docs/OBSERVABILITY.md)**: Logging, metrics, and tracing setup
- **[Explanation & Design Decisions](EXPLANATION.md)**: Detailed explanation of problem statement, architecture decisions, trade-offs, and implementation details

## Features

- **Multi-tenancy**: Row-level data isolation per brand
- **License Management**: Provision, renew, suspend, resume, and cancel licenses
- **License Activation**: Product-facing APIs for license activation
- **Seat Management**: Control concurrent activations per license
- **Observability**: Comprehensive logging, metrics, and distributed tracing
- **Resilience**: Error handling, retry logic, and graceful degradation


## API Endpoints

### Brand APIs (Authenticated)

- `POST /api/v1/brand/licenses/provision` - Provision license
- `POST /api/v1/brand/licenses/{id}/renew` - Renew license
- `POST /api/v1/brand/licenses/{id}/suspend` - Suspend license
- `POST /api/v1/brand/licenses/{id}/resume` - Resume license
- `POST /api/v1/brand/licenses/{id}/cancel` - Cancel license
- `GET /api/v1/brand/licenses?email=...` - List licenses by email

### Product APIs (Public)

- `POST /api/v1/product/licenses/activate` - Activate license
- `GET /api/v1/product/licenses/check` - Check license status
- `POST /api/v1/product/licenses/deactivate` - Deactivate seat

### Health Checks

- `GET /health` - Basic health check
- `GET /health/db` - Database health
- `GET /health/cache` - Cache health
- `GET /ready` - Readiness check

See [API Documentation](docs/API.md) for detailed API reference.


## Testing & Test Data

### Creating Test Data

The application includes a management command to quickly create test data for development and testing:

```bash
# Create all test data (superuser, brand, API key, product, license)
python manage.py create_test_data

# Skip superuser creation
python manage.py create_test_data --skip-superuser

# Skip license creation
python manage.py create_test_data --skip-license

# Customize brand and product names
python manage.py create_test_data \
    --brand-name "My Brand" \
    --brand-prefix "MB" \
    --product-name "My Product" \
    --customer-email "customer@example.com"
```

**In Docker:**
```bash
docker-compose exec app python manage.py create_test_data
```

The command creates:
- **Superuser**: `admin` / `admin` (for Django admin)
- **Brand**: Test brand with auto-generated slug and prefix
- **API Key**: Full-access API key for the brand (save this - it can't be retrieved later!)
- **Product**: Test product for the brand
- **License Key & License**: Optional test license (can be skipped with `--skip-license`)

After running the command, you'll see a summary with:
- Django admin credentials
- Brand details
- API key (save this!)
- Product details
- Example API request using the generated API key

### Django Admin

Access the Django admin at `http://localhost:8000/admin/` with the superuser credentials created by `create_test_data`:
- Username: `admin`
- Password: `admin`

**Note**: Change the admin password in production!

## Development

```bash
# Format code
black .

# Sort imports
isort .

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## License

[Your License Here]

## Contributing

1. Create a feature branch
2. Make your changes following the code style guidelines
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Your License Here]

