"""
Prometheus metrics for the license service.

Custom metrics for business logic and performance monitoring.
"""

from prometheus_client import Counter, Gauge, Histogram

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# License metrics
licenses_provisioned_total = Counter(
    "licenses_provisioned_total",
    "Total licenses provisioned",
    ["brand_id", "product_id"],
)

licenses_activated_total = Counter(
    "licenses_activated_total",
    "Total licenses activated",
    ["brand_id", "product_id"],
)

licenses_renewed_total = Counter(
    "licenses_renewed_total",
    "Total licenses renewed",
    ["brand_id"],
)

licenses_suspended_total = Counter(
    "licenses_suspended_total",
    "Total licenses suspended",
    ["brand_id"],
)

licenses_cancelled_total = Counter(
    "licenses_cancelled_total",
    "Total licenses cancelled",
    ["brand_id"],
)

# Current state metrics
active_licenses = Gauge(
    "active_licenses",
    "Number of active licenses",
    ["brand_id", "status"],
)

active_activations = Gauge(
    "active_activations",
    "Number of active activations",
    ["brand_id"],
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# Cache metrics
cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_key"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_key"],
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "endpoint"],
)
