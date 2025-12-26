"""
OpenTelemetry instrumentation setup.

This module configures OpenTelemetry for distributed tracing,
metrics, and logging.
"""

import logging
import os

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import NoOpTracer
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    # OpenTelemetry not available (e.g., in test environment)
    OPENTELEMETRY_AVAILABLE = False
    # Create a mock NoOpTracer for when opentelemetry is not available
    class NoOpTracer:
        def start_as_current_span(self, name):
            class NoOpSpan:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                def set_attribute(self, *args, **kwargs):
                    pass
                def set_status(self, *args, **kwargs):
                    pass
            return NoOpSpan()

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
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping instrumentation setup")
        return

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
        # Start metrics server on all interfaces (0.0.0.0) so Prometheus can access it
        from prometheus_client import start_http_server

        start_http_server(prometheus_port, addr="0.0.0.0")
        logger.info(f"Prometheus metrics server started on 0.0.0.0:{prometheus_port}")
    except OSError as e:
        logger.warning(f"Prometheus metrics server port {prometheus_port} already in use: {e}")

    logger.info("OpenTelemetry instrumentation configured")


def get_tracer(name: str):
    """
    Get a tracer instance for manual instrumentation.

    Args:
        name: Tracer name (usually module name)

    Returns:
        Tracer instance
    """
    if not OPENTELEMETRY_AVAILABLE:
        return NoOpTracer()
    
    try:
        return trace.get_tracer(name)
    except Exception:
        # Return a no-op tracer if OpenTelemetry fails to initialize
        return NoOpTracer()


# Provide trace status constants that work with or without OpenTelemetry
if OPENTELEMETRY_AVAILABLE:
    from opentelemetry import trace as otel_trace
    Status = otel_trace.Status
    StatusCode = otel_trace.StatusCode
else:
    # Mock Status and StatusCode for when OpenTelemetry is not available
    class StatusCode:
        OK = "ok"
        ERROR = "error"
        UNSET = "unset"

    class Status:
        def __init__(self, code, description=None):
            self.code = code
            self.description = description

        @classmethod
        def __call__(cls, code, description=None):
            return cls(code, description)
