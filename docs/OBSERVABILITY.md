# Observability Guide

This document describes the observability stack for the Centralized License Service.

## Overview

The observability stack consists of:

- **OpenTelemetry**: Instrumentation standard for traces, metrics, and logs
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation
- **Tempo**: Distributed tracing backend

## Architecture

```
Application (Django)
    ├── OpenTelemetry SDK
    │   ├── Traces → Tempo (OTLP)
    │   └── Metrics → Prometheus
    ├── Logs → Loki (via Promtail)
    └── Custom Metrics → Prometheus
```

## Components

### OpenTelemetry

**Purpose**: Standardized instrumentation for traces and metrics

**Configuration**: `core/instrumentation.py`

**Features**:
- Auto-instrumentation for Django, PostgreSQL, Redis
- Distributed tracing with Tempo
- Prometheus metrics export
- Trace context propagation

**Environment Variables**:
```bash
OTEL_SERVICE_NAME=license-service
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
PROMETHEUS_PORT=9090
```

### Prometheus

**Purpose**: Metrics collection and alerting

**Access**: http://localhost:9091

**Metrics Collected**:
- HTTP request rate and duration
- License operations (provision, activate, renew)
- Active licenses and activations
- Database query duration
- Cache hit/miss rates
- Error rates

**Configuration**: `docker/observability/prometheus.yml`

### Grafana

**Purpose**: Visualization and dashboards

**Access**: http://localhost:3000
- Username: `admin`
- Password: `admin`

**Data Sources**:
- Prometheus (metrics)
- Loki (logs)
- Tempo (traces)

**Dashboards**:
- License Service Overview
- HTTP Performance
- License Operations
- Error Analysis

### Loki

**Purpose**: Log aggregation

**Access**: http://localhost:3100

**Features**:
- Structured JSON logs
- LogQL query language
- Integration with Grafana
- Log correlation with traces

**Configuration**: `docker/observability/loki-config.yml`

### Tempo

**Purpose**: Distributed tracing backend

**Access**: http://localhost:3200

**Features**:
- OTLP receiver (gRPC and HTTP)
- Trace storage and querying
- Integration with Grafana
- Service graph generation

**Configuration**: `docker/observability/tempo-config.yml`

### Promtail

**Purpose**: Log shipper for Loki

**Features**:
- Collects logs from Docker containers
- Ships to Loki
- Automatic service discovery

**Configuration**: `docker/observability/promtail-config.yml`

## Running the Observability Stack

### Using Docker Compose

The observability stack is included in `docker-compose.yml`:

```bash
docker-compose up -d
```

This starts:
- Prometheus (port 9091)
- Grafana (port 3000)
- Loki (port 3100)
- Tempo (ports 3200, 4317, 4318)
- Promtail

### Accessing Services

- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9091
- **Loki**: http://localhost:3100
- **Tempo**: http://localhost:3200

## Metrics

### Custom Metrics

Located in `core/metrics.py`:

- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration histogram
- `licenses_provisioned_total`: Licenses provisioned
- `licenses_activated_total`: Licenses activated
- `active_licenses`: Current active licenses (gauge)
- `active_activations`: Current active activations (gauge)
- `db_query_duration_seconds`: Database query duration
- `cache_hits_total` / `cache_misses_total`: Cache statistics
- `errors_total`: Error counts

### Prometheus Queries

**Request Rate**:
```promql
rate(http_requests_total[5m])
```

**95th Percentile Latency**:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Error Rate**:
```promql
rate(errors_total[5m])
```

**License Provision Rate**:
```promql
rate(licenses_provisioned_total[5m])
```

## Logging

### Structured Logging

Logs are formatted as JSON for Loki:

```json
{
  "asctime": "2024-01-01T00:00:00Z",
  "name": "core.middleware.observability",
  "levelname": "INFO",
  "message": "Request completed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "abc123...",
  "method": "POST",
  "path": "/api/v1/brand/licenses/provision",
  "status_code": 201,
  "duration_ms": 45.2
}
```

### LogQL Queries

**Find errors**:
```logql
{service="license-service"} |= "ERROR"
```

**Requests by endpoint**:
```logql
{service="license-service"} | json | line_format "{{.path}} - {{.status_code}}"
```

**Correlate logs with traces**:
```logql
{service="license-service"} | json | trace_id="{{.trace_id}}"
```

## Tracing

### Distributed Tracing

Traces are automatically generated for:
- HTTP requests
- Database queries
- Redis operations
- Custom spans

### Manual Instrumentation

```python
from core.instrumentation import get_tracer

tracer = get_tracer(__name__)

def my_function():
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("custom.attribute", "value")
        # Your code here
```

### Trace Correlation

Traces are correlated with logs using:
- `trace_id`: OpenTelemetry trace ID
- `span_id`: OpenTelemetry span ID
- `correlation_id`: Request correlation ID

## Grafana Dashboards

### Pre-configured Dashboards

1. **License Service Overview**
   - Request rate and latency
   - License operations
   - Error rates
   - Active licenses

2. **HTTP Performance**
   - Request duration percentiles
   - Status code distribution
   - Endpoint performance

3. **License Operations**
   - Provision rate
   - Activation rate
   - Renewal rate
   - Suspension/cancellation rate

4. **Error Analysis**
   - Error rate by type
   - Error rate by endpoint
   - Error trends

### Creating Custom Dashboards

1. Go to Grafana → Dashboards → New Dashboard
2. Add panels with Prometheus queries
3. Use LogQL for log panels
4. Use Tempo for trace panels

## Alerting

### Prometheus Alerts

Example alert rules (add to `prometheus.yml`):

```yaml
groups:
  - name: license_service
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "High latency detected"
```

## Production Considerations

1. **Storage**: Configure persistent volumes for Prometheus, Loki, Tempo
2. **Retention**: Set appropriate retention policies
3. **Security**: Enable authentication for Grafana
4. **TLS**: Use TLS for OTLP in production
5. **Sampling**: Configure trace sampling for high-volume services
6. **Resource Limits**: Set appropriate resource limits for containers

## Troubleshooting

### Metrics Not Appearing

1. Check Prometheus targets: http://localhost:9091/targets
2. Verify metrics endpoint: http://localhost:9090/metrics
3. Check OpenTelemetry configuration

### Logs Not Appearing in Loki

1. Check Promtail logs: `docker-compose logs promtail`
2. Verify Loki is running: http://localhost:3100/ready
3. Check log format matches Loki expectations

### Traces Not Appearing in Tempo

1. Check Tempo is receiving traces: http://localhost:3200/api/traces
2. Verify OTLP endpoint: `OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317`
3. Check trace sampling configuration

## References

- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)

