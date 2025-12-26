"""
OpenTelemetry instrumentation setup.

This module configures OpenTelemetry for distributed tracing,
metrics, and logging.
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import start_http_server


logger = logging.getLogger(__name__)


def setup_opentelemetry():
    """
    Configure OpenTelemetry instrumentation.

    Sets up:
    - Distributed tracing (exported to Tempo via OTLP)
    - Metrics (exported to Prometheus)
    - Auto-instrumentation for Django, PostgreSQL, Redis
    """
    # Resource attributes
    service_name = os.environ.get("OTEL_SERVICE_NAME", "license-service")
    service_version = os.environ.get("OTEL_SERVICE_VERSION", "1.0.0")
    environment = os.environ.get("ENVIRONMENT", "development")

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )

    # Configure tracing
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    # OTLP exporter for Tempo
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,  # Use TLS in production
    )

    # Batch span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace_provider.add_span_processor(span_processor)

    # Auto-instrumentation
    DjangoInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()

    # Configure Prometheus metrics
    prometheus_port = int(os.environ.get("PROMETHEUS_PORT", "9090"))
    try:
        start_http_server(prometheus_port)
        logger.info(f"Prometheus metrics server started on port {prometheus_port}")
    except OSError:
        logger.warning(f"Prometheus metrics server port {prometheus_port} already in use")

    logger.info("OpenTelemetry instrumentation configured")


def get_tracer(name: str):
    """
    Get a tracer instance for manual instrumentation.

    Args:
        name: Tracer name (usually module name)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
