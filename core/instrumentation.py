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
                    """
                    Returns:
                        NoOpSpan instance
                    """
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
    # Note: Metrics are exposed via prometheus_client's default /metrics endpoint
    # The metrics server is started separately if needed, but Django can serve /metrics
    prometheus_port = int(os.environ.get("PROMETHEUS_PORT", "9090"))
    try:
        # Start metrics server on all interfaces (0.0.0.0) so Prometheus can access it
        import socket

        from prometheus_client import start_http_server

        # Check if port is already in use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("0.0.0.0", prometheus_port))
        sock.close()

        if result != 0:  # Port is not in use
            start_http_server(prometheus_port, addr="0.0.0.0")
            logger.info("Prometheus metrics server started on 0.0.0.0:%s", prometheus_port)
        else:
            logger.info("Prometheus metrics server already running on port %s", prometheus_port)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Could not start Prometheus metrics server: %s", e)

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
    except Exception:  # pylint: disable=broad-exception-caught
        # Return a no-op tracer if OpenTelemetry fails to initialize
        return NoOpTracer()


if OPENTELEMETRY_AVAILABLE:
    # pylint: disable=import-error,ungrouped-imports
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
